"""Image loading utility for VLM prompt tuning.

Handles fetching and encoding images from URLs or local file paths,
and building provider-specific content blocks.
"""
from __future__ import annotations

import base64
import mimetypes
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_SUPPORTED_MEDIA_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}

_EXT_TO_MEDIA: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


@dataclass(frozen=True)
class ImageData:
    base64_data: str
    media_type: str
    source_url: str


def _detect_media_type(source: str, content_type: str | None = None) -> str:
    """Detect media type from content-type header or file extension."""
    if content_type:
        # Strip parameters like charset
        mt = content_type.split(";")[0].strip().lower()
        if mt in _SUPPORTED_MEDIA_TYPES:
            return mt

    # Fallback to extension
    ext = Path(source.split("?")[0]).suffix.lower()
    return _EXT_TO_MEDIA.get(ext, "image/png")


async def load_image(source: str) -> ImageData:
    """Load an image from a URL or local file path and return base64-encoded data."""
    if source.startswith(("http://", "https://")):
        return await _load_from_url(source)
    return _load_from_file(source)


async def _load_from_url(url: str) -> ImageData:
    """Fetch image from HTTP/HTTPS URL."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()

    content_type = response.headers.get("content-type")
    media_type = _detect_media_type(url, content_type)
    b64 = base64.b64encode(response.content).decode("utf-8")
    return ImageData(base64_data=b64, media_type=media_type, source_url=url)


def _load_from_file(path: str) -> ImageData:
    """Load image from local file path."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    media_type = _detect_media_type(path)
    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    return ImageData(base64_data=b64, media_type=media_type, source_url=path)


# ---- In-memory cache for loaded images ----
_image_cache: dict[str, ImageData] = {}
_CACHE_MAX_SIZE = 200


async def load_image_cached(source: str) -> ImageData:
    """Load image with in-memory LRU-style caching."""
    if source in _image_cache:
        return _image_cache[source]

    data = await load_image(source)

    # Simple eviction: clear half when full
    if len(_image_cache) >= _CACHE_MAX_SIZE:
        keys = list(_image_cache.keys())
        for k in keys[: len(keys) // 2]:
            del _image_cache[k]

    _image_cache[source] = data
    return data


# ---- Provider-specific content block builders ----

async def build_openai_image_content(source: str) -> dict:
    """Build an OpenAI-compatible image_url content block.

    For URLs: passes through directly.
    For local files: converts to data URI.
    """
    if source.startswith(("http://", "https://")):
        return {
            "type": "image_url",
            "image_url": {"url": source},
        }

    img = await load_image_cached(source)
    data_uri = f"data:{img.media_type};base64,{img.base64_data}"
    return {
        "type": "image_url",
        "image_url": {"url": data_uri},
    }


async def build_anthropic_image_content(source: str) -> dict:
    """Build an Anthropic-compatible image content block."""
    img = await load_image_cached(source)
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": img.media_type,
            "data": img.base64_data,
        },
    }


def is_image_url(value: str) -> bool:
    """Heuristic check if a string looks like an image URL or path."""
    if not isinstance(value, str):
        return False
    v = value.strip().lower()
    if v.startswith(("http://", "https://")):
        # Check extension in URL
        path_part = v.split("?")[0]
        return any(path_part.endswith(ext) for ext in _EXT_TO_MEDIA)
    # Local file check
    return any(v.endswith(ext) for ext in _EXT_TO_MEDIA)
