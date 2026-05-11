"""Example script demonstrating the YouTube Reaction Pipeline.

This script shows how to use the pipeline to:
1. Process SRT transcripts
2. Classify reactions
3. Cut video segments
"""

import os
from ytb_pipeline import config, get_client, read_file, write_json
from ytb_pipeline.utils import timestamp_to_seconds, seconds_to_timestamp


def example_llm_usage():
    """Example: Using the LLM client directly."""
    print("=== LLM Client Example ===")

    # Initialize client (uses config from environment)
    client = get_client()

    # Generate text
    prompt = "What is the capital of France?"
    response = client.generate(prompt)

    print(f"Prompt: {prompt}")
    print(f"Response: {response}")
    print()


def example_config():
    """Example: Configuration management."""
    print("=== Configuration Example ===")

    print(f"LLM Provider: {config.api.llm_provider}")
    print(f"Max Workers: {config.api.max_workers}")
    print(f"Input Directory: {config.paths.input_dir}")
    print()


def example_timestamp_utils():
    """Example: Timestamp utilities."""
    print("=== Timestamp Utilities Example ===")

    # SRT timestamp to seconds
    srt_time = "00:01:30,500"
    seconds = timestamp_to_seconds(srt_time)
    print(f"SRT timestamp '{srt_time}' = {seconds} seconds")

    # Seconds to SRT timestamp
    back_to_srt = seconds_to_timestamp(seconds)
    print(f"{seconds} seconds = SRT timestamp '{back_to_srt}'")
    print()


def example_cut_video():
    """Example: Cutting video segments."""
    print("=== Video Cutting Example ===")

    from ytb_pipeline.stages import cut_video_segment

    # Example segment data
    segments = [
        {"type": "reactive_response", "start": "00:01:00,000", "end": "00:01:15,000"},
        {"type": "continuation", "start": "00:01:15,000", "end": "00:01:20,000"},
        {"type": "proactive_monologue", "start": "00:01:20,000", "end": "00:01:30,000"},
        {"type": "reactive_response", "start": "00:01:30,000", "end": "00:01:45,000"},
    ]

    # Identify reactive groups
    from ytb_pipeline.stages import identify_reactive_segments
    groups = identify_reactive_segments(segments)

    print(f"Found {len(groups)} reactive groups:")
    for i, group in enumerate(groups, 1):
        print(f"  Group {i}: {group['start']} -> {group['end']} ({len(group['segments'])} segments)")
    print()


def main():
    """Run all examples."""
    print("YouTube Reaction Pipeline - Examples")
    print("=" * 50)
    print()

    # Check configuration
    if not config.api.gemini_api_key and not config.api.openai_api_key:
        print("Warning: No API key configured.")
        print("Set GEMINI_API_KEY or OPENAI_API_KEY in your environment.")
        print()

    example_config()
    example_timestamp_utils()
    example_cut_video()

    # Only run LLM example if API key is configured
    if config.api.gemini_api_key or config.api.openai_api_key:
        example_llm_usage()
    else:
        print("Skipping LLM example - no API key configured.")

    print("=" * 50)
    print("Examples completed!")


if __name__ == "__main__":
    main()
