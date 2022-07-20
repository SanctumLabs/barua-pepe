from typing import Dict, List
import sendgrid as mail_client
from sendgrid.helpers.mail import Email, To, Bcc, Cc, Mail, Content, HtmlContent, Attachment, MimeType, FileContent, \
    FileName, FileType
from app.utils import singleton
from app.config import get_config
from app.logger import log
from .exceptions import ServiceIntegrationException
from .email_service import EmailService
from .types import RecipientList, EmailParticipant


@singleton
class SendGridEmailService(EmailService):
    """
    Email Service wrapper around Sendgrid email service provider
    """

    def __init__(self, url: str = get_config().mail_api_url, token: str = get_config().mail_api_token):
        super().__init__()
        self.url = url
        self.token = token
        self.mail_client = mail_client.SendGridAPIClient(api_key=token)

    def send_email(self, sender: EmailParticipant, recipients: RecipientList, cc: RecipientList | None,
                   bcc: RecipientList | None, subject: str, message: str,
                   attachments: List[Dict[str, str]] | None):

        from_email = Email(email=sender.get("email"), name=sender.get("name"))
        to_emails = [To(email=recipient.get("email"), name=recipient.get("name")) for recipient in recipients]

        mail = Mail(from_email=from_email, to_emails=to_emails, subject=subject)

        if "<html" in message:
            content = HtmlContent(content=message)
            mail.content = content
        else:
            content = Content(mime_type=MimeType.text, content=message)
            mail.content = content

        if cc:
            cc_emails = [Cc(email=recipient.get("email"), name=recipient.get("name")) for recipient in cc]
            mail.cc = cc_emails
        if bcc:
            bcc_emails = [Bcc(email=recipient.get("email"), name=recipient.get("name")) for recipient in bcc]
            mail.bcc = bcc_emails

        if attachments:
            attachment_content = [
                Attachment(file_content=FileContent(attachment.get("content")),
                           file_name=FileName(attachment.get("filename")), file_type=FileType(attachment.get("type")))
                for attachment in
                attachments]
            mail.attachment = attachment_content

        try:
            response = self.mail_client.client.mail.send.post(request_body=mail.get())
            status_code = response.status_code
            if not status_code >= 200 and status_code <= 299:
                raise ServiceIntegrationException(f"Sending email failed with status code: {status_code}")
            else:
                return dict(
                    success=True,
                    message=f"Message from {sender} successfully sent to {recipients}",
                )
        except Exception as e:
            log.error(f"Failed to send email {e}")
            raise ServiceIntegrationException(f"Sending email failed with {e}")
