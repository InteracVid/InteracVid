"""Stage 2: Reaction Filter

Classifies each sentence as reactive_response, proactive_monologue, or continuation.
"""

import argparse
import os
import sys
import concurrent.futures
import threading
from typing import Tuple

from ..config import config
from ..utils import read_file, write_json, read_json, parse_json_response, get_client


def process_single_json(
    prompt: str,
    json_path: str,
    output_path: str,
    client
) -> Tuple[bool, str]:
    """Process a single JSON file for reaction classification.

    Args:
        prompt: Prompt template with {json} placeholder.
        json_path: Path to input JSON file.
        output_path: Path to output JSON file.
        client: LLM client instance.

    Returns:
        Tuple of (success, file_path).
    """
    for _ in range(config.processing.max_retries):
        try:
            json_content = read_file(json_path)
            if not json_content:
                print(f"Cannot read JSON file: {json_path}")
                return False, json_path

            print(f"Thread {threading.current_thread().name} processing: {os.path.basename(json_path)}")

            # Prepare prompt
            full_prompt = prompt.replace("{json}", json_content)

            # Call API
            response = client.generate(full_prompt, max_tokens=config.processing.max_tokens)
            if not response:
                continue

            # Parse response
            result = parse_json_response(response)
            if not result:
                continue

            # Save result
            if write_json(result, output_path):
                print(f"✅ Processed: {os.path.basename(json_path)}")
                return True, json_path

        except Exception as e:
            print(f"Error processing {os.path.basename(json_path)}: {e}")

    return False, json_path


def main():
    parser = argparse.ArgumentParser(description="Stage 2: Classify reactions in transcripts")
    parser.add_argument("--prompt", required=True, help="Path to prompt file")
    parser.add_argument("--input-dir", required=True, help="Input directory with JSON files")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--max-workers", type=int, default=None, help="Max concurrent workers")
    args = parser.parse_args()

    max_workers = args.max_workers or config.api.max_workers

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

    # Build task list
    tasks = []
    for json_path in json_files:
        output_path = json_path.replace(args.input_dir, args.output_dir)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if not os.path.exists(output_path):
            tasks.append((prompt, json_path, output_path))

    print(f"Processing {len(tasks)} files...")

    # Initialize client
    client = get_client()

    # Process files
    successful = 0
    failed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ReactionFilter") as executor:
        future_to_task = {
            executor.submit(process_single_json, p, j, o, client): (j, o)
            for p, j, o in tasks
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
