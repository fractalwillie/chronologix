# rollover.py

import asyncio
import traceback
from datetime import datetime
from chronologix.config import LogConfig
from chronologix.state import LogState
from chronologix.io import prepare_directory
from chronologix.utils import get_current_chunk_start


class RolloverScheduler:
    def __init__(self, config: LogConfig, state: LogState):
        """Initialize rollover scheduler with config and mutable state reference."""
        self._config = config
        self._state = state
        self._running_task = None

    def start(self) -> None:
        """Launch async rollover task."""
        if not self._running_task:
            self._running_task = asyncio.create_task(self._run_loop())

    async def _run_loop(self) -> None:
        """Infinite loop that prepares new log directories and updates paths on interval."""
        try:
            while True:
                # calculate the current and next chunk times, determine how long to sleep
                now = datetime.now()
                interval_delta = self._config.interval_timedelta
                current_chunk_start = get_current_chunk_start(now, interval_delta)
                next_chunk_start = current_chunk_start + interval_delta
                sleep_duration = (next_chunk_start - now).total_seconds()

                # prepare dirs for current and next intervals
                current_folder = current_chunk_start.strftime(self._config.folder_format)
                next_folder = next_chunk_start.strftime(self._config.folder_format)

                # collect all unique files to be prepared (sinks + mirror)
                all_files = {p.name for p in self._config.sink_files.values()}
                if self._config.mirror_file:
                    all_files.add(self._config.mirror_file.name)

                # prepare dirs
                current_map = prepare_directory(self._config.resolved_base_path, current_folder, all_files)
                prepare_directory(self._config.resolved_base_path, next_folder, all_files)

                # update internal state with current paths + level routing
                self._state.update_active_paths(
                    sink_paths={name: current_map[path.name] for name, path in self._config.sink_files.items()},
                    mirror_path=current_map.get(self._config.mirror_file.name) if self._config.mirror_file else None,
                    sink_levels=self._config.sink_levels,
                    mirror_threshold=self._config.mirror_threshold
                )

                # sleep until rollover
                await asyncio.sleep(sleep_duration)

        except asyncio.CancelledError:
            pass
        except Exception:
            print("[Chronologix] Rollover loop crashed:\n" + traceback.format_exc())

    async def stop(self) -> None:
        """Cancel and await the rollover task to exit gracefully."""
        if self._running_task:
            self._running_task.cancel()
            try:
                await self._running_task
            except asyncio.CancelledError:
                pass
