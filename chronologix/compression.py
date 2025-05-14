# compression.py

import tarfile
import zipfile
from pathlib import Path
from datetime import timedelta, datetime
from chronologix.config import LogConfig


def _get_previous_chunk_name(folder_format: str, interval_td: timedelta) -> str:
    """Return the previous chunk's folder name based on current time and interval."""
    now = datetime.now()
    total_seconds = int((now - datetime.min).total_seconds())
    aligned = (total_seconds // int(interval_td.total_seconds())) * int(interval_td.total_seconds())
    previous_start = datetime.min + timedelta(seconds=aligned - int(interval_td.total_seconds()))
    return previous_start.strftime(folder_format)


async def run_compression(config: LogConfig) -> None:
    """
    Compress the previous log directory using configured format if compression is enabled.
    Does nothing if compression is disabled or already compressed.
    """
    if not config.compression_format:
        return  # compression is disabled

    base_dir = config.resolved_base_path
    previous_chunk_name = _get_previous_chunk_name(config.folder_format, config.interval_timedelta)
    subdir_path = base_dir / previous_chunk_name

    if not subdir_path.is_dir():
        return  # subdir does not exist
    
    # check if already compressed
    archive_name = f"{previous_chunk_name}.{config.compression_format}"
    archive_path = base_dir / archive_name
    if archive_path.exists():
        return  # already compressed

    try:
        if config.compression_format == "zip":
            _compress_zip(subdir_path, archive_path)
        elif config.compression_format == "tar.gz":
            _compress_tar(subdir_path, archive_path)
        else:
            raise ValueError(f"Unsupported compression format: {config.compression_format}")
    except Exception as e:
        print(f"[Chronologix] Compression failed for {subdir_path.name}: {e}")


def _compress_zip(source_dir: Path, dest_path: Path) -> None:
    """Compress a directory into a .zip archive."""
    with zipfile.ZipFile(dest_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in source_dir.rglob('*'):
            if file.is_file():
                zipf.write(file, arcname=file.relative_to(source_dir))


def _compress_tar(source_dir: Path, dest_path: Path) -> None:
    """Compress a directory into a .tar.gz archive."""
    with tarfile.open(dest_path, "w:gz") as tar:
        tar.add(source_dir, arcname=".")