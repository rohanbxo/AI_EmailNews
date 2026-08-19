import os
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
else:
    load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Copy app/example.env to .env and configure it."
    )


def _detect_environment() -> str:
    explicit = os.getenv("ENVIRONMENT")
    if explicit:
        return explicit.upper()
    if "render.com" in (DATABASE_URL or ""):
        return "PRODUCTION"
    return "LOCAL"


ENVIRONMENT = _detect_environment()


_connect_args = {}
if ENVIRONMENT == "PRODUCTION":
    _connect_args["sslmode"] = "require"


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,     # verify liveness on checkout (dead connections auto-refreshed)
    pool_recycle=280,        # Neon idle-idles at 300s; recycle before then
    pool_size=5,
    max_overflow=5,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
