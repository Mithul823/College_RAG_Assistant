from collections.abc import Generator
import os
from pathlib import Path
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models
from app.db.base import Base
from app.db.session import get_db
from app.main import app

temp_db_path = Path(tempfile.gettempdir()) / "test_college_rag.db"
test_engine = create_engine(
    f"sqlite:///{temp_db_path}",
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


from app.rag.vectorstore.chroma import get_vector_store


@pytest.fixture(autouse=True)
def setup_test_db() -> Generator[None, None, None]:
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    try:
        get_vector_store().reset()
    except Exception:
        pass
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(test_engine)
    try:
        get_vector_store().reset()
    except Exception:
        pass
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client

