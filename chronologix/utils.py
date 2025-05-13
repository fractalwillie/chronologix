# utils.py

from datetime import datetime, timedelta
import json

def get_current_chunk_start(now: datetime, interval_delta: timedelta) -> datetime:
    """Return start datetime of the current chunk based on interval delta."""
    total_seconds = int((now - datetime.min).total_seconds()) # align current time to nearest lower interval boundary
    aligned_seconds = (total_seconds // int(interval_delta.total_seconds())) * int(interval_delta.total_seconds())
    return datetime.min + timedelta(seconds=aligned_seconds)

def format_message(message: str, level: str, timestamp: str, format: str) -> str:
    """Format message based on the format config."""
    if format == "text":
        return f"[{timestamp}] [{level}] {message}\n"
    elif format == "json":
        return json.dumps({
            "timestamp": timestamp,
            "level": level,
            "message": message
        }) + "\n"
    else:
        raise ValueError(f"Unsupported format: {format}")