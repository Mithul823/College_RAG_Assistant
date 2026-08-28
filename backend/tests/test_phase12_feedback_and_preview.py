import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.conversation import Conversation
from app.models.feedback import MessageFeedback
from app.models.message import Message, MessageRole
from app.models.user import User, UserRole
from tests.conftest import TestingSessionLocal


@pytest.fixture
def test_setup():
    db = TestingSessionLocal()

    student = User(
        name="Student User",
        email=f"student_{uuid4()}@college.edu",
        password_hash=hash_password("pass123"),
        role=UserRole.STUDENT,
    )
    admin = User(
        name="Admin User",
        email=f"admin_{uuid4()}@college.edu",
        password_hash=hash_password("adminpass"),
        role=UserRole.ADMIN,
    )
    db.add_all([student, admin])
    db.commit()
    db.refresh(student)
    db.refresh(admin)

    conv = Conversation(
        id=uuid4(),
        user_id=student.id,
        title="Test Conversation",
    )
    db.add(conv)
    db.commit()

    msg = Message(
        id=uuid4(),
        conversation_id=conv.id,
        role=MessageRole.ASSISTANT,
        content="Test answer regarding attendance requirements.",
        answer_mode="grounded",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    student_token = create_access_token(student.id, student.role)
    admin_token = create_access_token(admin.id, admin.role)

    yield {
        "student": student,
        "admin": admin,
        "student_token": student_token,
        "admin_token": admin_token,
        "message": msg,
    }
    db.close()


def test_submit_feedback_student_success(test_setup) -> None:
    student_token = test_setup["student_token"]
    msg_id = test_setup["message"].id

    with TestClient(app) as client:
        # Submit positive rating
        res = client.post(
            f"/api/v1/chat/messages/{msg_id}/feedback",
            headers={"Authorization": f"Bearer {student_token}"},
            json={"rating": 1, "comment": "Very clear and helpful!"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["rating"] == 1
        assert data["comment"] == "Very clear and helpful!"
        assert data["message_id"] == str(msg_id)

        # Update to negative rating
        res_update = client.post(
            f"/api/v1/chat/messages/{msg_id}/feedback",
            headers={"Authorization": f"Bearer {student_token}"},
            json={"rating": -1, "comment": "Needs more detail."},
        )
        assert res_update.status_code == 200
        assert res_update.json()["rating"] == -1

        # Fetch feedback
        res_get = client.get(
            f"/api/v1/chat/messages/{msg_id}/feedback",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert res_get.status_code == 200
        assert res_get.json()["rating"] == -1


def test_feedback_requires_auth(test_setup) -> None:
    msg_id = test_setup["message"].id
    with TestClient(app) as client:
        res = client.post(
            f"/api/v1/chat/messages/{msg_id}/feedback",
            json={"rating": 1},
        )
        assert res.status_code == 401


def test_feedback_nonexistent_message(test_setup) -> None:
    student_token = test_setup["student_token"]
    fake_id = uuid4()
    with TestClient(app) as client:
        res = client.post(
            f"/api/v1/chat/messages/{fake_id}/feedback",
            headers={"Authorization": f"Bearer {student_token}"},
            json={"rating": 1},
        )
        assert res.status_code == 404


def test_admin_feedback_analytics(test_setup) -> None:
    admin_token = test_setup["admin_token"]
    student_token = test_setup["student_token"]
    msg_id = test_setup["message"].id

    with TestClient(app) as client:
        # Submit feedback as student
        client.post(
            f"/api/v1/chat/messages/{msg_id}/feedback",
            headers={"Authorization": f"Bearer {student_token}"},
            json={"rating": 1},
        )

        # Student should be rejected from admin analytics
        res_forbidden = client.get(
            "/api/v1/admin/analytics/feedback",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert res_forbidden.status_code == 403

        # Admin can view analytics
        res_admin = client.get(
            "/api/v1/admin/analytics/feedback",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_admin.status_code == 200
        analytics = res_admin.json()
        assert analytics["total_feedback"] >= 1
        assert analytics["positive_count"] >= 1
        assert analytics["satisfaction_rate"] > 0.0

