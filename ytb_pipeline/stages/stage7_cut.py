"""Stage 7: Video Cutting

Cuts video segments based on processed timestamps using FFmpeg.
"""

import argparse
import json
import os
import subprocess
from typing import List, Dict, Any

from ..utils import read_json, timestamp_to_seconds, seconds_to_timestamp, convert_timestamp_ffmpeg


def identify_reactive_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Identify and group reactive response segments with continuations.

    Args:
        segments: List of segment dictionaries with 'type', 'start', 'end' keys.

    Returns:
        List of grouped reactive segments.
    """
    reactive_segments = []
    current_group = None

    for segment in segments:
        seg_type = segment.get("type", "")

        if seg_type == "reactive_response":
            if current_group:
                reactive_segments.append(current_group)

            current_group = {
                "start": segment["start"],
                "end": segment["end"],
                "segments": [segment]
            }

        elif current_group and seg_type == "continuation":
            current_group["end"] = segment["end"]
            current_group["segments"].append(segment)

        elif current_group:
            reactive_segments.append(current_group)
            current_group = None

    if current_group:
        reactive_segments.append(current_group)

    return reactive_segments


def cut_video_segment(
    video_path: str,
    start_seconds: float,
    end_seconds: float,
    output_path: str,
    preset: str = "fast",
    crf: int = 23
) -> bool:
    """Cut a segment from a video using FFmpeg.

    Args:
        video_path: Path to input video.
        start_seconds: Start time in seconds.
        end_seconds: End time in seconds.
        output_path: Path to output video.
        preset: FFmpeg preset for encoding.
        crf: Constant Rate Factor for quality.

    Returns:
        True if successful, False otherwise.
    """
    start_ts = seconds_to_timestamp(start_seconds)
    end_ts = seconds_to_timestamp(end_seconds)
    start_ffmpeg = convert_timestamp_ffmpeg(start_ts)
    end_ffmpeg = convert_timestamp_ffmpeg(end_ts)

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-ss", start_ffmpeg,
        "-to", end_ffmpeg,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-preset", preset,
        "-crf", str(crf),
        output_path,
        "-y"
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Stage 7: Cut video segments")
    parser.add_argument("--video-path", required=True, help="Path to input video")
    parser.add_argument("--json-path", required=True, help="Path to JSON with timestamps")
    parser.add_argument("--output-dir", default="chunks", help="Output directory")
    parser.add_argument("--start-offset", type=float, default=0.0, help="Start time offset")
    parser.add_argument("--end-offset", type=float, default=0.0, help="End time offset")
    args = parser.parse_args()

    if not os.path.exists(args.video_path):
        print(f"Error: Video file not found: {args.video_path}")
        return

    if not os.path.exists(args.json_path):
        print(f"Error: JSON file not found: {args.json_path}")
        return

    os.makedirs(args.output_dir, exist_ok=True)

    segments = read_json(args.json_path)
    if not segments:
        print("Error: Could not load segments from JSON")
        return

    print(f"Found {len(segments)} segments in JSON")

    reactive_groups = identify_reactive_segments(segments)
    print(f"Identified {len(reactive_groups)} reactive response groups")

    successful = 0
    failed = 0

    for idx, group in enumerate(reactive_groups, 1):
        original_start = group["start"]
        original_end = group["end"]

        # Convert and apply offsets
        start_seconds = timestamp_to_seconds(original_start) + args.start_offset
        end_seconds = timestamp_to_seconds(original_end) + args.end_offset

        # Validate
        if start_seconds < 0:
            print(f"Warning: Start time negative for group {idx}, using 0")
            start_seconds = 0

        if end_seconds <= start_seconds:
            print(f"Warning: Invalid time range for group {idx}, skipping")
            continue

        output_filename = os.path.join(args.output_dir, f"reactive_chunk_{idx:03d}.mp4")

        print(f"\nProcessing group {idx}/{len(reactive_groups)}:")
        print(f"  Time: {original_start} -> {original_end}")
        print(f"  Output: {output_filename}")

        if cut_video_segment(args.video_path, start_seconds, end_seconds, output_filename):
            print(f"  ✓ Success!")
            successful += 1
        else:
            print(f"  ✗ Failed")
            failed += 1

    print(f"\n✅ Completed: {successful} successful, {failed} failed")
    print(f"Output directory: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()
