"""
Wrapper for Sendgrid Email Service Provider
"""

import sendgrid as mail_client
from sendgrid.helpers.mail import (
    Email,
    To,
    Bcc,
    Cc,
    Mail,
    Content,
    HtmlContent,
    Attachment,
    MimeType,
    FileContent,
    FileName,
    FileType,
)
from app.utils import singleton
from app.config import get_config
from app.logger import log
from app.domain.entities import EmailRequest
from .exceptions import (
    DeliveryOutcomeUnknownException,
    DeliveryRejectedException,
)
from .email_service import EmailDeliveryResult, EmailService


@singleton
# pylint: disable=too-few-public-methods
class SendGridEmailService(EmailService):
    """
    Email Service wrapper around Sendgrid email service provider
    """

    def __init__(
        self,
        url: str = get_config().mail_api_url,
        token: str = get_config().mail_api_token,
    ):
        super().__init__()
        self.url = url
        self.token = token
        self.mail_client = mail_client.SendGridAPIClient(api_key=token)

    def send_email(self, request: EmailRequest) -> EmailDeliveryResult:
        """Submit the canonical request using the SendGrid API."""
        from_email = Email(
            email=request.sender.email,
            name=request.sender.name,
        )
        to_emails = [
            To(email=str(recipient.email), name=recipient.name)
            for recipient in request.recipients
        ]

        mail = Mail(from_email=from_email, to_emails=to_emails, subject=request.subject)

        if "<html" in request.message:
            mail.content = HtmlContent(content=request.message)
        else:
            mail.content = Content(mime_type=MimeType.text, content=request.message)

        if request.ccs:
            mail.cc = [
                Cc(email=str(recipient.email), name=recipient.name)
                for recipient in request.ccs
            ]
        if request.bccs:
            mail.bcc = [
                Bcc(email=str(recipient.email), name=recipient.name)
                for recipient in request.bccs
            ]

        if request.attachments:
            mail.attachment = [
                Attachment(
                    file_content=FileContent(attachment.content),
                    file_name=FileName(attachment.filename),
                    file_type=FileType(attachment.type),
                )
                for attachment in request.attachments
            ]

        try:
            response = self.mail_client.client.mail.send.post(request_body=mail.get())
            status_code = response.status_code
            if 400 <= status_code <= 499:
                raise DeliveryRejectedException(
                    f"Sending email failed with status code: {status_code}"
                )
            if not 200 <= status_code <= 299:
                raise DeliveryOutcomeUnknownException(
                    f"Sending email outcome unknown with status code: {status_code}"
                )
            # pylint: disable=duplicate-code
            return {
                "success": True,
                "message": f"Message from {request.sender.email} successfully accepted",
            }
        except Exception as err:
            if isinstance(
                err, (DeliveryRejectedException, DeliveryOutcomeUnknownException)
            ):
                raise
            log.error(f"Failed to send email with SendGrid: {err}")
            status_code = getattr(err, "status_code", None)
            if status_code is not None and 400 <= status_code <= 499:
                raise DeliveryRejectedException(
                    "SendGrid explicitly rejected the email request"
                ) from err
            raise DeliveryOutcomeUnknownException(
                "Sending email with SendGrid failed; provider acceptance is unknown"
            ) from err
