# YouTube Reaction Pipeline

A multi-stage pipeline for processing YouTube videos to identify and extract reactive segments from live streams or videos.

## Overview

This pipeline processes YouTube videos through multiple stages to identify moments where streamers react to audience interactions (chat messages, donations, etc.) and extracts those segments as video clips.

### Stage 1: Transcript Processing
Converts raw SRT subtitle files into structured JSON transcripts with merged sentences and timestamps.

**Prompt Files:**
- `prompts/stage1/prompt_v1.txt`
- `prompts/stage1/prompt_v2.txt` (recommended)

**Output:** JSON array with `start`, `end`, `text` fields for each sentence.

### Stage 2: Reaction Filter
Classifies each sentence as:
- `reactive_response`: Response to audience interaction (chat, donations)
- `proactive_monologue`: Self-initiated speech
- `continuation`: Continuation of previous segment

**Prompt Files:**
- `prompts/stage2/prompt_v7_wob.txt` (without bullet)
- `prompts/stage2/prompt_v10.txt` (with bullet candidates)

**Output:** JSON with added `type` and `reason` fields.

### Stage 3: Continuation Processing
Three sub-steps:
1. **Add Context:** Extract following sentences as context for reactive responses
2. **Classify:** Use LLM to determine if context sentences are true continuations
3. **Merge:** Combine reactive responses with their continuations

**Prompt Files:**
- `prompts/stage3/prompt_v4.txt` (recommended)

**Output:** Merged response units with `merged_response` field.

### Stage 4: VLM Processing
Uses vision-language models (Gemini) to analyze video content:
- Count humans in the video
- Detect scene cuts and multiscreen layouts
- Rate content-transcript relevance (DIRECT/THEMATIC/UNRELATED)

**Prompt Files:**
- `prompts/stage4/prompt_v4.txt` (classification)
- `prompts/stage4/prompt_caption_v*.txt` (captioning)
- `prompts/stage4/prompt_query_v*.txt` (query processing)

**Output:** JSON with `human_count`, `scene_cut`, `multiscreen`, `relevance` fields.

### Stage 5: Temporal Refinement
Refines timing of segments with temporal offsets:
- Exact temporal localization
- ASR correction with context

**Prompt Files:**
- `prompts/stage5/prompt_v2.txt` (recommended)

**Output:** Corrected timestamps and transcripts.

### Stage 6: Bullet Creation
Generates concise summaries/annotations of reaction segments.

**Prompt Files:**
- `prompts/stage6/prompt_v2.txt` (recommended)

**Output:** Summarized reaction segments.

### Stage 7: Video Cutting
Extracts video clips using FFmpeg based on processed timestamps.

**Input:** Video file + JSON with timestamps

**Output:** Individual video clips (`reactive_chunk_*.mp4`)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ytb-pipeline.git
cd ytb-pipeline

# Install dependencies
pip install -r requirements.txt

# Install FFmpeg (required for video cutting)
# Ubuntu/Debian:
sudo apt-get install ffmpeg

# macOS:
brew install ffmpeg
```

## Configuration

Set up environment variables:

```bash
# Copy example env file
cp .env.example .env

# Edit with your API keys
export GEMINI_API_KEY=your_gemini_api_key
export OPENAI_API_KEY=your_openai_api_key  # optional
export LLM_PROVIDER=gemini  # or 'openai'
export MAX_WORKERS=30
```

Or configure programmatically:

```python
from ytb_pipeline import config

# Update configuration
config.api.gemini_api_key = "your_key"
config.api.max_workers = 50
```

## Usage

### Command Line

```bash
# Stage 1: Process transcripts
python -m ytb_pipeline.stages.stage1_transcript \
    --prompt ytb_pipeline/prompts/stage1/prompt_v2.txt \
    --input-dir data/srt_files \
    --output-dir data/stage1_output

# Stage 2: Filter reactions
python -m ytb_pipeline.stages.stage2_reaction \
    --prompt ytb_pipeline/prompts/stage2/prompt_v7_wob.txt \
    --input-dir data/stage1_output \
    --output-dir data/stage2_output

# Stage 3: Continuation processing
# Step 3.1: Add context
python -m ytb_pipeline.stages.stage3_continuation \
    --step 1 \
    --input-dir data/stage2_output \
    --output-dir data/stage3_step1

# Step 3.2: Classify continuations
python -m ytb_pipeline.stages.stage3_continuation \
    --step 2 \
    --prompt ytb_pipeline/prompts/stage3/prompt_v4.txt \
    --input-dir data/stage3_step1 \
    --output-dir data/stage3_step2

# Step 3.3: Merge continuations
python -m ytb_pipeline.stages.stage3_continuation \
    --step 3 \
    --input-dir data/stage3_step2 \
    --output-dir data/stage3_output \
    --max-duration 8.0

