"""
Wrapper for Sendgrid Email Service Provider
"""
from typing import Dict, List
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
from .exceptions import ServiceIntegrationException
from .email_service import EmailService
from .types import RecipientList, EmailParticipant


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

    # pylint: disable=too-many-arguments
    def send_email(
        self,
        sender: EmailParticipant,
        recipients: RecipientList,
        ccs: RecipientList | None,
        bcc: RecipientList | None,
        subject: str,
        message: str,
        attachments: List[Dict[str, str]] | None,
    ):

        from_email = Email(email=sender.get("email"), name=sender.get("name"))
        to_emails = [
            To(email=recipient.get("email"), name=recipient.get("name"))
            for recipient in recipients
        ]

        mail = Mail(from_email=from_email, to_emails=to_emails, subject=subject)

        if "<html" in message:
            mail.content = HtmlContent(content=message)
        else:
            mail.content = Content(mime_type=MimeType.text, content=message)

        if ccs:
            mail.cc = [
                Cc(email=recipient.get("email"), name=recipient.get("name"))
                for recipient in ccs
            ]
        if bcc:
            mail.bcc = [
                Bcc(email=recipient.get("email"), name=recipient.get("name"))
                for recipient in bcc
            ]

        if attachments:
            mail.attachment = [
                Attachment(
                    file_content=FileContent(attachment.get("content")),
                    file_name=FileName(attachment.get("filename")),
                    file_type=FileType(attachment.get("type")),
                )
                for attachment in attachments
            ]

        try:
            response = self.mail_client.client.mail.send.post(request_body=mail.get())
            status_code = response.status_code
            if not status_code >= 200 and status_code <= 299:
                raise ServiceIntegrationException(
                    f"Sending email failed with status code: {status_code}"
                )
            # pylint: disable=duplicate-code
            return dict(
                success=True,
                message=f"Message from {sender} successfully sent to {recipients}",
            )
        # pylint: disable=broad-except
        except Exception as err:
            log.error(f"Failed to send email {err}")
            raise ServiceIntegrationException(
                f"Sending email from {sender} to {recipients} failed"
            ) from err
