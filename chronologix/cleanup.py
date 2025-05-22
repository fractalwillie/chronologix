# cleanup.py

import shutil
from datetime import datetime, timezone
from chronologix.config import LogConfig
from chronologix.errors import internal_log

async def run_cleanup(config: LogConfig) -> None:
    """Delete old log directories based on retention config."""
    if not config.retain_timedelta:
        return

    try:
        cutoff = datetime.now(config.resolved_tz) - config.retain_timedelta
        base_dir = config.resolved_base_path

        for entry in base_dir.iterdir():
            if not entry.is_dir():
                continue

            try:
                timestamp = _parse_timestamp(entry.name, config.folder_format, config.resolved_tz)
                if timestamp < cutoff:
                    shutil.rmtree(entry)
            except Exception:
                continue  # skip invalid folder names or parse errors

    except Exception as e:
        internal_log(f"Cleanup failed: {e}")


def _parse_timestamp(folder_name: str, folder_format: str, resolved_tz: timezone) -> datetime:
    """Parse a timestamp from a folder name."""
    return datetime.strptime(folder_name, folder_format).replace(tzinfo=resolved_tz)
