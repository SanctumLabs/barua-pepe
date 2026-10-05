"""
Wrapper for MailChimp Email Service provider
"""

from typing import Literal
from mailchimp_transactional.api_client import ApiClientError
import mailchimp_transactional as mail_client
from app.utils import singleton
from app.config import get_config
from app.logger import log
from app.domain.entities import EmailRequest
from .exceptions import (
    DeliveryOutcomeUnknownException,
    DeliveryRejectedException,
    ServiceIntegrationException,
)
from .email_service import EmailDeliveryResult, EmailService
from .types import RecipientList


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
            raise ServiceIntegrationException(
                "Failed to configure mail service"
            ) from error

    def send_email(self, request: EmailRequest) -> EmailDeliveryResult:
        """Submit the canonical request using the Mailchimp Transactional API."""

        recipients_to = self._setup_recipients(
            recipients=[recipient.dict() for recipient in request.recipients],
            recipient_type="to",
        )
        recipients_to += self._setup_recipients(
            recipients=[recipient.dict() for recipient in request.ccs or []],
            recipient_type="cc",
        )
        recipients_to += self._setup_recipients(
            recipients=[recipient.dict() for recipient in request.bccs or []],
            recipient_type="bcc",
        )

        mail = {
            "from_email": request.sender.email,
            "subject": request.subject,
            "to": recipients_to,
        }

        if request.sender.name:
            mail.update({"from_name": request.sender.name})

        if "<html" in request.message:
            mail.update({"html": request.message})
        else:
            mail.update({"text": request.message})

        if request.attachments:
            mail.update(
                {
                    "attachments": [
                        attachment.dict() for attachment in request.attachments
                    ]
                }
            )

        try:
            self.mail_client.messages.send({"message": mail})
            log.debug("Message sent successfully through Mailchimp Transactional")
            return {
                "success": True,
                "message": f"Message from {request.sender.email} successfully accepted",
            }
        except ApiClientError as err:
            log.error(f"Failed to send email {err}")
            response = getattr(err, "response", None)
            status_code = getattr(response, "status_code", None)
            if status_code is None:
                status_code = getattr(err, "status_code", None)
            if status_code is not None and 400 <= status_code <= 499:
                raise DeliveryRejectedException(
                    "Mailchimp Transactional rejected the email request"
                ) from err
            raise DeliveryOutcomeUnknownException(
                "Mailchimp Transactional failed without confirming request acceptance"
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
                recipient_info.update({"name": name})

            recipients_to.append(recipient_info)
        return recipients_to
