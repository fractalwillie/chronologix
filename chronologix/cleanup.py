# cleanup.py

import shutil
from datetime import datetime
from chronologix.config import LogConfig

async def run_cleanup(config: LogConfig) -> None:
    """Delete old log directories based on retention config."""
    if not config.retain_timedelta:
        return

    try:
        cutoff = datetime.now() - config.retain_timedelta
        base_dir = config.resolved_base_path

        for entry in base_dir.iterdir():
            if not entry.is_dir():
                continue

            try:
                timestamp = _parse_timestamp(entry.name, config.folder_format)
                if timestamp < cutoff:
                    shutil.rmtree(entry)
            except Exception:
                continue  # skip invalid folder names or parse errors

    except Exception as e:
        print(f"[Chronologix] Cleanup failed: {e}")


def _parse_timestamp(folder_name: str, fmt: str) -> datetime:
    """Parse a timestamp from a folder name."""
    return datetime.strptime(folder_name, fmt)
