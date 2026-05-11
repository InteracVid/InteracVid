"""Utility functions for YouTube Reaction Pipeline."""

import json
import os
import time
from typing import Optional, Dict, Any, List


def read_file(file_path: str) -> Optional[str]:
    """Read file content.

    Args:
        file_path: Path to the file to read.

    Returns:
        File content as string, or None if reading fails.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None


def write_json(data: Any, file_path: str, ensure_ascii: bool = False, indent: int = 2) -> bool:
    """Write data to JSON file.

    Args:
        data: Data to write.
        file_path: Path to the output file.
        ensure_ascii: Whether to escape non-ASCII characters.
        indent: Indentation level for pretty printing.

    Returns:
        True if successful, False otherwise.
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
        return True
    except Exception as e:
        print(f"Error writing JSON file {file_path}: {e}")
        return False


def read_json(file_path: str) -> Optional[Any]:
    """Read JSON file.

    Args:
        file_path: Path to the JSON file.

    Returns:
        Parsed JSON data, or None if reading fails.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading JSON file {file_path}: {e}")
        return None


def parse_json_response(response_text: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from API response, handling markdown code blocks.

    Args:
        response_text: Raw response text from API.

    Returns:
        Parsed JSON data, or None if parsing fails.
    """
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Try removing markdown code blocks
        try:
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except json.JSONDecodeError:
            print(f"Failed to parse JSON response: {response_text[:100]}...")
            return None


def get_files_by_extension(directory: str, extension: str) -> List[str]:
    """Get all files with a specific extension in a directory.

    Args:
        directory: Directory to search.
        extension: File extension to filter (e.g., '.json', '.srt').

    Returns:
        List of file paths.
    """
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(extension):
                files.append(os.path.join(root, filename))
    return files


def retry_on_failure(func, max_retries: int = 10, delay: float = 1.0, *args, **kwargs):
    """Retry a function on failure.

    Args:
        func: Function to call.
        max_retries: Maximum number of retry attempts.
        delay: Delay between retries in seconds.
        *args: Arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        Function result, or None if all retries fail.
    """
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"All {max_retries} attempts failed.")
                raise
    return None
