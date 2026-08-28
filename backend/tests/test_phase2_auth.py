import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.base import Base
from app.main import app
from app.models.user import User, UserRole
from tests.conftest import TestingSessionLocal


def test_register_hashes_password_and_defaults_to_student() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={"name": "Student Name", "email": "STUDENT@example.com", "password": "secret123"},
        )

    assert response.status_code == 201
    assert response.json()["role"] == "student"
    assert "password" not in response.json()

    with TestingSessionLocal() as database:
        user = database.query(Base.metadata.tables["users"]).one()
        assert user.password_hash != "secret123"


def test_duplicate_registration_and_invalid_login_are_rejected() -> None:
    with TestClient(app) as client:
        payload = {"name": "Student", "email": "student@example.com", "password": "secret123"}
        assert client.post("/api/v1/auth/register", json=payload).status_code == 201
        assert client.post("/api/v1/auth/register", json=payload).status_code == 409
        response = client.post(
            "/api/v1/auth/login",
            json={"email": payload["email"], "password": "wrong-password"},
        )

    assert response.status_code == 401


def test_login_returns_token_and_me_requires_bearer_token() -> None:
    with TestClient(app) as client:
        payload = {"name": "Student", "email": "student@example.com", "password": "secret123"}
        client.post("/api/v1/auth/register", json=payload)
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )
        token = login_response.json()["access_token"]
        me_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        unauthorized_response = client.get("/api/v1/auth/me")

    assert login_response.status_code == 200
    assert me_response.status_code == 200
    assert me_response.json()["email"] == payload["email"]
    assert unauthorized_response.status_code == 401


def test_admin_role_dependency_rejects_students() -> None:
    admin_dependency = require_role(UserRole.ADMIN)
    admin = User(name="Admin", email="admin@example.com", password_hash="hash", role=UserRole.ADMIN)
    student = User(
        name="Student", email="student@example.com", password_hash="hash", role=UserRole.STUDENT
    )

    assert admin_dependency(admin) is admin
    with pytest.raises(HTTPException) as error:
        admin_dependency(student)
    assert error.value.status_code == 403