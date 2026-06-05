"""Score unsent digests against the user profile."""
from __future__ import annotations

import logging

from ..agent import CuratorAgent
from ..config import DIGEST_LOOKBACK_HOURS
from ..database import Repository
from ..profiles import USER_PROFILE
from .base import ProcessService


log = logging.getLogger(__name__)


class ProcessCurator(ProcessService):
    name = "process_curator"

    def __init__(self):
        self.agent = CuratorAgent()

    def _run(self, repo: Repository) -> int:
        digests = [d for d in repo.unsent_digests(hours=DIGEST_LOOKBACK_HOURS) if d.score is None]
        if not digests:
            return 0
        items = [
            {
                "id": d.id,
                "source_type": d.source_type,
                "title": d.title,
                "summary": d.summary,
            }
            for d in digests
        ]
        scores = self.agent.rank(profile_prompt=USER_PROFILE.as_prompt(), items=items)
        for s in scores:
            repo.update_digest_score(s.id, s.score)
        return len(scores)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ProcessCurator().run()


if __name__ == "__main__":
    main()
