"""Generate Digest rows for content that has been processed but not yet summarized."""
from __future__ import annotations

import logging

from ..agent import DigestAgent
from ..database import Repository
from .base import ProcessService


log = logging.getLogger(__name__)


class ProcessDigest(ProcessService):
    name = "process_digests"

    def __init__(self):
        self.agent = DigestAgent()

    def _run(self, repo: Repository) -> int:
        n = 0

        for art in repo.anthropic_needing_digest():
            result = self.agent.summarize(
                title=art.title, body=art.markdown or "", source="Anthropic blog"
            )
            repo.create_digest(
                source_type="anthropic",
                title=art.title,
                url=art.url,
                summary=result.summary,
                published_at=art.published_at,
                anthropic_article_id=art.id,
            )
            n += 1

        for art in repo.openai_needing_digest():
            result = self.agent.summarize(
                title=art.title, body=art.markdown or "", source="OpenAI blog"
            )
            repo.create_digest(
                source_type="openai",
                title=art.title,
                url=art.url,
                summary=result.summary,
                published_at=art.published_at,
                openai_article_id=art.id,
            )
            n += 1

        for vid in repo.youtube_needing_digest():
            result = self.agent.summarize(
                title=vid.title,
                body=vid.transcript or vid.description or "",
                source=f"YouTube — {vid.channel_title or vid.channel_id}",
            )
            repo.create_digest(
                source_type="youtube",
                title=vid.title,
                url=vid.url,
                summary=result.summary,
                published_at=vid.published_at,
                youtube_video_id=vid.id,
            )
            n += 1

        return n


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ProcessDigest().run()


if __name__ == "__main__":
    main()
