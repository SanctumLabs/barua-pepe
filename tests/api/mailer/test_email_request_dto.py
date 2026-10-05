import asyncio
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import Response

from app.api.mailer.dto import EmailRequestDto
from app.api.mailer.routes import send_plain_email
from app.domain.entities import EmailRequest


@pytest.mark.parametrize("sender_field", ["from", "from_"])
def test_http_email_dto_converts_to_canonical_contract(sender_field):
    dto = EmailRequestDto.parse_obj(
        {
            sender_field: {"email": "sender@example.com"},
            "to": ["to@example.com"],
            "cc": [{"email": "cc@example.com", "name": "Carbon Copy"}],
            "bcc": ["bcc@example.com"],
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

    request = dto.to_email_request()

    assert isinstance(request, EmailRequest)
    assert str(request.recipients[0].email) == "to@example.com"
    assert str(request.ccs[0].email) == "cc@example.com"
    assert str(request.bccs[0].email) == "bcc@example.com"
    assert request.attachments[0].filename == "report.pdf"


@pytest.mark.parametrize(
    "overrides",
    [
        {"to": []},
        {"cc": []},
        {"bcc": []},
        {"attachments": []},
        {"subject": ""},
        {"message": ""},
    ],
)
def test_http_email_dto_validates_using_canonical_contract(overrides):
    payload = {
        "from": {"email": "sender@example.com"},
        "to": ["to@example.com"],
        "subject": "A subject",
        "message": "A message",
    }
    payload.update(overrides)

    with pytest.raises(ValidationError):
        EmailRequestDto.parse_obj(payload)


def test_sendmail_route_converts_http_payload_to_canonical_contract():
    payload = EmailRequestDto.parse_obj(
        {
            "from": {"email": "sender@example.com"},
            "to": ["to@example.com"],
            "cc": ["cc@example.com"],
            "bcc": ["bcc@example.com"],
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
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/baruapepe/sendmail/",
            "headers": [],
            "query_string": b"",
            "state": {"request_id": "trace-123"},
        }
    )

    with patch("app.api.mailer.routes.dispatch_email") as dispatch_email:
        response = asyncio.run(send_plain_email(payload, request, Response()))

    dispatch_args = dispatch_email.call_args.args
    enqueued_request = dispatch_args[0]
    assert response.status == 202
    assert isinstance(enqueued_request, EmailRequest)
    assert str(enqueued_request.recipients[0].email) == "to@example.com"
    assert str(enqueued_request.ccs[0].email) == "cc@example.com"
    assert str(enqueued_request.bccs[0].email) == "bcc@example.com"
    assert dispatch_args[2] == "trace-123"
