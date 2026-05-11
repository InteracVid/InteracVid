"""API clients for LLM interactions."""

import json
import time
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from ..config import config


class BaseLLMClient(ABC):
    """Base class for LLM clients."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate response from the LLM.

        Args:
            prompt: Input prompt.
            **kwargs: Additional arguments.

        Returns:
            Generated text response.
        """
        pass


class GeminiClient(BaseLLMClient):
    """Gemini API client."""

    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None, model: Optional[str] = None):
        from google import genai

        self.api_key = api_key or config.api.gemini_api_key
        self.endpoint = endpoint or config.api.gemini_endpoint
        self.model = model or config.api.gemini_model

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set. Please set it in environment variables.")

        self.client = genai.Client(
            api_key=self.api_key,
        )

    def generate(self, prompt: str, max_tokens: int = 65536, **kwargs) -> Optional[str]:
        """Generate response using Gemini API."""
        max_retries = config.processing.max_retries

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                print(f"Gemini API error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(config.processing.retry_delay)

        return None

    def generate_with_video(
        self,
        prompt: str,
        video_url: str,
        start_offset: str,
        end_offset: str,
        **kwargs
    ) -> Optional[str]:
        """Generate response with video input.

        Args:
            prompt: Text prompt.
            video_url: URL to the video.
            start_offset: Start timestamp (e.g., '10.000s').
            end_offset: End timestamp (e.g., '20.000s').

        Returns:
            Generated text response.
        """
        max_retries = config.processing.max_retries

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[{
                        "role": "user",
                        "parts": [
                            {
                                "file_data": {
                                    "file_uri": video_url,
                                    "mime_type": "video/*"
                                },
                                "video_metadata": {
                                    "start_offset": start_offset,
                                    "end_offset": end_offset
                                }
                            },
                            {"text": prompt}
                        ]
                    }]
                )
                return response.text
            except Exception as e:
                print(f"Gemini API error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(config.processing.retry_delay)

        return None


class OpenAIClient(BaseLLMClient):
    """OpenAI-compatible API client."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        from openai import OpenAI

        self.api_key = api_key or config.api.openai_api_key
        self.base_url = base_url or config.api.openai_base_url
        self.model = model or config.api.openai_model

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set. Please set it in environment variables.")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def generate(self, prompt: str, max_tokens: int = 4096, **kwargs) -> Optional[str]:
        """Generate response using OpenAI-compatible API."""
        max_retries = config.processing.max_retries

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"OpenAI API error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(config.processing.retry_delay)

        return None


def get_client(provider: Optional[str] = None) -> BaseLLMClient:
    """Get the appropriate LLM client based on configuration.

    Args:
        provider: LLM provider ('gemini' or 'openai'). If None, uses config.

    Returns:
        LLM client instance.
    """
    provider = provider or config.api.llm_provider

    if provider == "gemini":
        return GeminiClient()
    elif provider == "openai":
        return OpenAIClient()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
