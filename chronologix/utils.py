# utils.py

from datetime import datetime, timedelta

def get_current_chunk_start(now: datetime, interval_delta: timedelta) -> datetime:
    """Return start datetime of the current chunk based on interval delta."""
    total_seconds = int((now - datetime.min).total_seconds()) # align current time to nearest lower interval boundary
    aligned_seconds = (total_seconds // int(interval_delta.total_seconds())) * int(interval_delta.total_seconds())
    return datetime.min + timedelta(seconds=aligned_seconds)
