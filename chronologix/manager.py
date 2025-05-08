# manager.py

import asyncio
import atexit
from typing import List
from datetime import datetime
from chronologix.config import LogConfig, LOG_LEVELS
from chronologix.state import LogState
from chronologix.rollover import RolloverScheduler
from chronologix.io import prepare_directory, async_write
from chronologix.utils import get_current_chunk_start


class LogManager:
    """
    Core orchestrator class that wires together config, state, I/O and rollover scheduling.
    User API entry point.
    """

    def __init__(self, config: LogConfig):
        """Initialize core components: config, state, scheduler, locks, shutdown hook."""
        self._config = config
        self._state = LogState(config.log_streams, config.mirror_map)
        self._scheduler = RolloverScheduler(config, self._state)
        self._lock = asyncio.Lock()
        self._pending_tasks: List[asyncio.Task] = []
        self._level_thresholds = {
            stream: LOG_LEVELS[level]
            for stream, level in self._config.min_log_levels.items()
        }
        self._started = False
        atexit.register(self._on_exit) # register exit handler

    async def start(self) -> None:
        """Initialize current log directory, update state, and start rollover loop."""
        if self._started:
            return
        
        # compute current time chunk and next rollover point
        now = datetime.now()
        interval_delta = self._config.interval_timedelta
        current_chunk_start = get_current_chunk_start(now, interval_delta)
        chunk_name = current_chunk_start.strftime(self._config.folder_format)


        # prepare current + next interval dirs
        current_map = prepare_directory(
            self._config.resolved_base_path,
            chunk_name,
            self._config.log_streams
        )

        self._state.update_active_paths(current_map)
        self._scheduler.start()
        self._started = True

    async def log(self, message: str, target: str, level: str = None) -> None:
        """Write a timestamped log message to the target stream and its mirrors.
           If `min_log_levels` is configured, this function will skip writing to streams
           where the provided log `level` is below the configured threshold.
        """
        if not self._started:
            raise RuntimeError("LogManager has not been started yet. Call `await start()` first.")

        if level and level not in LOG_LEVELS:
            raise ValueError(f"Invalid log level: '{level}'. Must be one of: {list(LOG_LEVELS)}")

        all_paths = self._state.get_all_resolved_paths()

        if target not in all_paths:
            raise ValueError(f"Unknown log stream target: '{target}'")

        level_value = LOG_LEVELS[level] if level else None

        # check if source stream accepts level
        if target in self._level_thresholds:
            threshold = self._level_thresholds[target]
            if level_value is None or level_value < threshold:
                return  # skip, don't write or mirror

        async with self._lock:
            timestamp = datetime.now().strftime(self._config.timestamp_format)
            tasks = []

            for stream_id, path in all_paths[target]:
                # Check stream threshold (based on stream_id)
                if stream_id in self._level_thresholds:
                    if level_value is None or level_value < self._level_thresholds[stream_id]:
                        continue

                formatted_msg = (
                    f"[{timestamp}] [{level}] {message}\n"
                    if level else
                    f"[{timestamp}] {message}\n"
                )

                tasks.append(asyncio.create_task(async_write(path, formatted_msg)))
                
            self._pending_tasks.extend(tasks)
            self._pending_tasks = [t for t in self._pending_tasks if not t.done()] # remove completed tasks to avoid memory buildup
            await asyncio.gather(*tasks)

    async def stop(self) -> None:
        """Stop rollover loop and flush all pending async writes."""
        await self._scheduler.stop()
        if self._pending_tasks:
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)

    def _on_exit(self) -> None:
        """Handle atexit shutdown by awaiting pending cleanup if event loop is running."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.stop())
            else:
                loop.run_until_complete(self.stop())
        except Exception:
            pass