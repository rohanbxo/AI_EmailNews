"""Daily pipeline orchestrator."""
from __future__ import annotations

import logging

from .database import Base, engine
from .database.migrate import main as _run_migrations
from .runner import run_all_scrapers
from .services.process_anthropic import ProcessAnthropic
from .services.process_curator import ProcessCurator
from .services.process_digest import ProcessDigest
from .services.process_email import run as run_email
from .services.process_youtube import ProcessYouTube


log = logging.getLogger(__name__)


def _ensure_schema() -> None:
    # Register models on import side-effect via app.database.__init__
    Base.metadata.create_all(engine)
    _run_migrations()


def run_daily_pipeline() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log.info("=== Daily pipeline start ===")

    _ensure_schema()

    log.info("Step 1/5: scraping")
    run_all_scrapers()

    log.info("Step 2/5: markdown conversion")
    ProcessAnthropic().run()

    log.info("Step 3/5: youtube transcripts")
    ProcessYouTube().run()

    log.info("Step 4/5: digests + curator scoring")
    ProcessDigest().run()
    ProcessCurator().run()

    log.info("Step 5/5: email")
    sent = run_email()
    log.info("Email step sent %d items.", sent)

    log.info("=== Daily pipeline done ===")


if __name__ == "__main__":
    run_daily_pipeline()
