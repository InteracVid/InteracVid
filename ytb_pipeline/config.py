"""Configuration module for YouTube Reaction Pipeline."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class APIConfig:
    """API configuration settings."""
    # Gemini API settings
    gemini_api_key: str = field(default_factory=lambda: os.environ.get('GEMINI_API_KEY', ''))
    gemini_endpoint: str = field(default_factory=lambda: os.environ.get(
        'GEMINI_ENDPOINT',
        'https://generativelanguage.googleapis.com/v1beta'
    ))
    gemini_model: str = 'gemini-2.0-flash'

    # OpenAI-compatible API settings (for alternative LLM providers)
    openai_api_key: str = field(default_factory=lambda: os.environ.get('OPENAI_API_KEY', ''))
    openai_base_url: str = field(default_factory=lambda: os.environ.get(
        'OPENAI_BASE_URL',
        'https://api.openai.com/v1'
    ))
    openai_model: str = 'gpt-4'

    # LLM provider selection: "gemini" or "openai"
    llm_provider: str = field(default_factory=lambda: os.environ.get('LLM_PROVIDER', 'gemini'))

    # Concurrency settings
    max_workers: int = field(default_factory=lambda: int(os.environ.get('MAX_WORKERS', '30')))


@dataclass
class PathsConfig:
    """Path configuration settings."""
    input_dir: str = field(default_factory=lambda: os.environ.get('INPUT_DIR', './data/input'))
    output_dir: str = field(default_factory=lambda: os.environ.get('OUTPUT_DIR', './data/output'))
    prompts_dir: str = field(default_factory=lambda: os.environ.get('PROMPTS_DIR', './prompts'))


@dataclass
class ProcessingConfig:
    """Processing configuration settings."""
    # Timestamp offsets for video segments (in seconds)
    start_offset: float = 0.0
    end_offset: float = 0.0

    # Retry settings
    max_retries: int = 10
    retry_delay: float = 1.0

    # API settings
    max_tokens: int = 65536


@dataclass
class Config:
    """Main configuration class."""
    api: APIConfig = field(default_factory=APIConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)

    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables."""
        return cls()


# Global configuration instance
config = Config.from_env()
