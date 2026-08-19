"""Semantic cross-source deduplication.

Runs after `ProcessDigest` and before `ProcessCurator`. Steps:

  1. Embed any digest whose `embedding` column is NULL (batch).
  2. For each newly-created digest (no `dup_of_id`, no `sent_at`), compare
     its embedding against every non-duplicate digest from the last N days.
  3. If cosine similarity >= DEDUP_THRESHOLD, mark the new digest as a
     duplicate of the earliest matching canonical one.

Downstream `ProcessCurator` / `process_email` filter out `dup_of_id IS NOT
NULL`, so duplicates never get ranked or emailed. The website surfaces them
as "also covered by: X, Y" on the canonical item.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

import numpy as np
from sqlalchemy import select

from ..agent import embedding_agent
from ..database import Digest, get_session
from .base import ProcessService


log = logging.getLogger(__name__)


# Tunable via env. Empirically on MiniLM + AI news summaries:
#   - same story, different outlets: 0.75-0.85
#   - distinct AI stories: -0.05 to 0.20
#   - cross-topic AI content: 0.05-0.35
# 0.75 sits well below "same story" and well above the noise ceiling.
DEDUP_THRESHOLD = float(os.getenv("DEDUP_THRESHOLD", "0.75"))

# How far back to search for possible canonicals.
DEDUP_LOOKBACK_DAYS = int(os.getenv("DEDUP_LOOKBACK_DAYS", "7"))


class ProcessDedup(ProcessService):
    """Runs in three short DB transactions so the connection never sits idle
    while sentence-transformers is loading or embedding."""

    name = "process_dedup"

    # Override the base run() to avoid holding one long-lived session across
    # the (slow) embedding step. Each phase opens a fresh session.
    def run(self) -> int:
        log.info("Starting %s...", self.name)

        # -- Phase 1: fetch ids + text for digests missing embeddings -------
        with get_session() as s:
            missing = list(
                s.scalars(select(Digest).where(Digest.embedding.is_(None)))
            )
            missing_payload: List[Tuple[int, str]] = [
                (d.id, f"{d.title}\n\n{d.summary}") for d in missing
            ]

        # -- Phase 2: embed OUTSIDE any DB session (may take seconds) -------
        if missing_payload:
            texts = [t for _, t in missing_payload]
            vecs = embedding_agent.embed(texts)
            with get_session() as s:
                for (did, _), v in zip(missing_payload, vecs):
                    d = s.get(Digest, did)
                    if d is not None:
                        d.embedding = embedding_agent.pack(v)
            log.info("Embedded %d new digests", len(missing_payload))

        # -- Phase 3: cluster + mark duplicates -----------------------------
        marked = self._cluster_and_mark()

        log.info("Finished %s: marked %d duplicates", self.name, marked)
        return marked

    def _run(self, repo) -> int:  # pragma: no cover  (base API compat)
        return self.run()

    def _cluster_and_mark(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=DEDUP_LOOKBACK_DAYS)
        with get_session() as s:
            recent = list(
                s.scalars(
                    select(Digest)
                    .where(Digest.embedding.is_not(None))
                    .where(Digest.created_at >= cutoff)
                    .order_by(Digest.created_at.asc())  # earliest wins canonicality
                )
            )
            if len(recent) < 2:
                return 0

            vec_by_id: Dict[int, np.ndarray] = {
                d.id: embedding_agent.unpack(d.embedding) for d in recent
            }

            canonicals: List[Digest] = []
            marked = 0

            for d in recent:
                v = vec_by_id[d.id]
                best_id = None
                best_sim = 0.0
                for cd in canonicals:
                    sim = embedding_agent.cosine(v, vec_by_id[cd.id])
                    if sim > best_sim:
                        best_sim = sim
                        best_id = cd.id
                if best_id is not None and best_sim >= DEDUP_THRESHOLD:
                    if d.dup_of_id != best_id:
                        d.dup_of_id = best_id
                        marked += 1
                        log.info(
                            "Digest %d -> dup of %d (cosine=%.3f) — %r",
                            d.id,
                            best_id,
                            best_sim,
                            d.title[:60],
                        )
                else:
                    # Ensure previously-set dup_of_id is cleared if this item
                    # now looks canonical (e.g. after a threshold change).
                    if d.dup_of_id is not None:
                        d.dup_of_id = None
                    canonicals.append(d)

            log.info(
                "Dedup: %d canonicals, %d newly-marked duplicates (threshold=%.2f)",
                len(canonicals),
                marked,
                DEDUP_THRESHOLD,
            )
            return marked


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ProcessDedup().run()


if __name__ == "__main__":
    main()
