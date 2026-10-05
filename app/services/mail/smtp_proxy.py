"""
SMTP Proxy service. This wraps functionality around an SMTP library
"""

from typing import List, Dict
import smtplib
import ssl
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText

from app.config import config
from app.logger import log
from app.utils import singleton
from app.domain.entities import EmailRequest
from .email_service import EmailDeliveryResult, EmailService
from .exceptions import (
    DeliveryOutcomeUnknownException,
    DeliveryRejectedException,
    ServiceIntegrationException,
)


@singleton
class SmtpServer(EmailService):
    """
    SMTP Server
    """

    def __init__(
        self, host: str | None = config.mail_server, port: int | None = config.mail_port
    ):
        self.host = host
        self.port = port
        self.context = ssl.create_default_context()
        if config.mail_use_ssl:
            self.server = smtplib.SMTP_SSL(host=host, port=port, context=self.context)
        else:
            self.server = smtplib.SMTP(host=host, port=port)

    def login(self, username: str, password: str):
        """
        Logs into SMTP server
        """
        log.info(f"Logging into SMTP {self.host}")
        try:
            self.server.ehlo()
            if config.mail_use_tls:
                self.server.starttls(context=self.context)
                self.server.login(user=username, password=password)
            if config.mail_use_ssl:
                self.server.login(
                    user=config.mail_username, password=config.mail_password
                )
            self.server.ehlo()
        # pylint: disable=broad-except
        except Exception as err:
            log.error(f"Failed to login {err}")
            self.server.quit()

    def logout(self):
        """
        Logs out of SMTP server
        """
        log.info(f"Logging out of SMTP {self.host}")
        try:
            self.server.quit()
        # pylint: disable=broad-except
        except Exception as err:
            log.error(f"Failed to quite smtp server {err}")
            self.server.quit()

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def sendmail(
        self,
        sender: Dict[str, str],
        recipients: List[Dict[str, str]],
        subject: str,
        message: str,
        ccs: List[Dict[str, str]] | None = None,
        bcc: List[Dict[str, str]] | None = None,
        attachments: List[Dict[str, str]] | None = None,
    ):
        """
        Sends plain email
        """
        body = MIMEMultipart()
        body["From"] = sender.get("email")
        body["To"] = ", ".join(email.get("email") for email in recipients)
        if ccs:
            body["Cc"] = ", ".join(email.get("email") for email in ccs)
        body["Subject"] = subject

        body.attach(MIMEText(message, "plain"))

        if attachments:
            part = MIMEBase("application", "octet-stream")

            for attachment in attachments:
                filename = attachment.get("filename")
                content = attachment.get("content")

                part.set_payload(content)

                # Encode file in ASCII characters to send by email
                encoders.encode_base64(part)

                # Add header as key/value pair to attachment part
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {filename}",
                )

            body.attach(part)

        text = body.as_string()

        try:
            if not self.__check_connection():
                self.server.connect(host=config.mail_server, port=config.mail_port)
            # pylint: disable=duplicate-code
            self.server.sendmail(
                from_addr=sender.get("email"),
                to_addrs=[
                    email.get("email")
                    for email in recipients + (ccs or []) + (bcc or [])
                ],
                msg=text,
            )
            return {
                "success": True,
                "message": f"Message from {sender} successfully sent to {recipients}",
            }
        # pylint: disable=broad-except
        except Exception as err:
            log.error(f"Failed to send email {err}")
            raise ServiceIntegrationException(
                f"Sending email from {sender} to {recipients} failed"
            ) from err

    def send_email(self, request: EmailRequest) -> EmailDeliveryResult:
        """Submit the canonical email request using the SMTP server."""
        sender = request.sender.dict()
        recipients = [recipient.dict() for recipient in request.recipients]
        ccs = [recipient.dict() for recipient in request.ccs or []]
        bccs = [recipient.dict() for recipient in request.bccs or []]
        attachments = [attachment.dict() for attachment in request.attachments or []]

        try:
            response = self.sendmail(
                sender=sender,
                recipients=recipients,
                ccs=ccs,
                bcc=bccs,
                subject=request.subject,
                message=request.message,
                attachments=attachments,
            )
            return response
        except Exception as err:
            definitive_rejections = (
                smtplib.SMTPRecipientsRefused,
                smtplib.SMTPHeloError,
                smtplib.SMTPAuthenticationError,
                smtplib.SMTPConnectError,
                smtplib.SMTPSenderRefused,
                smtplib.SMTPDataError,
            )
            if isinstance(err.__cause__, definitive_rejections):
                raise DeliveryRejectedException(
                    "SMTP explicitly rejected the email request"
                ) from err
            raise DeliveryOutcomeUnknownException(
                "SMTP failed without confirming whether the email request was accepted"
            ) from err

    def __check_connection(self) -> bool:
        """
        Checks connection of SMTP server
        """
        try:
            status = self.server.noop()[0]
        # pylint: disable=broad-except
        except Exception as err:
            log.error(f"SMTP Server is disconnected {err}")
            status = -1
        return status == 250
