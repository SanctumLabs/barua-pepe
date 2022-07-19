from typing import Dict, List
from mailchimp_transactional.api_client import ApiClientError
import mailchimp_transactional as mail_client
from app.utils import singleton
from app.config import get_config
from app.logger import log
from .exceptions import ServiceIntegrationException
from .email_service import EmailService


@singleton
class MailChimpEmailService(EmailService):
    """
    Email Service wrapper around Mailchimp email service provider
    """

    def __init__(self, url: str = get_config().mail_api_url, token: str = get_config().mail_api_token):
        super().__init__()
        self.url = url
        self.token = token
        self.mail_client = mail_client.Client(api_key=token)

        try:
            self.mail_client.users.ping()
            log.info("Successfully setup mail service")
        except ApiClientError as error:
            log.error(f"Failed to configure mail service")
            raise ServiceIntegrationException("Failed to configure mail service")

    def send_email(self, sender: Dict[str, str], recipients: List[Dict[str, str]], cc: List[Dict[str, str]] | None,
                   bcc: List[Dict[str, str]] | None, subject: str, message: str,
                   attachments: List[Dict[str, str]] | None):

        to = [{"email": recipient.get("email"), "type": "to"} for recipient in recipients]

        if cc:
            for cc_recipient in cc:
                recipient = {"email": cc_recipient.get("email"), "type": "cc"}
                to.append(recipient)

        if bcc:
            for bcc_recipient in bcc:
                recipient = {"email": bcc_recipient.get("email"), "type": "bcc"}
                to.append(recipient)

        mail = {
            "from_email": sender.get("email"),
            "subject": subject,
            "text": message,
            "to": to
        }

        try:
            response = self.mail_client.messages.send(dict(message=mail))
            log.debug(f"Message sent successfully from {sender} to {recipients}. Res: {response}")
            return dict(
                success=True,
                message=f"Message from {sender} successfully sent to {recipients}",
            )
        except Exception as e:
            log.error(f"Failed to send email {e}")
            raise ServiceIntegrationException(f"Sending email failed with {e}")
