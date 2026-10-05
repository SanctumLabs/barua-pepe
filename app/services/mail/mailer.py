"""
Send email service wrapper. This handles sending the actual email to recipients and handles connection to an SMTP client
if provided with the credentials. If that fails, this will use an alternative to send an email using an External API.
Ensure that the correct environment variables have been set for the SMTP client and External API for this method to work
These env variables are imported and included in the config.py file under the Config class for these to be available in
the current application context
"""

from app.logger import log as logger
from app.config import get_config
from app.domain.entities import EmailRequest
from .delivery_policy import deliver_email
from .smtp_proxy import SmtpServer
from .sendgrid_email_service import SendGridEmailService


@logger.catch(reraise=True)
def send_plain_mail(request: EmailRequest):
    """
    Sends a plain text email to a list of recipients with optional Carbon Copies and Blind Carbon Copies. This includes
    an option for sending email attachments
    """
    logger.info("Sending email request", recipient_count=len(request.recipients))

    if get_config().mail_smtp_enabled:
        primary = SmtpServer
        fallback = SendGridEmailService
    else:
        primary = SendGridEmailService
        fallback = None

    return deliver_email(request, primary=primary, fallback=fallback)