# Stage 4: VLM processing
python -m ytb_pipeline.stages.stage4_vlm \
    --prompt ytb_pipeline/prompts/stage4/prompt_v4.txt \
    --input-dir data/stage3_output \
    --output-dir data/stage4_output

# Stage 5: Temporal refinement
python -m ytb_pipeline.stages.stage5_temporal \
    --prompt ytb_pipeline/prompts/stage5/prompt_v2.txt \
    --input-dir data/stage4_output \
    --output-dir data/stage5_output \
    --start-offset -2.0 \
    --end-offset 2.0

# Stage 6: Bullet creation
python -m ytb_pipeline.stages.stage6_bullet \
    --prompt ytb_pipeline/prompts/stage6/prompt_v2.txt \
    --input-dir data/stage5_output \
    --output-dir data/stage6_output

# Stage 7: Cut videos
python -m ytb_pipeline.stages.stage7_cut \
    --video-path input_video.mp4 \
    --json-path data/stage6_output/processed.json \
    --output-dir output_chunks
```

### Python API

```python
from ytb_pipeline import get_client, read_file, write_json
from ytb_pipeline.stages import (
    cut_video_segment,
    identify_reactive_segments,
    merge_continuations_in_file,
)

# Use LLM client
client = get_client("gemini")
response = client.generate("Your prompt here")

# Process video segments
segments = read_json("segments.json")
reactive_groups = identify_reactive_segments(segments)

for group in reactive_groups:
    cut_video_segment(
        video_path="video.mp4",
        start_seconds=group["start"],
        end_seconds=group["end"],
        output_path=f"output/chunk_{group['id']}.mp4"
    )

# Merge continuations
merge_continuations_in_file(
    "input.json",
    "output.json",
    max_duration=8.0
)
```

## Project Structure

```
ytb_pipeline/
├── __init__.py
├── config.py              # Configuration management
├── stages/
│   ├── __init__.py
│   ├── stage1_transcript.py    # SRT to JSON
│   ├── stage2_reaction.py      # Reaction classification
│   ├── stage3_continuation.py  # Context & merging
│   ├── stage4_vlm.py           # Video analysis
│   ├── stage5_temporal.py      # Timestamp refinement
│   ├── stage6_bullet.py        # Summary generation
│   └── stage7_cut.py           # Video cutting
├── utils/
│   ├── __init__.py
│   ├── api_client.py      # LLM API clients
│   ├── file_utils.py      # File I/O utilities
│   └── timestamp_utils.py # Timestamp handling
└── prompts/               # Prompt templates
    ├── stage1/
    │   ├── prompt_v1.txt
    │   └── prompt_v2.txt
    ├── stage2/
    │   ├── prompt_v7_wob.txt
    │   └── prompt_v10.txt
    ├── stage3/
    │   └── prompt_v4.txt
    ├── stage4/
    │   ├── prompt_v4.txt
    │   ├── prompt_caption_v*.txt
    │   └── prompt_query_v*.txt
    ├── stage5/
    │   └── prompt_v2.txt
    └── stage6/
        └── prompt_v2.txt
```

## Requirements

- Python 3.8+
- FFmpeg (for video cutting)
- API keys for:
  - Google Gemini (for VLM processing)
  - OpenAI or compatible API (optional, for text processing)

## API Costs

This pipeline makes extensive API calls. Be aware of:
- Gemini API pricing for video analysis
- Token limits and quotas
- Consider using batch processing for large datasets

## Data Flow Example

```
Input: video.srt
    │
    ▼ Stage 1: Transcript Processing
[{"start": "00:00:01,000", "end": "00:00:05,000", "text": "Hello everyone!"}, ...]
    │
    ▼ Stage 2: Reaction Filter
[{"text": "Hello everyone!", "type": "proactive_monologue"}, 
 {"text": "Thanks for the sub!", "type": "reactive_response"}, ...]
    │
    ▼ Stage 3: Continuation Processing
[{"merged_response": {"text": "Thanks for the sub! I really appreciate it.", 
                      "start": 10.5, "end": 15.2}, ...}]
    │
    ▼ Stage 4: VLM Processing
[{..., "api_response": {"human_count": 1, "relevance": {"rating": "DIRECT"}}}]
    │
    ▼ Stage 5-6: Temporal & Summary
[{..., "corrected_transcript": "...", "bullet_summary": "..."}]
    │
    ▼ Stage 7: Video Cutting
Output: reactive_chunk_001.mp4, reactive_chunk_002.mp4, ...
```

## License

MIT License

## Contributing

Contributions are welcome! Please read the contributing guidelines first.

## Acknowledgments

- Google Gemini API for vision-language processing
- OpenAI API for text processing
- FFmpeg for video manipulation
