"""Stage 5: Temporal Refinement

Refines timing of segments with temporal offsets using VLM.
"""

import argparse
import os
import sys
import concurrent.futures
import threading
import time
from typing import Tuple, Optional

from ..config import config
from ..utils import read_file, write_json, read_json, parse_json_response, apply_timestamp_offset
from ..utils.api_client import GeminiClient


def process_single_json(
    prompt: str,
    json_path: str,
    output_dir: str,
    client: GeminiClient,
    start_offset_seconds: float = 0,
    end_offset_seconds: float = 0
) -> Tuple[bool, str, int]:
    """Process a single JSON file with VLM for temporal refinement.

    Args:
        prompt: Prompt template with {TRANSCRIPT} and {BULLET} placeholders.
        json_path: Path to input JSON file.
        output_dir: Output directory.
        client: Gemini client with video support.
        start_offset_seconds: Offset for start timestamp.
        end_offset_seconds: Offset for end timestamp.

    Returns:
        Tuple of (success, file_path, processed_items_count).
    """
    try:
        data = read_json(json_path)
        if not data:
            return False, json_path, 0

        if not isinstance(data, list):
            data = [data]

        print(f"Thread {threading.current_thread().name} processing: {os.path.basename(json_path)}")

        processed_items = 0
        base_name = os.path.splitext(os.path.basename(json_path))[0]

        for i, item in enumerate(data, 1):
            meta = item.get("meta", {})
            video_id = meta.get("video_id")
            result_filename = f"{base_name}_item_{i:03d}.json"
            result_path = os.path.join(output_dir, result_filename)

            if os.path.exists(result_path):
                print(f"File exists, skipping: {result_path}")
                continue

            if not video_id:
                print("Cannot extract video_id, skipping")
                continue

            video_url = f"https://www.youtube.com/watch?v={video_id}"

            merged_resp = item.get("merged_response", {})
            start_sec = merged_resp.get("start")
            end_sec = merged_resp.get("end")
            transcript = merged_resp.get("text", "")

            # Extract bullet text
            bullet_obj = item.get("bullet", {})
            raw_bullet_text = bullet_obj.get("text", "")
            bullet_text = raw_bullet_text.replace('["', '').replace('"]', '').strip()

            if start_sec is None or end_sec is None:
                print("Missing timestamps, skipping")
                continue

            start_offset = apply_timestamp_offset(start_sec, start_offset_seconds)
            end_offset = apply_timestamp_offset(end_sec, end_offset_seconds)

            if not start_offset or not end_offset:
                print("Timestamp conversion failed, skipping")
                continue

            # Prepare prompt
            current_prompt = prompt.replace("{TRANSCRIPT}", transcript).replace("{BULLET}", bullet_text)

            print(f"Processing video: {video_url} | {start_offset} - {end_offset}")

            # Call API with video
            response = client.generate_with_video(
                prompt=current_prompt,
                video_url=video_url,
                start_offset=start_offset,
                end_offset=end_offset
            )

            if not response:
                print(f"❌ API call failed: {json_path}")
                continue

            api_response = parse_json_response(response)
            if not api_response:
                continue

            result = {
                "meta": meta,
                "bullet": item.get("bullet"),
                "target_analysis": item.get("target_analysis"),
                "merged_response": merged_resp,
                "api_request_metadata": {
                    "video_url": video_url,
                    "start_offset_applied": start_offset,
                    "end_offset_applied": end_offset
                },
                "api_response_4": item.get("api_response"),
                "api_response": api_response,
                "additional_offset": {
                    "start_offset": start_offset_seconds,
                    "end_offset": end_offset_seconds
                }
            }

            if write_json(result, result_path):
                processed_items += 1
                print(f"✅ Saved: {result_filename}")

            time.sleep(1)

        return True, json_path, processed_items

    except Exception as e:
        print(f"❌ Error processing {os.path.basename(json_path)}: {e}")
        return False, json_path, 0


def main():
    parser = argparse.ArgumentParser(description="Stage 5: Temporal refinement with VLM")
    parser.add_argument("--prompt", required=True, help="Path to prompt file")
    parser.add_argument("--input-dir", required=True, help="Input directory with JSON files")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--max-workers", type=int, default=30, help="Max concurrent workers")
    parser.add_argument("--start-offset", type=float, default=-2.0, help="Start timestamp offset")
    parser.add_argument("--end-offset", type=float, default=2.0, help="End timestamp offset")
    args = parser.parse_args()

    # Load prompt
    prompt = read_file(args.prompt)
    if not prompt:
        print("Cannot read prompt file")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    # Get JSON files
    json_files = []
    for root, _, files in os.walk(args.input_dir):
        for f in files:
            if f.endswith('.json'):
                json_files.append(os.path.join(root, f))

    if not json_files:
        print(f"No JSON files found in {args.input_dir}")
        sys.exit(1)

    print(f"Found {len(json_files)} JSON files")

    # Initialize Gemini client (required for video processing)
    client = GeminiClient()

    total_processed_items = 0
    successful = 0
    failed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers, thread_name_prefix="TemporalProcessor") as executor:
        future_to_task = {
            executor.submit(
                process_single_json,
                prompt, json_path, args.output_dir,
                client, args.start_offset, args.end_offset
            ): json_path
            for json_path in json_files
        }

        for future in concurrent.futures.as_completed(future_to_task):
            success, path, processed_items = future.result()
            if success:
                successful += 1
                total_processed_items += processed_items
            else:
                failed += 1

    print(f"\n✅ Completed: {successful} successful, {failed} failed")
    print(f"📊 Total segments processed: {total_processed_items}")
    if args.start_offset != 0:
        print(f"⏰ Start offset: {args.start_offset}s")
    if args.end_offset != 0:
        print(f"⏰ End offset: {args.end_offset}s")


if __name__ == "__main__":
    main()
