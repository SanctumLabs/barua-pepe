from unittest.mock import patch

import pytest

from app.domain.entities import EmailRequest
from app.services.mail.delivery_policy import deliver_email
from app.services.mail.exceptions import (
    DeliveryOutcomeUnknownException,
    DeliveryRejectedException,
    EmailSendingException,
)
from app.services.mail.mailer import send_plain_mail


@patch("app.services.mail.mailer.SmtpServer")
@patch("app.services.mail.mailer.SendGridEmailService")
@patch("app.services.mail.mailer.get_config")
@patch("app.services.mail.mailer.deliver_email")
def test_mailer_selects_smtp_primary_and_sendgrid_fallback(
    deliver_email_patch, get_config_patch, sendgrid_patch, smtp_server_patch
):
    get_config_patch.return_value.mail_smtp_enabled = True
    request = EmailRequest(
        sender={"email": "sender@example.com"},
        recipients=["to@example.com"],
        subject="A subject",
        message="A message",
    )

    send_plain_mail(request)

    deliver_email_patch.assert_called_once_with(
        request,
        primary=smtp_server_patch,
        fallback=sendgrid_patch,
    )


@patch("app.services.mail.mailer.SmtpServer")
@patch("app.services.mail.mailer.SendGridEmailService")
@patch("app.services.mail.mailer.get_config")
@patch("app.services.mail.mailer.deliver_email")
def test_mailer_uses_sendgrid_without_fallback_when_smtp_is_disabled(
    deliver_email_patch, get_config_patch, sendgrid_patch, smtp_server_patch
):
    get_config_patch.return_value.mail_smtp_enabled = False
    request = EmailRequest(
        sender={"email": "sender@example.com"},
        recipients=["to@example.com"],
        subject="A subject",
        message="A message",
    )

    send_plain_mail(request)

    deliver_email_patch.assert_called_once_with(
        request, primary=sendgrid_patch, fallback=None
    )
    smtp_server_patch.assert_not_called()


@patch(
    "app.services.mail.mailer.deliver_email",
    side_effect=DeliveryOutcomeUnknownException("connection lost"),
)
@patch("app.services.mail.mailer.get_config")
def test_mailer_propagates_unknown_provider_outcomes(get_config_patch, deliver_patch):
    get_config_patch.return_value.mail_smtp_enabled = False
    request = EmailRequest(
        sender={"email": "sender@example.com"},
        recipients=["to@example.com"],
        subject="A subject",
        message="A message",
    )

    with pytest.raises(DeliveryOutcomeUnknownException):
        send_plain_mail(request)


class StubProvider:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.requests = []

    def send_email(self, request):
        self.requests.append(request)
        if self.error:
            raise self.error
        return self.result


def make_request():
    return EmailRequest(
        sender={"email": "sender@example.com"},
        recipients=["to@example.com"],
        subject="A subject",
        message="A message",
    )


def test_delivery_policy_returns_primary_success_without_using_fallback():
    result = {"success": True}
    primary = StubProvider(result=result)
    fallback = StubProvider(result={"success": True})

    assert deliver_email(make_request(), lambda: primary, lambda: fallback) is result
    assert len(primary.requests) == 1
    assert fallback.requests == []


def test_delivery_policy_uses_fallback_after_confirmed_rejection():
    request = make_request()
    fallback_result = {"success": True}
    primary = StubProvider(error=DeliveryRejectedException("rejected"))
    fallback = StubProvider(result=fallback_result)

    assert deliver_email(request, lambda: primary, lambda: fallback) is fallback_result
    assert primary.requests == [request]
    assert fallback.requests == [request]


def test_delivery_policy_raises_when_both_providers_reject():
    primary = StubProvider(error=DeliveryRejectedException("primary rejected"))
    fallback = StubProvider(error=DeliveryRejectedException("fallback rejected"))

    with pytest.raises(EmailSendingException) as raised:
        deliver_email(make_request(), lambda: primary, lambda: fallback)

    assert isinstance(raised.value.__cause__, DeliveryRejectedException)

    assert len(primary.requests) == 1
    assert len(fallback.requests) == 1


def test_delivery_policy_does_not_fallback_when_acceptance_is_unknown():
    primary = StubProvider(error=DeliveryOutcomeUnknownException("connection lost"))
    fallback = StubProvider(result={"success": True})

    with pytest.raises(DeliveryOutcomeUnknownException):
        deliver_email(make_request(), lambda: primary, lambda: fallback)

    assert len(primary.requests) == 1
    assert fallback.requests == []


def test_delivery_policy_falls_back_when_primary_cannot_be_initialized():
    fallback = StubProvider(result={"success": True})

    def primary_factory():
        raise RuntimeError("SMTP connection setup failed")

    assert deliver_email(make_request(), primary_factory, lambda: fallback) == {
        "success": True
    }
    assert fallback.requests
