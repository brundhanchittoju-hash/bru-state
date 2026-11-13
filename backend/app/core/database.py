from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Engine configuration supporting both SQLite and PostgreSQL
raw_db_url = settings.DATABASE_URL
if raw_db_url:
    clean_url = raw_db_url.strip().strip("'\"")
    for prefix in ("DATABASE_URL=", "DIRECT_URL="):
        if clean_url.startswith(prefix):
            clean_url = clean_url.split(prefix, 1)[1].strip().strip("'\"")
    raw_db_url = clean_url

connect_args = {}
if raw_db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    raw_db_url,
    connect_args=connect_args,
    echo=False,
    future=True,
)

# Enable foreign keys for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    """Dependency that yields a database session and safely closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
