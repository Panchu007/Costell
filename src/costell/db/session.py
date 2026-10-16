"""Database engine and session management for Costell."""

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from costell.config import settings

# Store the SQLite file at data/costell.db
_DB_PATH = settings.processed_data_dir.parent / "costell.db"
_DB_URL = f"sqlite:///{_DB_PATH}"

# check_same_thread=False is required for SQLite + FastAPI
engine = create_engine(_DB_URL, echo=False, connect_args={"check_same_thread": False})


def init_db() -> None:
    """Create all tables if they don't exist yet."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a database session."""
    with Session(engine) as session:
        yield session
