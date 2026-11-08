"""One shared in-memory database + one get_db override for the whole test run."""
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["LOAD_MODELS_ON_STARTUP"] = "false"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import db as dbmod

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
dbmod.engine = engine
dbmod.SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

import app.main as mainmod  # noqa: E402
from app.db import Base, get_db  # noqa: E402

mainmod.engine = engine
Base.metadata.create_all(engine)


def _db():
    s = dbmod.SessionLocal()
    try:
        yield s
    finally:
        s.close()


mainmod.app.dependency_overrides[get_db] = _db


@pytest.fixture(autouse=True)
def clean_db():
    from app.services import security
    security.clear_failures()
    security.lookup_limiter.clear()
    yield
    with dbmod.SessionLocal() as s:
        for t in reversed(Base.metadata.sorted_tables):
            s.execute(t.delete())
        s.commit()
