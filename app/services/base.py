"""Base class for processing services.

A `ProcessService` opens a database session, processes pending records, and
returns a count of items processed. Subclasses override `_run`.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from ..database import Repository, get_session


log = logging.getLogger(__name__)


class ProcessService(ABC):
    name: str = "process"

    def run(self) -> int:
        log.info("Starting %s...", self.name)
        with get_session() as session:
            repo = Repository(session)
            n = self._run(repo)
        log.info("Finished %s: processed %d items", self.name, n)
        return n

    @abstractmethod
    def _run(self, repo: Repository) -> int: ...
