from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from .models import AnthropicArticle, Digest, OpenAIArticle, YouTubeVideo


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Repository:
    """Data access for scraped content and digests.

    Bulk-create methods use Postgres ON CONFLICT DO NOTHING so reruns are idempotent.
    """

    def __init__(self, session: Session):
        self.session = session

    # -- Bulk inserts ---------------------------------------------------------

    def _bulk_insert_ignore(self, model, rows: List[dict], conflict_cols: List[str]) -> int:
        if not rows:
            return 0
        stmt = pg_insert(model).values(rows).on_conflict_do_nothing(index_elements=conflict_cols)
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount or 0

    def bulk_create_anthropic_articles(self, rows: List[dict]) -> int:
        return self._bulk_insert_ignore(AnthropicArticle, rows, ["url"])

    def bulk_create_openai_articles(self, rows: List[dict]) -> int:
        return self._bulk_insert_ignore(OpenAIArticle, rows, ["url"])

    def bulk_create_youtube_videos(self, rows: List[dict]) -> int:
        return self._bulk_insert_ignore(YouTubeVideo, rows, ["video_id"])

    # -- Fetchers for processors ---------------------------------------------

    def anthropic_needing_markdown(self, limit: int = 50) -> List[AnthropicArticle]:
        stmt = (
            select(AnthropicArticle)
            .where(AnthropicArticle.markdown.is_(None))
            .order_by(AnthropicArticle.published_at.desc().nullslast())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def openai_needing_markdown(self, limit: int = 50) -> List[OpenAIArticle]:
        stmt = (
            select(OpenAIArticle)
            .where(OpenAIArticle.markdown.is_(None))
            .order_by(OpenAIArticle.published_at.desc().nullslast())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def youtube_needing_transcript(self, limit: int = 50) -> List[YouTubeVideo]:
        stmt = (
            select(YouTubeVideo)
            .where(YouTubeVideo.transcript_status == "pending")
            .order_by(YouTubeVideo.published_at.desc().nullslast())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    # -- Digest building ------------------------------------------------------

    def anthropic_needing_digest(self, limit: int = 50) -> List[AnthropicArticle]:
        stmt = (
            select(AnthropicArticle)
            .outerjoin(Digest, Digest.anthropic_article_id == AnthropicArticle.id)
            .where(Digest.id.is_(None))
            .where(AnthropicArticle.markdown.is_not(None))
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def openai_needing_digest(self, limit: int = 50) -> List[OpenAIArticle]:
        stmt = (
            select(OpenAIArticle)
            .outerjoin(Digest, Digest.openai_article_id == OpenAIArticle.id)
            .where(Digest.id.is_(None))
            .where(OpenAIArticle.markdown.is_not(None))
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def youtube_needing_digest(self, limit: int = 50) -> List[YouTubeVideo]:
        stmt = (
            select(YouTubeVideo)
            .outerjoin(Digest, Digest.youtube_video_id == YouTubeVideo.id)
            .where(Digest.id.is_(None))
            .where(YouTubeVideo.transcript_status == "ok")
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def create_digest(self, **kwargs) -> Digest:
        digest = Digest(**kwargs)
        self.session.add(digest)
        self.session.flush()
        return digest

    # -- Curation / email ----------------------------------------------------

    def unsent_digests(self, hours: int = 24) -> List[Digest]:
        cutoff = _utcnow() - timedelta(hours=hours)
        stmt = (
            select(Digest)
            .where(Digest.sent_at.is_(None))
            .where(
                (Digest.published_at.is_(None)) | (Digest.published_at >= cutoff)
            )
            .order_by(Digest.score.desc().nullslast(), Digest.published_at.desc().nullslast())
        )
        return list(self.session.scalars(stmt))

    def mark_digests_sent(self, digest_ids: Iterable[int]) -> None:
        ids = list(digest_ids)
        if not ids:
            return
        now = _utcnow()
        for d in self.session.scalars(select(Digest).where(Digest.id.in_(ids))):
            d.sent_at = now
        self.session.flush()

    def update_digest_score(self, digest_id: int, score: int) -> None:
        d = self.session.get(Digest, digest_id)
        if d is not None:
            d.score = score
            self.session.flush()
