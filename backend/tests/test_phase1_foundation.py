from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.base import Base
from app.db.session import engine
from app.main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "development"}


def test_settings_parse_cors_origins() -> None:
    settings = Settings(cors_origins="http://localhost:5173, http://localhost:3000")

    assert settings.cors_origins == ["http://localhost:5173", "http://localhost:3000"]


def test_settings_use_psycopg_for_generic_postgresql_url() -> None:
    settings = Settings(database_url="postgresql://user:password@localhost:5432/college_rag")

    assert settings.database_url.startswith("postgresql+psycopg://")


def test_settings_encode_reserved_database_password_characters() -> None:
    settings = Settings(
        database_url="postgresql://user:[password@123]@localhost:5432/college_rag"
    )

    assert settings.database_url == (
        "postgresql+psycopg://user:%5Bpassword%40123%5D@localhost:5432/college_rag"
    )


def test_database_foundation_uses_configured_engine() -> None:
    assert str(engine.url).startswith("postgresql+psycopg://")
    assert "users" in Base.metadata.tables
