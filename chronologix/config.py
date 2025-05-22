# config.py

import re
from dataclasses import dataclass, field
from datetime import timedelta, datetime
from zoneinfo import ZoneInfo, available_timezones
from pathlib import Path
from typing import Dict, Union, Optional, List
from inspect import iscoroutinefunction
from chronologix.hooks import HookHandler

# custom exceptions
class LogConfigError(Exception):
    """Raised when Chronologix config is invalid."""


# interval config mapping
INTERVAL_CONFIG = {
    "24h":  {"timedelta": timedelta(hours=24), "folder_format": "%Y-%m-%d"},
    "12h":  {"timedelta": timedelta(hours=12), "folder_format": "%Y-%m-%d__%H-%M"},
    "6h":   {"timedelta": timedelta(hours=6),  "folder_format": "%Y-%m-%d__%H-%M"},
    "3h":   {"timedelta": timedelta(hours=3),  "folder_format": "%Y-%m-%d__%H-%M"},
    "1h":   {"timedelta": timedelta(hours=1),  "folder_format": "%Y-%m-%d__%H-%M"},
    "30m":  {"timedelta": timedelta(minutes=30), "folder_format": "%Y-%m-%d__%H-%M"},
    "15m":  {"timedelta": timedelta(minutes=15), "folder_format": "%Y-%m-%d__%H-%M"},
    "5m":   {"timedelta": timedelta(minutes=5),  "folder_format": "%Y-%m-%d__%H-%M"},
}

# valid directives for strftime()
DIRECTIVE_CONFIG = {
    "%H", "%I", "%M", "%S", "%f", "%p", "%z", "%Z", "%j", "%U", "%W",
    "%d", "%m", "%y", "%Y", "%a", "%A", "%b", "%B"
}

# log level hierarchy
LOG_LEVELS = {
    "NOTSET": 0,
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50
}

# regex for retain strings
RETAIN_PATTERN = re.compile(r"^(\d+)([mhdw])$")

# convert retain string to seconds
_UNIT_TO_SECONDS = {
    "m": 60,
    "h": 3600,
    "d": 86400,
    "w": 604800
}

