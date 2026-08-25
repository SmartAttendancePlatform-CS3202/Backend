from __future__ import annotations

import os
from functools import lru_cache
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse

def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # Strip pgbouncer parameter
    parsed = urlparse(database_url)
    query = dict(parse_qsl(parsed.query))
    if "pgbouncer" in query:
        del query["pgbouncer"]
    parsed = parsed._replace(query=urlencode(query))
    return urlunparse(parsed)


@lru_cache(maxsize=1)
def get_database_url() -> str:
    for name in (
        "SUPABASE_DATABASE_URL",
        "DATABASE_URL",
        "POSTGRES_URL",
        "SQLALCHEMY_DATABASE_URL",
    ):
        value = os.getenv(name)
        if value:
            return _normalize_database_url(value)

    raise RuntimeError(
        "Missing database configuration. Set SUPABASE_DATABASE_URL or DATABASE_URL."
    )


@lru_cache(maxsize=1)
def get_engine():
    return create_engine(get_database_url(), pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_session_factory():
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()