from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app
from app.exceptions import AppException
from app.services.auth.auth_service import get_current_auth


def test_sendmail_returns_accepted_after_dispatch(monkeypatch):
    monkeypatch.setitem(app.dependency_overrides, get_current_auth, lambda: None)

    with patch("app.api.mailer.routes.dispatch_email") as dispatch_email:
        response = TestClient(app).post(
            "/api/v1/baruapepe/sendmail/",
            json={
                "from": {"email": "sender@example.com"},
                "to": ["recipient@example.com"],
                "subject": "A subject",
                "message": "A message",
            },
        )

    assert response.status_code == 202
    assert response.json()["message"] == "Email request accepted for processing"
    dispatch_email.assert_called_once()


def test_sendmail_reports_enqueue_failure_as_server_error(monkeypatch):
    monkeypatch.setitem(app.dependency_overrides, get_current_auth, lambda: None)

    with patch(
        "app.api.mailer.routes.dispatch_email",
        side_effect=AppException("enqueue failed"),
    ):
        response = TestClient(app).post(
            "/api/v1/baruapepe/sendmail/",
            json={
                "from": {"email": "sender@example.com"},
                "to": ["recipient@example.com"],
                "subject": "A subject",
                "message": "A message",
            },
        )

    assert response.status_code == 500
    assert response.json()["message"] == "Failed to send email"
