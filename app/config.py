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

# Primary model.  Groq deprecates models every few months — if a run fails
# with 404 model_not_found, the agent falls through LLM_MODEL_FALLBACKS
# below (env-overridable, comma-separated).  Check the current list at
# https://console.groq.com/docs/models before pinning a new primary.
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")

# All currently-live Groq chat models suitable for summarization
# (as of 2026-08-20). Kept ordered smallest -> largest so we upshift
# only when a smaller model is gone. Refresh from the live list with:
#   curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"
_DEFAULT_FALLBACKS = ",".join(
    [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "qwen/qwen3.6-27b",
    ]
)
LLM_MODEL_FALLBACKS: List[str] = [
    m.strip() for m in os.getenv("LLM_MODEL_FALLBACKS", _DEFAULT_FALLBACKS).split(",") if m.strip()
]
