# errors.py

from pathlib import Path
from datetime import datetime
import sys

INTERNAL_LOG_FILE = "chronologix_internal.log"

_current_internal_path: Path | None = None


def set_internal_log_path(path: Path):
    """Store the current path to the internal log file."""
    global _current_internal_path
    _current_internal_path = path


def internal_log(msg: str):
    """
    Write diagnostic message to internal Chronologix log file if configured.
    Falls back to stderr if the file path is unset or write fails.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    full = f"[Chronologix] [{timestamp}] {msg}\n"

    path = _current_internal_path
    if path is None:
        print(full.strip(), file=sys.stderr)
        return

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(full)
    except Exception:
        # CLI fallback
        print(full.strip(), file=sys.stderr)
