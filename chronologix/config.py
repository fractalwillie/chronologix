# config.py

from dataclasses import dataclass, field
from datetime import timedelta, datetime
from pathlib import Path
from typing import List, Dict, Union

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

# log levels hierarchy
LOG_LEVELS = {
    "TRACE": 5,
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
    log_streams: List[str] = field(default_factory=lambda: ["all", "errors"])
    min_log_levels: Dict[str, str] = field(default_factory=dict)
    mirror_map: Dict[str, List[str]] = field(default_factory=lambda: {"errors": ["all"]})
    timestamp_format: str = "%H:%M:%S"

    # derived fields (set during validation)
    interval_timedelta: timedelta = field(init=False)
    folder_format: str = field(init=False)
    resolved_base_path: Path = field(init=False)
    level_thresholds: Dict[str, int] = field(init=False)

    def __post_init__(self):
        """Validate & compute derived config fields (base_log_dir, interval, log_streams, mirror_map, timestamp_format, interval_timedelta, folder_format, resolved_base_path)"""
        # validate interval
        if self.interval not in INTERVAL_CONFIG:
            raise LogConfigError(
                f"Invalid interval: '{self.interval}'. "
                f"Must be one of: {list(INTERVAL_CONFIG.keys())}"
            )

        # validate mirror_map keys and targets
        invalid_keys = [k for k in self.mirror_map if k not in self.log_streams]
        invalid_targets = [
            (k, t) for k, targets in self.mirror_map.items()
            for t in targets if t not in self.log_streams
        ]

        if invalid_keys:
            raise LogConfigError(
                f"Mirror map references undefined log streams: {invalid_keys}"
            )
        if invalid_targets:
            broken = ", ".join(f"{k} → {t}" for k, t in invalid_targets)
            raise LogConfigError(
                f"Mirror map has invalid target streams: {broken}"
            )

        # validate min_log_levels if present
        for stream, level in self.min_log_levels.items():
            if stream not in self.log_streams:
                raise LogConfigError(f"min_log_levels key '{stream}' is not in log_streams")
            if level not in LOG_LEVELS:
                raise LogConfigError(f"Invalid log level '{level}' for stream '{stream}'")

        object.__setattr__(self, "level_thresholds", {
            stream: LOG_LEVELS[level]
            for stream, level in self.min_log_levels.items()
        })

        # check for presence of at least one known strftime directive in timestamp_format
        if not any(code in self.timestamp_format for code in DIRECTIVE_CONFIG):
            raise LogConfigError(
                f"Invalid timestamp_format: '{self.timestamp_format}'. "
                f"Must contain at least one valid strftime directive like %H, %M, %S (e.g. %H:%M:%S for HH:MM:SS)"
            )
        # verbose error for invalid timestamp_format string
        try:
            datetime.now().strftime(self.timestamp_format)
        except Exception as e:
            raise LogConfigError(f"Invalid timestamp_format: {self.timestamp_format} — {e}")
        
        # resolve/create and validate base_log_dir
        try:
            base = Path(self.base_log_dir).expanduser().resolve()
            base.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise LogConfigError(f"Could not resolve or create base_log_dir: {e}")
        object.__setattr__(self, "resolved_base_path", base)

        # set derived interval properties
        config = INTERVAL_CONFIG[self.interval]
        object.__setattr__(self, "interval_timedelta", config["timedelta"])
        object.__setattr__(self, "folder_format", config["folder_format"])
