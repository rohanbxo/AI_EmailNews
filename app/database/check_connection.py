from sqlalchemy import text

from .connection import ENVIRONMENT, engine


def main() -> None:
    print(f"Environment: {ENVIRONMENT}")
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar()
        print(f"Connected. Server: {version}")


if __name__ == "__main__":
    main()
