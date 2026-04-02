import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Default to SQLite for local dev (no Postgres needed).
# Docker / production sets DATABASE_URL to the Postgres connection string.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./agripermit.db",
)

# SQLite requires check_same_thread=False; PostgreSQL does not accept that arg
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
