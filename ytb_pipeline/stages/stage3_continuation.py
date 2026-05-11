"""Stage 3: Continuation Processing

This stage has three sub-steps:
1. Add context from source files to reactive responses
2. Classify continuations using LLM
3. Merge continuations to form complete response units
"""

import os
import json
import glob
import argparse
import sys
import concurrent.futures
from multiprocessing import Pool, cpu_count
from typing import List, Dict, Any, Optional

from ..config import config
from ..utils import read_file, write_json, read_json, parse_json_response, get_client


# =============================================================================
# Step 3.1: Add Context from Source Files
# =============================================================================

def add_context_to_entry(entry: Dict, source_cache: Dict) -> Dict:
    """Add context_next to a reactive_response entry.

    Args:
        entry: The entry to process.
        source_cache: Cache for source file data.

    Returns:
        Processed entry with context_next added.
    """
    if entry.get("label") != "reactive_response":
        return None

    meta = entry.get("meta", {})
    source_file = meta.get("source_file")
    source_index = meta.get("source_index")

    if source_file and source_index is not None:
        if source_file not in source_cache:
            if os.path.exists(source_file):
                try:
                    with open(source_file, 'r', encoding='utf-8') as sf:
                        source_cache[source_file] = json.load(sf)
                except Exception as e:
                    print(f"[Error] Could not read source {source_file}: {e}")
                    source_cache[source_file] = None
            else:
                source_cache[source_file] = None

        source_data = source_cache[source_file]

        if source_data:
            start_idx = source_index + 1
            end_idx = start_idx + 5

            context_raw = source_data[start_idx:end_idx]

            context_next = [
                {
                    "text": item.get("text", ""),
                    "start": item.get("start", 0),
                    "end": item.get("end", 0)
                }
                for item in context_raw
            ]

            entry["context_next"] = context_next

    # Process bullet
    try:
        tb_idx = int(entry["trigger_bullet_index"])
        entry["bullet"] = entry["candidates"][tb_idx]
    except:
        entry["bullet"] = None

    # Clean up
    entry.pop("context_prev", None)
    entry.pop("reason", None)
    entry.pop("candidates", None)
    entry.pop("trigger_bullet_index", None)
    entry.pop("label", None)

    return entry


def step1_add_context(input_dir: str, output_dir: str, num_workers: int = None):
    """Step 3.1: Add context from source files.

    Args:
        input_dir: Input directory with JSON files.
        output_dir: Output directory.
        num_workers: Number of workers.
    """
    num_workers = num_workers or max(1, cpu_count() - 2)

    def get_files(root_dir, extension="*.json"):
        return glob.glob(os.path.join(root_dir, "**", extension), recursive=True)

    def process_single_file(file_pair):
        input_path, output_path = file_pair

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            filtered_data = []
            source_cache = {}

            for entry in data:
                if isinstance(entry, dict) and entry.get("label") == "reactive_response":
                    processed = add_context_to_entry(entry, source_cache)
                    if processed:
                        filtered_data.append(processed)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            if len(filtered_data) > 0:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(filtered_data, f, indent=2, ensure_ascii=False)

            return 1

        except Exception as e:
            print(f"[Fatal Error] Failed processing {input_path}: {e}")
            return 0

    print(f"Scanning for files in: {input_dir}")
    all_files = get_files(input_dir)
    print(f"Found {len(all_files)} files.")

    tasks = []
    for input_path in all_files:
        rel_path = os.path.relpath(input_path, input_dir)
        output_path = os.path.join(output_dir, rel_path)
        tasks.append((input_path, output_path))

    print(f"Starting multiprocessing with {num_workers} workers...")

    with Pool(num_workers) as pool:
        results = list(pool.imap_unordered(process_single_file, tasks))

    print(f"Processed {sum(results)} files successfully.")


# =============================================================================
# Step 3.2: Classify Continuations using LLM
# =============================================================================

def process_single_continuation(prompt: str, json_path: str, output_path: str, client) -> tuple:
    """Process a single JSON file for continuation classification.

    Args:
        prompt: Prompt template.
        json_path: Input JSON path.
        output_path: Output JSON path.
        client: LLM client.

    Returns:
        Tuple of (success, path).
    """
    for _ in range(config.processing.max_retries):
        try:
            json_content = read_file(json_path)
            if not json_content:
                return False, json_path

            full_prompt = prompt.replace("{json}", json_content)

            response = client.generate(full_prompt, max_tokens=config.processing.max_tokens)
            if not response:
                continue

            result = parse_json_response(response)
            if not result:
                continue

            if write_json(result, output_path):
                print(f"✅ Processed: {os.path.basename(json_path)}")
                return True, json_path

        except Exception as e:
            print(f"Error processing {os.path.basename(json_path)}: {e}")

    return False, json_path


