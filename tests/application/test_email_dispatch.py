from app.application.email_dispatch import dispatch_email
from app.domain.entities import EmailRequest


def test_dispatch_email_uses_adapter_interface():
    request = EmailRequest(
        sender={"email": "sender@example.com"},
        recipients=["recipient@example.com"],
        subject="A subject",
        message="A message",
    )
    dispatched = []

    class InMemoryEmailDispatcher:
        def dispatch(self, email_request, request_id=None):
            dispatched.append((email_request, request_id))

    dispatch_email(request, InMemoryEmailDispatcher(), request_id="trace-123")

    assert dispatched == [(request, "trace-123")]
