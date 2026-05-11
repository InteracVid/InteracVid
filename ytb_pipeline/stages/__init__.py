"""Pipeline stages for YouTube Reaction Pipeline.

Stage 1: Transcript Processing - Convert SRT to structured JSON
Stage 2: Reaction Filter - Classify sentences as reactive/proactive/continuation
Stage 3: Continuation Processing - Add context and merge continuations
Stage 4: VLM Processing - Analyze video content with vision-language models
Stage 5: Temporal Refinement - Adjust segment timing
Stage 6: Bullet Creation - Generate summaries
Stage 7: Video Cutting - Extract video clips using FFmpeg
"""

from .stage1_transcript import process_single_srt
from .stage2_reaction import process_single_json as process_reaction
from .stage3_continuation import (
    step1_add_context,
    step2_classify_continuations,
    step3_merge_continuations,
    merge_continuations_in_file,
)
from .stage4_vlm import process_single_json as process_vlm
from .stage5_temporal import process_single_json as process_temporal
from .stage6_bullet import process_single_json as process_bullet
from .stage7_cut import cut_video_segment, identify_reactive_segments

__all__ = [
    # Stage 1
    'process_single_srt',
    # Stage 2
    'process_reaction',
    # Stage 3
    'step1_add_context',
    'step2_classify_continuations',
    'step3_merge_continuations',
    'merge_continuations_in_file',
    # Stage 4
    'process_vlm',
    # Stage 5
    'process_temporal',
    # Stage 6
    'process_bullet',
    # Stage 7
    'cut_video_segment',
    'identify_reactive_segments',
]
