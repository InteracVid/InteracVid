"""YouTube Reaction Pipeline

A multi-stage pipeline for processing YouTube videos to identify and extract
reactive segments from live streams or videos.

Pipeline Stages:
1. Transcript Processing: Convert SRT subtitles to structured JSON
2. Reaction Filter: Classify sentences as reactive/proactive/continuation
3. Continuation Merging: Merge reactive responses with continuations
4. VLM Processing: Analyze video content with vision-language models
5. Temporal Refinement: Adjust segment timing
6. Bullet Creation: Generate summaries
7. Video Cutting: Extract video clips using FFmpeg

Usage:
    from ytb_pipeline import config, get_client
    from ytb_pipeline.stages import stage1_transcript, stage2_reaction

    # Configure via environment variables
    export GEMINI_API_KEY=your_key_here
    export OPENAI_API_KEY=your_key_here

    # Or use the config module
    from ytb_pipeline.config import Config, APIConfig
    config = Config(api=APIConfig(gemini_api_key='your_key'))
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from .config import config, Config, APIConfig, PathsConfig, ProcessingConfig
from .utils import get_client, read_file, write_json, read_json
from . import stages
from . import utils

__all__ = [
    'config',
    'Config',
    'APIConfig',
    'PathsConfig',
    'ProcessingConfig',
    'get_client',
    'read_file',
    'write_json',
    'read_json',
    'stages',
    'utils',
]
