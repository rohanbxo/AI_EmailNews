"""Fetch transcripts for pending YouTube videos."""
from __future__ import annotations

import logging
import os
from typing import Optional

from ..database import Repository
from .base import ProcessService


log = logging.getLogger(__name__)


def _build_transcript_api():
    from youtube_transcript_api import YouTubeTranscriptApi  # local import keeps optional dep lazy

    username = os.getenv("WEBSHARE_USERNAME")
    password = os.getenv("WEBSHARE_PASSWORD")
    if username and password:
        try:
            from youtube_transcript_api.proxies import WebshareProxyConfig

            return YouTubeTranscriptApi(
                proxy_config=WebshareProxyConfig(
                    proxy_username=username, proxy_password=password
                )
            )
        except Exception as e:  # noqa: BLE001
            log.warning("Webshare proxy config failed (%s); continuing without proxy.", e)
    return YouTubeTranscriptApi()


def fetch_transcript(video_id: str) -> Optional[str]:
    api = _build_transcript_api()
    try:
        fetched = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
        snippets = getattr(fetched, "snippets", fetched)
        return " ".join(s.text if hasattr(s, "text") else s["text"] for s in snippets).strip()
    except Exception as e:  # noqa: BLE001
        log.info("No transcript for %s: %s", video_id, e)
        return None


class ProcessYouTube(ProcessService):
    name = "process_youtube_transcripts"

    def _run(self, repo: Repository) -> int:
        n = 0
        for video in repo.youtube_needing_transcript():
            transcript = fetch_transcript(video.video_id)
            if transcript:
                video.transcript = transcript
                video.transcript_status = "ok"
                n += 1
            else:
                video.transcript_status = "unavailable"
        return n


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ProcessYouTube().run()


if __name__ == "__main__":
    main()
