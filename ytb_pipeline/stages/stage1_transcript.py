"""Stage 1: Transcript Processing

Converts raw SRT subtitle files into structured JSON transcripts.
"""

import argparse
import os
import sys
import concurrent.futures
import threading
from typing import Optional, Tuple

from ..config import config
from ..utils import read_file, write_json, parse_json_response, get_client


def process_single_srt(
    prompt: str,
    srt_path: str,
    output_path: str,
    client
) -> Tuple[bool, str]:
    """Process a single SRT file.

    Args:
        prompt: Prompt template with {srt} placeholder.
        srt_path: Path to input SRT file.
        output_path: Path to output JSON file.
        client: LLM client instance.

    Returns:
        Tuple of (success, file_path).
    """
    try:
        srt_content = read_file(srt_path)
        if not srt_content:
            print(f"Cannot read SRT file: {srt_path}")
            return False, srt_path

        print(f"Thread {threading.current_thread().name} processing: {os.path.basename(srt_path)}")

        # Prepare prompt
        full_prompt = prompt.replace("{srt}", srt_content)

        # Call API
        response = client.generate(full_prompt, max_tokens=config.processing.max_tokens)
        if not response:
            return False, srt_path

        # Parse response
        result = parse_json_response(response)
        if not result:
            return False, srt_path

        # Save result
        if write_json(result, output_path):
            print(f"✅ Processed: {os.path.basename(srt_path)} -> {os.path.basename(output_path)}")
            return True, srt_path
        else:
            return False, srt_path

    except Exception as e:
        print(f"Error processing {os.path.basename(srt_path)}: {e}")
        return False, srt_path


def main():
    parser = argparse.ArgumentParser(description="Stage 1: Process SRT files into JSON transcripts")
    parser.add_argument("--prompt", required=True, help="Path to prompt file")
    parser.add_argument("--input-dir", required=True, help="Input directory with SRT files")
    parser.add_argument("--output-dir", required=True, help="Output directory for JSON files")
    parser.add_argument("--max-workers", type=int, default=None, help="Max concurrent workers")
    args = parser.parse_args()

    max_workers = args.max_workers or config.api.max_workers

    # Load prompt
    prompt = read_file(args.prompt)
    if not prompt:
        print("Cannot read prompt file")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    # Get SRT files
    srt_files = []
    for root, _, files in os.walk(args.input_dir):
        for f in files:
            if f.endswith('.srt'):
                srt_files.append(os.path.join(root, f))

    if not srt_files:
        print(f"No SRT files found in {args.input_dir}")
        sys.exit(1)

    print(f"Found {len(srt_files)} SRT files")

    # Build task list
    tasks = []
    for srt_path in srt_files:
        output_path = srt_path.replace(args.input_dir, args.output_dir).replace(".srt", ".json")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if not os.path.exists(output_path):
            tasks.append((prompt, srt_path, output_path))

    print(f"Processing {len(tasks)} files...")

    # Initialize client
    client = get_client()

    # Process files
    successful = 0
    failed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="SRTProcessor") as executor:
        future_to_task = {
            executor.submit(process_single_srt, p, s, o, client): (s, o)
            for p, s, o in tasks
        }

        for future in concurrent.futures.as_completed(future_to_task):
            success, path = future.result()
            if success:
                successful += 1
            else:
                failed += 1

    print(f"\n✅ Completed: {successful} successful, {failed} failed")


if __name__ == "__main__":
    main()
