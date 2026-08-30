"""Describe an image with a vision model — used for captioning campaign art.

Unlike the session notetaker (which runs on OCI-hosted models via litellm),
this talks to OpenAI directly and needs `OPENAI_API_KEY` in `.env`.
"""

import base64
import mimetypes
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")
DEFAULT_PROMPT = "What is in this image?"


def _client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY must be set in .env")
    return OpenAI(api_key=key)


def _describe(image_url: str, prompt: str, max_tokens: int) -> str:
    response = _client().chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
    )
    return response.choices[0].message.content


def analyze_image_from_url(
    image_url: str, prompt: str = DEFAULT_PROMPT, max_tokens: int = 300
) -> str:
    """Describe an image hosted at a URL."""
    return _describe(image_url, prompt, max_tokens)


def analyze_image_from_file(
    image_path: str | Path, prompt: str = DEFAULT_PROMPT, max_tokens: int = 300
) -> str:
    """Describe a local image file, sent inline as a base64 data URL."""
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {path}")

    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return _describe(f"data:{mime};base64,{encoded}", prompt, max_tokens)


def analyze(target: str, prompt: str = DEFAULT_PROMPT, max_tokens: int = 300) -> str:
    """Describe an image given either a URL or a local path."""
    if target.startswith(("http://", "https://")):
        return analyze_image_from_url(target, prompt, max_tokens)
    return analyze_image_from_file(target, prompt, max_tokens)
