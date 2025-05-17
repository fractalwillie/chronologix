# manager.py

import sys
import asyncio
import atexit
from typing import Optional, Dict, Callable, Awaitable
from datetime import datetime
from chronologix.config import LogConfig, LOG_LEVELS
from chronologix.state import LogState
from chronologix.rollover import RolloverScheduler
from chronologix.io import prepare_directory, BufferedWriter
from chronologix.utils import get_current_chunk_start, format_message
from chronologix.hooks import dispatch_hooks


class LogManager:
    """
    Core orchestrator class that wires together config, state, I/O and rollover scheduling.
    User API entry point.
    """

    def __init__(self, config: LogConfig):
        """Initialize config, state, scheduler, lock, and register shutdown hook."""
        self._config = config
        self._state = LogState()
        self._writer = BufferedWriter()
        self._scheduler = RolloverScheduler(config, self._state, self._writer)
        self._level_loggers: Dict[str, Callable[[str], Awaitable[None]]] = {}
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

        self._writer.start()
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

        level_value = LOG_LEVELS[level]

        timestamp = datetime.now().strftime(self._config.timestamp_format)

        # determine which log files should receive this message based on level routing
        paths = self._state.get_paths_for_level(level)

        # Map path → format
        format_map = {}
        for sink_name, path in self._state._sink_paths.items():
            if path in paths:
                format_map[path] = self._config.sink_formats.get(sink_name, "text")

        # if mirror is in use and path matches, assign default format
        mirror_path = self._state._mirror_path
        if mirror_path and mirror_path in paths:
            format_map[mirror_path] = self._config.mirror_format or "text"

        # async handler with mutex to prevent concurrent writes to the same file
        # create and track async write tasks for all matching sinks
        for path in paths:
            fmt = format_map.get(path, "text")
            msg = format_message(message, level, timestamp, fmt)
            await self._writer.write(path, msg)

        # hook dispatch (non-blocking, isolated)
        if self._config.hook_handlers:
            log_dict = {
                "timestamp": timestamp,
                "level": level,
                "message": message
            }
            await dispatch_hooks(log_dict, level_value, self._config.hook_handlers)

        # echo to stdout/stderr if configured
        if self._config.cli_stdout_threshold is not None or self._config.cli_stderr_threshold is not None:
            cli_msg = format_message(message, level, timestamp, "text").strip()

            if self._config.cli_stderr_threshold is not None and level_value >= self._config.cli_stderr_threshold:
                print(cli_msg, file=sys.stderr)
            elif self._config.cli_stdout_threshold is not None and level_value >= self._config.cli_stdout_threshold:
                print(cli_msg, file=sys.stdout)


    def __getattr__(self, level_name: str):
        """
        Allow logger.error("msg") style calls.
        Returns a coroutine that logs with the specified level.
        """
        level_name = level_name.upper()
        if level_name not in LOG_LEVELS:
            raise AttributeError(f"'LogManager' object has no attribute '{level_name}'")

        if level_name not in self._level_loggers:
            async def level_logger(msg: str) -> None:
                await self.log(msg, level=level_name)
            self._level_loggers[level_name] = level_logger

        return self._level_loggers[level_name]


    async def stop(self) -> None:
        """Stop rollover and I/O loops."""
        await self._scheduler.stop()
        await self._writer.stop()


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