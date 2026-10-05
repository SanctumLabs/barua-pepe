import smtplib
from email import message_from_string
from unittest.mock import Mock, patch

import pytest

from app.domain.entities import EmailRequest
from app.services.mail.exceptions import (
    DeliveryOutcomeUnknownException,
    DeliveryRejectedException,
)
from app.services.mail.sendgrid_email_service import SendGridEmailService
from app.services.mail.smtp_proxy import SmtpServer


@patch("app.services.mail.smtp_proxy.smtplib.SMTP")
def test_smtp_sends_cc_and_bcc_in_envelope_without_exposing_bcc(_smtp_factory):
    provider = SmtpServer()
    original_server = provider.server
    smtp_server = Mock()
    provider.server = smtp_server
    request = EmailRequest(
        sender={"email": "sender@example.com"},
        recipients=["to@example.com"],
        ccs=[{"email": "cc@example.com"}],
        bccs=[{"email": "bcc@example.com"}],
        subject="A subject",
        message="A message",
    )

    with patch.object(provider, "_SmtpServer__check_connection", return_value=True):
        try:
            provider.send_email(request)
        finally:
            provider.server = original_server

    sendmail_kwargs = smtp_server.sendmail.call_args.kwargs
    assert sendmail_kwargs["to_addrs"] == [
        "to@example.com",
        "cc@example.com",
        "bcc@example.com",
    ]
    message = message_from_string(sendmail_kwargs["msg"])
    assert message["To"] == "to@example.com"
    assert message["Cc"] == "cc@example.com"
    assert "Bcc" not in message


def make_request():
    return EmailRequest(
        sender={"email": "sender@example.com"},
        recipients=["recipient@example.com"],
        subject="A subject",
        message="A message",
    )


@pytest.mark.parametrize(
    ("status_code", "expected_exception"),
    [
        (202, None),
        (400, DeliveryRejectedException),
        (503, DeliveryOutcomeUnknownException),
    ],
)
def test_sendgrid_response_classifies_acceptance(status_code, expected_exception):
    provider = SendGridEmailService()
    original_client = provider.mail_client
    provider.mail_client = Mock()
    provider.mail_client.client.mail.send.post.return_value.status_code = status_code

    try:
        if expected_exception is None:
            assert provider.send_email(make_request())["success"] is True
        else:
            with pytest.raises(expected_exception):
                provider.send_email(make_request())
    finally:
        provider.mail_client = original_client


@patch("app.services.mail.smtp_proxy.smtplib.SMTP")
def test_smtp_classifies_explicit_server_rejection(_smtp_factory):
    provider = SmtpServer()
    original_server = provider.server
    provider.server = Mock()
    provider.server.sendmail.side_effect = smtplib.SMTPRecipientsRefused({})
    with patch.object(provider, "_SmtpServer__check_connection", return_value=True):
        try:
            with pytest.raises(DeliveryRejectedException):
                provider.send_email(make_request())
        finally:
            provider.server = original_server


@patch("app.services.mail.smtp_proxy.smtplib.SMTP")
def test_smtp_classifies_connection_loss_as_unknown(_smtp_factory):
    provider = SmtpServer()
    original_server = provider.server
    provider.server = Mock()
    provider.server.sendmail.side_effect = OSError("connection lost")
    with patch.object(provider, "_SmtpServer__check_connection", return_value=True):
        try:
            with pytest.raises(DeliveryOutcomeUnknownException):
                provider.send_email(make_request())
        finally:
            provider.server = original_server
