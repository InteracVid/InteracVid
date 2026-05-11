"""Timestamp utility functions."""

from typing import Optional, Tuple


def apply_timestamp_offset(timestamp_sec: float, offset_seconds: float = 0) -> str:
    """Apply offset to timestamp and convert to API format.

    Args:
        timestamp_sec: Timestamp in seconds.
        offset_seconds: Offset to apply in seconds.

    Returns:
        Timestamp string in format '12.345s'.
    """
    try:
        adjusted_seconds = max(0.0, float(timestamp_sec) + offset_seconds)
        return f"{adjusted_seconds:.3f}s"
    except Exception as e:
        print(f"Error converting timestamp: {e}")
        return None


def seconds_to_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format.

    Args:
        seconds: Time in seconds.

    Returns:
        Timestamp in 'HH:MM:SS,mmm' format.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_part = seconds % 60
    seconds_whole = int(seconds_part)
    milliseconds = int((seconds_part - seconds_whole) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds_whole:02d},{milliseconds:03d}"


def timestamp_to_seconds(timestamp: str) -> float:
    """Convert SRT timestamp to seconds.

    Args:
        timestamp: Timestamp in 'HH:MM:SS,mmm' format.

    Returns:
        Time in seconds.
    """
    try:
        hours, minutes, seconds_ms = timestamp.split(":")
        seconds, milliseconds = seconds_ms.split(",")
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000
    except Exception as e:
        print(f"Error parsing timestamp: {e}")
        return 0.0


def convert_timestamp_ffmpeg(timestamp: str) -> str:
    """Convert SRT timestamp to FFmpeg format.

    Args:
        timestamp: Timestamp in 'HH:MM:SS,mmm' format.

    Returns:
        Timestamp in 'HH:MM:SS.mmm' format for FFmpeg.
    """
    try:
        hours, minutes, seconds_ms = timestamp.split(":")
        seconds, milliseconds = seconds_ms.split(",")
        return f"{hours}:{minutes}:{seconds}.{milliseconds}"
    except Exception as e:
        print(f"Error converting timestamp: {e}")
        return timestamp
