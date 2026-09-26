import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
import app.models  # noqa: F401
from app.db.session import get_db
from app.main import app

TEST_DB = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://chinna@/mockfastapi_test?host=/tmp",
)

engine = create_engine(TEST_DB, pool_pre_ping=True)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _ensure_db():
    admin = create_engine("postgresql+psycopg://chinna@/postgres?host=/tmp")
    with admin.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname='mockfastapi_test'")
        ).first()
        if not exists:
            conn.execute(text("CREATE DATABASE mockfastapi_test"))


_ensure_db()


@pytest.fixture()
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    s = TestingSession()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def client(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
