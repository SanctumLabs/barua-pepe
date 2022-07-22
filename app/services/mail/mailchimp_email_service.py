"""
Wrapper for MailChimp Email Service provider
"""
from typing import Dict, List, Literal
from mailchimp_transactional.api_client import ApiClientError
import mailchimp_transactional as mail_client
from app.utils import singleton
from app.config import get_config
from app.logger import log
from .exceptions import ServiceIntegrationException
from .email_service import EmailService
from .types import RecipientList, EmailParticipant


@singleton
# pylint: disable=too-few-public-methods
class MailChimpEmailService(EmailService):
    """
    Email Service wrapper around Mailchimp email service provider
    """

    def __init__(
        self,
        url: str = get_config().mail_api_url,
        token: str = get_config().mail_api_token,
    ):
        super().__init__()
        self.url = url
        self.token = token
        self.mail_client = mail_client.Client(api_key=token)

        try:
            self.mail_client.users.ping()
            log.info("Successfully setup mail service")
        except ApiClientError as error:
            log.error(f"Failed to configure mail service {error}")
            raise ServiceIntegrationException("Failed to configure mail service") from error

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

        recipients_to = self._setup_recipients(recipients=recipients, recipient_type="to")
        recipients_to += self._setup_recipients(recipients=ccs, recipient_type="cc")
        recipients_to += self._setup_recipients(recipients=bcc, recipient_type="bcc")

        mail = {"from_email": sender.get("email"), "subject": subject, "to": recipients_to}

        if sender.get("name"):
            mail.update(dict(from_name=sender.get("name")))

        if "<html" in message:
            mail.update(dict(html=message))
        else:
            mail.update(dict(text=message))

        if attachments:
            mail.update(dict(attachments=attachments))

        try:
            response = self.mail_client.messages.send(dict(message=mail))
            log.debug(
                f"Message sent successfully from {sender} to {recipients}. Res: {response}"
            )
            return dict(
                success=True,
                message=f"Message from {sender} successfully sent to {recipients}",
            )
        except ApiClientError as err:
            log.error(f"Failed to send email {err}")
            raise ServiceIntegrationException(
                f"Sending email from {sender} to {recipients} failed"
            ) from err

    @staticmethod
    def _setup_recipients(
        recipients: RecipientList, recipient_type: Literal["to", "cc", "bcc"]
    ) -> RecipientList:
        recipients_to = []
        for recipient in recipients:
            name = recipient.get("name")

            recipient_info = {"email": recipient.get("email"), "type": recipient_type}

            if name:
                recipient_info.update(dict(name=name))

            recipients_to.append(recipient_info)
        return recipients_to