def step2_classify_continuations(prompt_path: str, input_dir: str, output_dir: str, max_workers: int = None):
    """Step 3.2: Classify continuations using LLM.

    Args:
        prompt_path: Path to prompt file.
        input_dir: Input directory.
        output_dir: Output directory.
        max_workers: Max concurrent workers.
    """
    max_workers = max_workers or config.api.max_workers

    prompt = read_file(prompt_path)
    if not prompt:
        print("Cannot read prompt file")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    json_files = []
    for root, _, files in os.walk(input_dir):
        for f in files:
            if f.endswith('.json'):
                json_files.append(os.path.join(root, f))

    if not json_files:
        print(f"No JSON files found in {input_dir}")
        return

    print(f"Found {len(json_files)} JSON files")

    tasks = []
    for json_path in json_files:
        output_path = json_path.replace(input_dir, output_dir)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if not os.path.exists(output_path):
            tasks.append((prompt, json_path, output_path))

    print(f"Processing {len(tasks)} files...")

    client = get_client()

    successful = 0
    failed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(process_single_continuation, p, j, o, client): (j, o)
            for p, j, o in tasks
        }

        for future in concurrent.futures.as_completed(future_to_task):
            success, path = future.result()
            if success:
                successful += 1
            else:
                failed += 1

    print(f"✅ Completed: {successful} successful, {failed} failed")


# =============================================================================
# Step 3.3: Merge Continuations
# =============================================================================

def parse_timestamp(ts) -> float:
    """Converts both float seconds and 'HH:MM:SS,mmm' strings into float seconds."""
    if isinstance(ts, (int, float)):
        return float(ts)
    elif isinstance(ts, str):
        ts = ts.replace(',', '.')
        parts = ts.split(':')
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        else:
            return float(ts)
    return 0.0


def merge_continuations_in_file(input_path: str, output_path: str, max_duration: float = 8.0) -> str:
    """Reads the unified JSON, merges continuations, and saves the output.

    Args:
        input_path: Input JSON path.
        output_path: Output JSON path.
        max_duration: Maximum duration in seconds.

    Returns:
        Status message.
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        merged_results = []

        if not isinstance(data, list):
            data = [data]

        for item in data:
            target = item.get("target", {})
            merged_text_parts = [target.get("text", "").strip()]

            start_time = parse_timestamp(target.get("start"))
            current_end_time = parse_timestamp(target.get("end"))

            for ctx in item.get("context_next", []):
                if ctx.get("is_continuation") is True:
                    candidate_end = parse_timestamp(ctx.get("end"))
                    projected_duration = candidate_end - start_time

                    if projected_duration <= max_duration:
                        utterance_text = ctx.get("text", "").strip()
                        if utterance_text:
                            merged_text_parts.append(utterance_text)
                            current_end_time = candidate_end
                    else:
                        break
                else:
                    break

            merged_item = {
                "meta": item.get("meta"),
                "bullet": item.get("bullet"),
                "target_analysis": item.get("target_analysis"),
                "merged_response": {
                    "text": " ".join(merged_text_parts),
                    "start": round(start_time, 3),
                    "end": round(current_end_time, 3),
                    "total_duration": round(current_end_time - start_time, 3)
                }
            }
            merged_results.append(merged_item)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_results, f, indent=2, ensure_ascii=False)

        return f"Success: {output_path}"

    except Exception as e:
        return f"Error processing {input_path}: {str(e)}"


def step3_merge_continuations(input_dir: str, output_dir: str, max_duration: float = 8.0):
    """Step 3.3: Merge continuations.

    Args:
        input_dir: Input directory.
        output_dir: Output directory.
        max_duration: Maximum duration in seconds.
    """
    from pathlib import Path

    input_path_obj = Path(input_dir)
    json_files = input_path_obj.rglob("*.json")
    relative_paths = [str(p.relative_to(input_path_obj)) for p in json_files]

    if not relative_paths:
        print(f"No JSON files found in {input_dir}")
        return

    print(f"Found {len(relative_paths)} files. Starting processing...")

    successes = 0
    for rel_path in relative_paths:
        input_path = os.path.join(input_dir, rel_path)
        output_path = os.path.join(output_dir, rel_path)
        result = merge_continuations_in_file(input_path, output_path, max_duration)
        if result.startswith("Success"):
            successes += 1

    print(f"Successfully merged: {successes}/{len(relative_paths)} files.")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Stage 3: Continuation Processing")
    parser.add_argument("--step", choices=['1', '2', '3', 'all'], default='all', help="Which step to run")
    parser.add_argument("--prompt", help="Path to prompt file (for step 2)")
    parser.add_argument("--input-dir", required=True, help="Input directory")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--max-workers", type=int, default=None, help="Max concurrent workers")
    parser.add_argument("--max-duration", type=float, default=8.0, help="Max duration for merging (seconds)")
    args = parser.parse_args()

    if args.step == '1':
        step1_add_context(args.input_dir, args.output_dir, args.max_workers)
    elif args.step == '2':
        if not args.prompt:
            print("Error: --prompt is required for step 2")
            sys.exit(1)
        step2_classify_continuations(args.prompt, args.input_dir, args.output_dir, args.max_workers)
    elif args.step == '3':
        step3_merge_continuations(args.input_dir, args.output_dir, args.max_duration)
    else:
        print("Running all steps requires intermediate directories. Use individual steps.")


if __name__ == "__main__":
    main()
