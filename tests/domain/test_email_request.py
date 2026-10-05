import pytest
from pydantic import ValidationError

from app.domain.entities import EmailRequest


def test_task_payload_maps_to_cc_and_bcc_roles_and_attachments():
    request = EmailRequest.from_task_payload(
        {
            "sender": {"email": "sender@example.com"},
            "recipients": ["to@example.com"],
            "cc": [{"email": "cc@example.com", "name": "Carbon Copy"}],
            "bcc": [{"email": "bcc@example.com"}],
            "subject": "A subject",
            "message": "A message",
            "attachments": [
                {
                    "filename": "report.pdf",
                    "content": "encoded contents",
                    "type": "application/pdf",
                }
            ],
        }
    )

    assert str(request.recipients[0].email) == "to@example.com"
    assert str(request.ccs[0].email) == "cc@example.com"
    assert str(request.bccs[0].email) == "bcc@example.com"
    assert request.ccs[0].name == "Carbon Copy"
    assert request.attachments[0].filename == "report.pdf"


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"recipients": []},
        {"ccs": []},
        {"bcc": []},
        {"attachments": []},
        {"subject": ""},
        {"message": ""},
        {"recipients": ["not-an-email"]},
        {"attachments": [{"filename": "report.pdf", "content": ""}]},
    ],
)
def test_task_payload_rejects_invalid_email_fields(invalid_payload):
    payload = {
        "sender": {"email": "sender@example.com"},
        "recipients": ["to@example.com"],
        "subject": "A subject",
        "message": "A message",
    }
    payload.update(invalid_payload)

    with pytest.raises(ValidationError):
        EmailRequest.from_task_payload(payload)


def test_task_payload_serialization_uses_legacy_message_field_names():
    request = EmailRequest.from_task_payload(
        {
            "sender": {"email": "sender@example.com"},
            "recipients": ["to@example.com"],
            "subject": "A subject",
            "message": "A message",
        }
    )

    assert request.to_task_payload() == {
        "sender": {"email": "sender@example.com", "name": None},
        "recipients": [{"email": "to@example.com", "name": None}],
        "ccs": None,
        "bccs": None,
        "subject": "A subject",
        "message": "A message",
        "attachments": None,
    }
