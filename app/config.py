"""Static configuration: source lists and tunables.

Secrets live in the environment (see `app/example.env`).
"""
import os
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class YouTubeChannel:
    channel_id: str
    name: str


# Curated AI-focused channels. Add/remove as desired.
YOUTUBE_CHANNELS: List[YouTubeChannel] = [
    YouTubeChannel("UCXZCJLdBC09xxGZ6gcdrc6A", "OpenAI"),
    YouTubeChannel("UCrDwWp7EBBv4NwvScIpBDOA", "Anthropic"),
    YouTubeChannel("UCbfYPyITQ-7l4upoX8nvctg", "Two Minute Papers"),
    YouTubeChannel("UCv83tO5cePwHMt1952IVVHw", "AI Explained"),
    YouTubeChannel("UCcAlTqd9zID6aLX3i_jjE2g", "Matthew Berman"),
]


# Tunables (env-overridable)
DIGEST_LOOKBACK_HOURS = int(os.getenv("DIGEST_LOOKBACK_HOURS", "24"))
EMAIL_TOP_N = int(os.getenv("EMAIL_TOP_N", "10"))
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
