"""Database setup shared by the Streamlit app and future workers."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from config import settings


class Base(DeclarativeBase):
    pass


def _database_url(value: str) -> str:
    # Neon supplies postgres:// or postgresql:// URLs; use psycopg 3 explicitly.
    if value.startswith("postgres://"):
        value = "postgresql://" + value[len("postgres://"):]
    if value.startswith("postgresql://"):
        value = value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


engine = create_engine(_database_url(settings.database_url), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    # Import models before create_all so their tables are registered on Base.
    import models  # noqa: F401
    Base.metadata.create_all(engine)
