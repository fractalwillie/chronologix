# config.py

from dataclasses import dataclass, field
from datetime import timedelta, datetime
from pathlib import Path
from typing import Dict, Union, Optional, Any

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

    # derived fields
    interval_timedelta: timedelta = field(init=False)
    folder_format: str = field(init=False)
    resolved_base_path: Path = field(init=False)
    sink_levels: Dict[str, int] = field(init=False)
    sink_files: Dict[str, Path] = field(init=False)
    mirror_file: Optional[Path] = field(init=False)
    mirror_threshold: Optional[int] = field(init=False)

    def __post_init__(self):
        """Validate & compute derived config fields"""

        # validate that the interval is known and map it to its duration and folder naming format
        if self.interval not in INTERVAL_CONFIG:
            raise LogConfigError(f"Invalid interval: '{self.interval}'. Must be one of: {list(INTERVAL_CONFIG.keys())}")

        config = INTERVAL_CONFIG[self.interval]
        object.__setattr__(self, "interval_timedelta", config["timedelta"])
        object.__setattr__(self, "folder_format", config["folder_format"])

        # validate that timestamp format includes at least one valid directive and can be used by strftime
        if not any(code in self.timestamp_format for code in DIRECTIVE_CONFIG):
            raise LogConfigError(f"Invalid timestamp_format: '{self.timestamp_format}'. Must contain at least one valid strftime directive.")

        try:
            datetime.now().strftime(self.timestamp_format)
        except Exception as e:
            raise LogConfigError(f"Invalid timestamp_format: {self.timestamp_format} — {e}")

        # validate that the base directory exists and is a valid path
        try:
            base = Path(self.base_log_dir).expanduser().resolve()
            base.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise LogConfigError(f"Could not resolve or create base_log_dir: {e}")
        object.__setattr__(self, "resolved_base_path", base)

        # resolve sink paths and log levels from user config
        # validate each sink config (must include 'file' and 'min_level')
        resolved_sink_levels = {}
        resolved_sink_paths = {}

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

        # validate optional mirror config, resolve file and threshold level if provided
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
        else:
            object.__setattr__(self, "mirror_file", None)
            object.__setattr__(self, "mirror_threshold", None)
