# utils.py

from datetime import datetime, timedelta
import json

def floor_time(ts: datetime, delta: timedelta) -> datetime:
    """Return ts floored to a multiple of delta since Unix epoch, respecting local tz."""
    if ts.tzinfo is None:
        raise ValueError("Input datetime must be timezone-aware")

    epoch = datetime(1970, 1, 1, tzinfo=ts.tzinfo)
    seconds = int((ts - epoch).total_seconds())
    return epoch + timedelta(seconds=(seconds // int(delta.total_seconds())) * int(delta.total_seconds()))


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