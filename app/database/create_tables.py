from . import models  # noqa: F401  (register models)
from .connection import Base, engine, ENVIRONMENT


def main() -> None:
    print(f"Creating tables in {ENVIRONMENT} environment...")
    Base.metadata.create_all(engine)
    print("Done. Tables:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")


if __name__ == "__main__":
    main()
