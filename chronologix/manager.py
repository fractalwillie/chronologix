# manager.py

import sys
import asyncio
import atexit
from typing import List, Optional
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
        """Initialize config, state, scheduler, lock, and register shutdown hook."""
        self._config = config
        self._state = LogState()
        self._scheduler = RolloverScheduler(config, self._state)
        self._lock = asyncio.Lock()
        self._pending_tasks: List[asyncio.Task] = []
        self._started = False

        atexit.register(self._on_exit) # register exit handler

    async def start(self) -> None:
        """Initialize current log directory, update state, and start rollover loop."""
        if self._started:
            return

        # determine the current chunk (log folder) name based on interval alignment
        now = datetime.now()
        interval_delta = self._config.interval_timedelta
        chunk_name = get_current_chunk_start(now, interval_delta).strftime(self._config.folder_format)

        # collect unique filenames across all sinks (and optional mirror) to prepare directory
        all_files = {p.name for p in self._config.sink_files.values()}
        if self._config.mirror_file:
            all_files.add(self._config.mirror_file.name)

        # prepare the current log directory and create all required files
        current_map = prepare_directory(self._config.resolved_base_path, chunk_name, all_files)

        # register file paths and levels into shared log state
        self._state.update_active_paths(
            sink_paths={name: current_map[path.name] for name, path in self._config.sink_files.items()},
            mirror_path=current_map.get(self._config.mirror_file.name) if self._config.mirror_file else None,
            sink_levels=self._config.sink_levels,
            mirror_threshold=self._config.mirror_threshold
        )

        self._scheduler.start()
        self._started = True

    async def log(self, message: str, level: Optional[str] = None) -> None:
        """
        Write a timestamped log message to all sinks (and mirror) that accept the level.
        If level is omitted, 'NOTSET' is used by default.
        """
        if not self._started:
            raise RuntimeError("LogManager has not been started yet. Call `await start()` first.")

        # normalize level and validate
        level = (level or "NOTSET").upper()
        if level not in LOG_LEVELS:
            raise ValueError(f"Invalid log level: '{level}'. Must be one of: {list(LOG_LEVELS)}")

        timestamp = datetime.now().strftime(self._config.timestamp_format)
        formatted_msg = f"[{timestamp}] [{level}] {message}\n"

        # determine which log files should receive this message based on level routing
        paths = self._state.get_paths_for_level(level)

        # async handler with mutex to prevent concurrent writes to the same file
        # create and track async write tasks for all matching sinks
        async with self._lock:
            tasks = [asyncio.create_task(async_write(p, formatted_msg)) for p in paths]
            self._pending_tasks.extend(tasks)
            self._pending_tasks = [t for t in self._pending_tasks if not t.done()] # remove completed tasks to avoid memory buildup
            await asyncio.gather(*tasks)

        # echo to stdout/stderr if configured
        if self._config.cli_stdout_threshold is not None or self._config.cli_stderr_threshold is not None:
            level_value = LOG_LEVELS[level]

            if self._config.cli_stderr_threshold is not None and level_value >= self._config.cli_stderr_threshold:
                print(formatted_msg.strip(), file=sys.stderr)
            elif self._config.cli_stdout_threshold is not None and level_value >= self._config.cli_stdout_threshold:
                print(formatted_msg.strip(), file=sys.stdout)



    def __getattr__(self, level_name: str):
        """
        Allow logger.error("msg") style calls
        Maps attribute access to log-level-aware logging
        """
        level_name = level_name.upper()
        if level_name not in LOG_LEVELS:
            raise AttributeError(f"'LogManager' object has no attribute '{level_name}'")

        async def level_logger(msg: str) -> None:
            await self.log(msg, level=level_name)

        return level_logger

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