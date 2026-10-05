from unittest.mock import patch

from app.domain.entities import EmailRequest
from app.services.mail.mailer import send_plain_mail


@patch("app.services.mail.mailer.SmtpServer")
@patch("app.services.mail.mailer.get_config")
def test_mailer_converts_contract_to_legacy_delivery_arguments(
    get_config_patch, smtp_server_patch
):
    get_config_patch.return_value.mail_smtp_enabled = True
    request = EmailRequest(
        sender={"email": "sender@example.com"},
        recipients=["to@example.com"],
        ccs=None,
        bccs=None,
        subject="A subject",
        message="A message",
        attachments=[
            {
                "filename": "report.pdf",
                "content": "encoded contents",
                "type": "application/pdf",
            }
        ],
    )

    send_plain_mail(request)

    smtp_server_patch.return_value.sendmail.assert_called_once_with(
        sender={"email": "sender@example.com", "name": None},
        recipients=[{"email": "to@example.com", "name": None}],
        ccs=[],
        bcc=[],
        subject="A subject",
        message="A message",
        attachments=[
            {
                "filename": "report.pdf",
                "content": "encoded contents",
                "type": "application/pdf",
            }
        ],
    )
