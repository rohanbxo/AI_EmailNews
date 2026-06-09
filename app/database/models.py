from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from .connection import Base


class _TimestampMixin:
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AnthropicArticle(Base, _TimestampMixin):
    __tablename__ = "anthropic_articles"

    id = Column(Integer, primary_key=True)
    url = Column(String(1024), nullable=False, unique=True)
    title = Column(String(512), nullable=False)
    author = Column(String(256))
    published_at = Column(DateTime(timezone=True))
    summary = Column(Text)
    raw_html = Column(Text)
    markdown = Column(Text)

    digest = relationship("Digest", back_populates="anthropic_article", uselist=False)

    __table_args__ = (Index("ix_anthropic_published_at", "published_at"),)


class OpenAIArticle(Base, _TimestampMixin):
    __tablename__ = "openai_articles"

    id = Column(Integer, primary_key=True)
    url = Column(String(1024), nullable=False, unique=True)
    title = Column(String(512), nullable=False)
    author = Column(String(256))
    published_at = Column(DateTime(timezone=True))
    summary = Column(Text)
    raw_html = Column(Text)
    markdown = Column(Text)

    digest = relationship("Digest", back_populates="openai_article", uselist=False)

    __table_args__ = (Index("ix_openai_published_at", "published_at"),)


class YouTubeVideo(Base, _TimestampMixin):
    __tablename__ = "youtube_videos"

    id = Column(Integer, primary_key=True)
    video_id = Column(String(64), nullable=False, unique=True)
    channel_id = Column(String(64), nullable=False)
    channel_title = Column(String(256))
    url = Column(String(1024), nullable=False)
    title = Column(String(512), nullable=False)
    description = Column(Text)
    published_at = Column(DateTime(timezone=True))
    transcript = Column(Text)
    transcript_status = Column(String(32), default="pending", nullable=False)

    digest = relationship("Digest", back_populates="youtube_video", uselist=False)

    __table_args__ = (
        Index("ix_youtube_published_at", "published_at"),
        Index("ix_youtube_channel", "channel_id"),
    )


class BlogArticle(Base, _TimestampMixin):
    """Generic blog article from any RSS source.

    Rather than create a new table for every new source, additional RSS
    feeds (HuggingFace, ImportAI, Latent Space, ...) share this table and
    are distinguished by `source`. The original Anthropic / OpenAI tables
    were kept for backwards compatibility with existing data.
    """

    __tablename__ = "blog_articles"

    id = Column(Integer, primary_key=True)
    source = Column(String(64), nullable=False)  # e.g. "huggingface", "importai"
    url = Column(String(1024), nullable=False, unique=True)
    title = Column(String(512), nullable=False)
    author = Column(String(256))
    published_at = Column(DateTime(timezone=True))
    summary = Column(Text)
    raw_html = Column(Text)
    markdown = Column(Text)

    digest = relationship("Digest", back_populates="blog_article", uselist=False)

    __table_args__ = (
        Index("ix_blog_published_at", "published_at"),
        Index("ix_blog_source", "source"),
    )


class Digest(Base, _TimestampMixin):
    """Unified summary record produced for any source content."""

    __tablename__ = "digests"

    id = Column(Integer, primary_key=True)
    source_type = Column(String(32), nullable=False)  # anthropic | openai | youtube
    title = Column(String(512), nullable=False)
    url = Column(String(1024), nullable=False)
    summary = Column(Text, nullable=False)
    score = Column(Integer)  # curator score 0-100
    sent_at = Column(DateTime(timezone=True))
    published_at = Column(DateTime(timezone=True))

    anthropic_article_id = Column(Integer, ForeignKey("anthropic_articles.id"))
    openai_article_id = Column(Integer, ForeignKey("openai_articles.id"))
    youtube_video_id = Column(Integer, ForeignKey("youtube_videos.id"))
    blog_article_id = Column(Integer, ForeignKey("blog_articles.id"))

    anthropic_article = relationship("AnthropicArticle", back_populates="digest")
    openai_article = relationship("OpenAIArticle", back_populates="digest")
    youtube_video = relationship("YouTubeVideo", back_populates="digest")
    blog_article = relationship("BlogArticle", back_populates="digest")

    __table_args__ = (
        UniqueConstraint(
            "source_type",
            "anthropic_article_id",
            "openai_article_id",
            "youtube_video_id",
            "blog_article_id",
            name="uq_digest_source",
        ),
        Index("ix_digest_sent_at", "sent_at"),
        Index("ix_digest_published_at", "published_at"),
    )
