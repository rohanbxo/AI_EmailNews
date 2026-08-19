"""Tiny idempotent migration runner.

`Base.metadata.create_all` only creates missing tables — it never alters
existing ones. This module applies the small set of schema deltas we've
needed since v0. Safe to run repeatedly; each statement uses `IF NOT EXISTS`.
"""
from __future__ import annotations

from sqlalchemy import text

from .connection import ENVIRONMENT, engine


MIGRATIONS = [
    # 2026-06-10: link Digest -> BlogArticle for new generic blog sources.
    """
    ALTER TABLE digests
        ADD COLUMN IF NOT EXISTS blog_article_id INTEGER
        REFERENCES blog_articles(id)
    """,
    # 2026-08-19: semantic-dedup fields.
    """
    ALTER TABLE digests
        ADD COLUMN IF NOT EXISTS embedding BYTEA
    """,
    """
    ALTER TABLE digests
        ADD COLUMN IF NOT EXISTS dup_of_id INTEGER
        REFERENCES digests(id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_digest_dup_of ON digests(dup_of_id)
    """,
]


def main() -> None:
    print(f"Running migrations against {ENVIRONMENT}...")
    with engine.begin() as conn:
        for stmt in MIGRATIONS:
            conn.execute(text(stmt))
    print(f"Applied {len(MIGRATIONS)} migration statement(s).")


if __name__ == "__main__":
    main()
