# io.py

from pathlib import Path
import asyncio
from typing import List, Dict
import os


def prepare_directory(base_dir: Path, folder_name: str, log_streams: List[str]) -> Dict[str, Path]:
    """Create log folder and check if .log files for all streams exist. Return stream → file path map."""
    target_folder = base_dir / folder_name
    target_folder.mkdir(parents=True, exist_ok=True)

    path_map: Dict[str, Path] = {}

    for stream in log_streams:
        log_file = target_folder / f"{stream}.log"
        if not log_file.exists():
            log_file.touch(exist_ok=True)
        path_map[stream] = log_file

    return path_map


async def async_write(path: Path, formatted_msg: str) -> None:
    """Async wrapper to write formatted log message to file (thread-safe)."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _sync_write, path, formatted_msg)


def _sync_write(path: Path, formatted_msg: str) -> None:
    """Blocking write with flush and fsync to protect against crashes."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(formatted_msg)
        f.flush()
        os.fsync(f.fileno())
