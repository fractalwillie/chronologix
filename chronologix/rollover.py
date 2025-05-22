# rollover.py

import asyncio, time, traceback
from datetime import datetime, timedelta
from chronologix.config import LogConfig
from chronologix.state import LogState
from chronologix.io import BufferedWriter
from chronologix.io import prepare_directory
from chronologix.utils import floor_time
from chronologix.cleanup import run_cleanup
from chronologix.compression import run_compression
from chronologix.errors import set_internal_log_path, INTERNAL_LOG_FILE, internal_log


class RolloverScheduler:
    def __init__(self, config: LogConfig, state: LogState, writer: BufferedWriter):
        """Initialize rollover scheduler with config and mutable state reference."""
        self._config = config
        self._state = state
        self._writer = writer
        self._running_task = None
        self._lock = asyncio.Lock()

    def start(self) -> None:
        """Launch async rollover task."""
        if not self._running_task:
            self._running_task = asyncio.create_task(self._run_loop())

    async def _run_loop(self) -> None:
        """Continuously schedules log rollover based on configured interval."""
        try:
            interval = self._config.interval_timedelta 
            slop = 0.50 # tolerance for wake-up delay

            # initial rollover (creates current+next dirs)
            wall_now = datetime.now(self._config.resolved_tz)
            chunk_start = floor_time(wall_now, interval)
            await self._do_rollover(chunk_start)

            next_wall = chunk_start + interval
            next_mono = time.monotonic() + (next_wall - wall_now).total_seconds()

            while True:
                # sleep until rollover
                await asyncio.sleep(max(0.0, next_mono - time.monotonic()))

                wall_now = datetime.now(self._config.resolved_tz)

                await self._do_rollover(next_wall)

                missed = 0
                # catch-up loop for missed intervals
                while True:
                    wall_now = datetime.now(self._config.resolved_tz)
                    if wall_now < next_wall + interval - timedelta(seconds=slop):
                        break
                    missed += 1
                    next_wall += interval
                    await self._do_rollover(next_wall)

                if missed:
                    internal_log(f"Rollover caught up {missed} extra intervals")

                # schedule next wake-up
                wall_now = datetime.now(self._config.resolved_tz)    # fresh read
                next_wall = floor_time(wall_now, interval) + interval
                next_mono = time.monotonic() + (next_wall - wall_now).total_seconds()

        except asyncio.CancelledError:
            pass
        except Exception:
            internal_log("Rollover loop crashed:\n" + traceback.format_exc())

    async def _do_rollover(self, chunk_start: datetime) -> None:
        """Prepares new log directories and updates paths on interval."""
        # calculate next chunk timestamp
        interval = self._config.interval_timedelta
        next_chunk_start = chunk_start + interval

        # prepare dirs for current and next intervals
        current_folder = chunk_start.strftime(self._config.folder_format)
        next_folder = next_chunk_start.strftime(self._config.folder_format)

        # collect all unique files to be prepared (sinks + mirror)
        all_files = {p.name for p in self._config.sink_files.values()}
        if self._config.mirror_file:
            all_files.add(self._config.mirror_file.name)
        all_files.add(INTERNAL_LOG_FILE)

        # prepare dirs
        current_map = prepare_directory(self._config.resolved_base_path, current_folder, all_files)
        prepare_directory(self._config.resolved_base_path, next_folder, all_files)

        # set path to internal sink
        internal_path = current_map.get(INTERNAL_LOG_FILE)
        if internal_path:
            set_internal_log_path(internal_path)

        # flush any pending writes before updating state
        await self._writer.flush()

        # update internal state with current paths + level routing
        self._state.update_active_paths(
            sink_paths={name: current_map[path.name] for name, path in self._config.sink_files.items()},
            mirror_path=current_map.get(self._config.mirror_file.name) if self._config.mirror_file else None,
            sink_levels=self._config.sink_levels,
            mirror_threshold=self._config.mirror_threshold
        )

        # run compression and cleanup with lock to prevent deletion of active subdir during compression
        async with self._lock:
            await run_compression(self._config)
            await run_cleanup(self._config)


    async def stop(self) -> None:
        """Cancel and await the rollover task to exit gracefully."""
        if self._running_task:
            self._running_task.cancel()
            try:
                await self._running_task
            except asyncio.CancelledError:
                pass