# Chronologix config
@dataclass(frozen=True)
class LogConfig:
    base_log_dir: Union[str, Path] = "logs"
    interval: str = "24h"
    sinks: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        "debug": {"file": "debug.log", "min_level": "NOTSET"},
        "errors": {"file": "errors.log", "min_level": "ERROR"}
    })
    mirror: Optional[Dict[str, str]] = None
    timestamp_format: str = "%H:%M:%S"
    cli_echo: Optional[dict] = None
    retain: Optional[str] = None
    compression: Optional[Dict[str, str]] = None
    hooks: Optional[Dict[str, list]] = None
    timezone: str = "UTC"

    # derived fields
    interval_timedelta: timedelta = field(init=False)
    folder_format: str = field(init=False)
    resolved_base_path: Path = field(init=False)
    sink_levels: Dict[str, int] = field(init=False)
    sink_files: Dict[str, Path] = field(init=False)
    sink_formats: Dict[str, str] = field(init=False)
    mirror_file: Optional[Path] = field(init=False)
    mirror_threshold: Optional[int] = field(init=False)
    mirror_format: Optional[str] = field(init=False, default="text")
    cli_stdout_threshold: Optional[int] = field(init=False, default=None)
    cli_stderr_threshold: Optional[int] = field(init=False, default=None)
    retain_timedelta: Optional[timedelta] = field(init=False, default=None)
    compression_format: Optional[str] = field(init=False, default=None)
    hook_handlers: List["HookHandler"] = field(init=False, default_factory=list)
    resolved_tz: ZoneInfo = field(init=False)


    def __post_init__(self):
        """Validate & compute derived config fields"""

        # validate that the interval is known and map it to its duration and folder naming format
        self._validate_interval()

        # validate that timestamp format includes at least one valid directive and can be used by strftime
        self._validate_timestamp_format()

        # validate that the base directory exists and is a valid path
        self._validate_base_dir()

        # resolve sink paths and log levels from user config
        # validate each sink config (must include 'file' and 'min_level')
        self._validate_sinks_and_levels()

        # validate optional mirror config, resolve file and threshold level if provided
        self._validate_mirror_config()

        # validate & normalize cli_echo
        self._validate_cli_echo()

        # validate retain interval
        self._validate_retain()

        # validate output format, file type & create formats object
        self._validate_sink_formats()

        # validate compression config
        self._validate_compression()

        # validate hooks config and functions being passed to it
        self._validate_hooks()

        # validate timezone config
        self._validate_timezone() 


    def _validate_interval(self):
        """Validate that the interval is known and map it to its duration and folder naming format."""
        if self.interval not in INTERVAL_CONFIG:
            raise LogConfigError(f"Invalid interval: '{self.interval}'. Must be one of: {list(INTERVAL_CONFIG.keys())}")

        config = INTERVAL_CONFIG[self.interval]
        object.__setattr__(self, "interval_timedelta", config["timedelta"])
        object.__setattr__(self, "folder_format", config["folder_format"])


    def _validate_timestamp_format(self):
        """Validate that timestamp format includes at least one valid directive and can be used by strftime."""
        if not any(code in self.timestamp_format for code in DIRECTIVE_CONFIG):
            raise LogConfigError(f"Invalid timestamp_format: '{self.timestamp_format}'. Must contain at least one valid strftime directive.")

        try:
            datetime.now().strftime(self.timestamp_format)
        except Exception as e:
            raise LogConfigError(f"Invalid timestamp_format: {self.timestamp_format} — {e}")


    def _validate_base_dir(self):
        """Validate that the base directory exists and is a valid path."""
        try:
            base = Path(self.base_log_dir).expanduser().resolve()
            base.mkdir(parents=True, exist_ok=True)
            object.__setattr__(self, "resolved_base_path", base)
        except Exception as e:
            raise LogConfigError(f"Could not resolve or create base_log_dir: {e}")
        

    def _validate_sinks_and_levels(self):
        """
        Resolve sink paths and log levels from user config.
        Validate each sink config (must include 'file' and 'min_level').
        """
        resolved_sink_levels = {}
        resolved_sink_paths = {}
        base = self.resolved_base_path

        for sink_name, cfg in self.sinks.items():
            if "file" not in cfg or "min_level" not in cfg:
                raise LogConfigError(f"Sink '{sink_name}' must have both 'file' and 'min_level' keys.")
            level = cfg["min_level"].upper()
            if level not in LOG_LEVELS:
                raise LogConfigError(f"Invalid min_level '{level}' in sink '{sink_name}'. Must be one of {list(LOG_LEVELS.keys())}")
            path = base / cfg["file"]
            resolved_sink_levels[sink_name] = LOG_LEVELS[level]
            resolved_sink_paths[sink_name] = path

        object.__setattr__(self, "sink_levels", resolved_sink_levels)
        object.__setattr__(self, "sink_files", resolved_sink_paths)


    def _validate_mirror_config(self):
        """Validate optional mirror config, resolve file, threshold level, and format if provided"""
        base = self.resolved_base_path

        if self.mirror is not None:
            if not isinstance(self.mirror, dict):
                raise LogConfigError("Mirror must be a dictionary with 'file' and optional 'min_level'.")
            if "file" not in self.mirror:
                raise LogConfigError("Mirror config must contain a 'file' key.")

            mirror_file = base / self.mirror["file"]
            mirror_level = self.mirror.get("min_level", "NOTSET").upper()
            if mirror_level not in LOG_LEVELS:
                raise LogConfigError(f"Invalid mirror min_level: '{mirror_level}'")

            object.__setattr__(self, "mirror_file", mirror_file)
            object.__setattr__(self, "mirror_threshold", LOG_LEVELS[mirror_level])

            mirror_format = self.mirror.get("format", "text").lower()
            if mirror_format not in {"text", "json"}:
                raise LogConfigError(f"Invalid format '{mirror_format}' for mirror. Must be 'text' or 'json'.")

            ext = Path(self.mirror["file"]).suffix
            if ext not in {".log", ".txt", ".json", ".jsonl"}:
                raise LogConfigError(f"Unsupported file extension '{ext}' for mirror. Allowed: .log, .txt, .json, .jsonl")

            object.__setattr__(self, "mirror_format", mirror_format)
        else:
            object.__setattr__(self, "mirror_file", None)
            object.__setattr__(self, "mirror_threshold", None)
            object.__setattr__(self, "mirror_format", "text")


    def _validate_cli_echo(self):
        """Helper function to parse and normalize cli_echo config into separate thresholds for stdout and stderr"""
        cli_echo = self.cli_echo
        if not cli_echo:
            object.__setattr__(self, "cli_stdout_threshold", None)
            object.__setattr__(self, "cli_stderr_threshold", None)
            return

        def resolve_level(name: str) -> int:
            """Convert level name to numeric severity"""
            level = name.upper()
            if level not in LOG_LEVELS:
                raise LogConfigError(f"Invalid cli_echo min_level: '{level}' Must be one of {list(LOG_LEVELS.keys())}")
            return LOG_LEVELS[level]

        # simple format - {"enabled": True}
        if "enabled" in cli_echo:
            if not isinstance(cli_echo["enabled"], bool):
                raise LogConfigError("cli_echo.enabled must be a boolean.")
            if cli_echo["enabled"] is False:
                object.__setattr__(self, "cli_stdout_threshold", None)
                object.__setattr__(self, "cli_stderr_threshold", None)
                return
            level = resolve_level(cli_echo.get("min_level", "NOTSET"))
            object.__setattr__(self, "cli_stdout_threshold", level)
            object.__setattr__(self, "cli_stderr_threshold", None)
            return

        # advanced format - {"stdout": {...}, "stderr": {...}}
        stdout = cli_echo.get("stdout")
        stderr = cli_echo.get("stderr")

        if stdout is None and stderr is None:
            raise LogConfigError("cli_echo must define at least 'stdout' or 'stderr' block.")

        if stdout:
            if "min_level" not in stdout:
                raise LogConfigError("cli_echo.stdout requires a 'min_level'")
            object.__setattr__(self, "cli_stdout_threshold", resolve_level(stdout["min_level"]))
        else:
            object.__setattr__(self, "cli_stdout_threshold", None)

        if stderr:
            if "min_level" not in stderr:
                raise LogConfigError("cli_echo.stderr requires a 'min_level'")
            object.__setattr__(self, "cli_stderr_threshold", resolve_level(stderr["min_level"]))
        else:
            object.__setattr__(self, "cli_stderr_threshold", None)


    def _validate_retain(self):
        """Validate the 'retain' config string and calculate its timedelta."""
        if self.retain is None:
            object.__setattr__(self, "retain_timedelta", None)
            return

        if not isinstance(self.retain, str):
            raise LogConfigError("retain must be a string like '3d', '24h', or '1w'. Supported units: m, h, d, w.")

        normalized = self.retain.strip().lower()

        if not RETAIN_PATTERN.match(normalized):
            raise LogConfigError(
                f"Invalid retain interval: '{self.retain}'. "
                "retain must be a string like '3d', '24h', or '1w'. Supported units: m, h, d, w."
            )

        def parse_retain_string(retain: str) -> timedelta:
            """ Parse retain string into a timedelta."""
            match = RETAIN_PATTERN.match(retain.strip().lower())
            if not match:
                raise ValueError(f"Invalid retain interval: '{retain}'. Supported units: m, h, d, w.")

            value, unit = match.groups()
            return timedelta(seconds=int(value) * _UNIT_TO_SECONDS[unit])

        retain_td = parse_retain_string(self.retain)
        if retain_td < self.interval_timedelta:
            raise LogConfigError(
                f"retain='{self.retain}' is shorter than the rollover interval '{self.interval}'. "
                "Retention must be equal to or longer than the interval to avoid deleting active logs."
            )

        object.__setattr__(self, "retain_timedelta", retain_td)


    def _validate_sink_formats(self):
        """Validate and assign sink format per sink."""
        supported_formats = {"text", "json"}
        supported_extensions = {".log", ".txt", ".json", ".jsonl"}
        formats: Dict[str, str] = {}

        for sink_name, cfg in self.sinks.items():
            format_value = cfg.get("format", "text").lower()
            if format_value not in supported_formats:
                raise LogConfigError(f"Invalid format '{format_value}' for sink '{sink_name}'. Must be one of {list(supported_formats)}")

            ext = Path(cfg["file"]).suffix
            if ext not in supported_extensions:
                raise LogConfigError(f"Unsupported file extension '{ext}' for sink '{sink_name}'. Allowed: {list(supported_extensions)}")

            formats[sink_name] = format_value

        object.__setattr__(self, "sink_formats", formats)


    def _validate_compression(self):
        """Validate compression config block and assign compression_format if enabled."""
        if not self.compression:
            object.__setattr__(self, "compression_format", None)
            return

        if not isinstance(self.compression, dict):
            raise LogConfigError("compression must be a dictionary with 'enabled' boolean and optional 'compress_format'.")

        enabled = self.compression.get("enabled", False)

        if not isinstance(enabled, bool):
            raise LogConfigError("compression.enabled must be a boolean.")

        if not enabled:
            object.__setattr__(self, "compression_format", None)
            return

        # If enabled, validate or assign compress_format
        compress_format = self.compression.get("compress_format", "zip").lower()
        if compress_format not in {"zip", "tar.gz"}:
            raise LogConfigError("Invalid compress_format: must be either 'zip' or 'tar.gz'.")

        object.__setattr__(self, "compression_format", compress_format)


    def _validate_hooks(self):
        """Validate and normalize hooks config into HookHandler objects."""
        raw_hooks = getattr(self, "hooks", None)

        if not raw_hooks or not isinstance(raw_hooks, dict):
            object.__setattr__(self, "hook_handlers", [])
            return

        raw_handlers = raw_hooks.get("handlers", [])
        if not isinstance(raw_handlers, list):
            raise LogConfigError("hooks.handlers must be a list of coroutine functions or dicts with 'func'.")

        parsed_hooks = []

        for idx, entry in enumerate(raw_handlers):
            if iscoroutinefunction(entry):
                parsed_hooks.append(HookHandler(threshold=0, func=entry))
            elif isinstance(entry, dict):
                func = entry.get("func")
                if not iscoroutinefunction(func):
                    raise LogConfigError(f"Hook entry {idx} has non-async func.")
                level = entry.get("min_level", "NOTSET").upper()
                if level not in LOG_LEVELS:
                    raise LogConfigError(f"Hook entry {idx} has invalid min_level: '{level}'")
                parsed_hooks.append(HookHandler(threshold=LOG_LEVELS[level], func=func))
            else:
                raise LogConfigError(f"Hook entry {idx} must be a coroutine or a dict with 'func'.")

        object.__setattr__(self, "hook_handlers", parsed_hooks)


    def _validate_timezone(self):
        """Validate and resolve timezone string into ZoneInfo object."""
        try:
            tz = ZoneInfo(self.timezone)
            object.__setattr__(self, "resolved_tz", tz)
        except Exception:
            valid = sorted(available_timezones())
            raise LogConfigError(
                f"Invalid timezone: '{self.timezone}'. Must be a valid IANA zone name: {valid}"
            )
