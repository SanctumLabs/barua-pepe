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
from .exceptions import EmailSendingException
from .smtp_proxy import SmtpServer
from .sendgrid_email_service import SendGridEmailService


@logger.catch
def send_plain_mail(request: EmailRequest):
    """
    Sends a plain text email to a list of recipients with optional Carbon Copies and Blind Carbon Copies. This includes
    an option for sending email attachments
    """
    logger.info(f"Sending email request {request}")

    sender = request.get("sender")
    recipients = request.get("recipients")
    ccs = request.get("ccs", [])
    bccs = request.get("bccs", [])
    subject = request.get("subject")
    message = request.get("message")
    attachments = request.get("attachments", [])

    if get_config().mail_smtp_enabled:
        email_svc = SmtpServer()
    else:
        email_svc = SendGridEmailService()

    try:
        response = email_svc.sendmail(
            sender=sender,
            recipients=recipients,
            ccs=ccs,
            bcc=bccs,
            subject=subject,
            message=message,
            attachments=attachments,
        )

        return response
    # pylint: disable=broad-except
    except Exception as err:
        # this should only happen if there is a fallback, or we fail to send emails with the default setting
        # if in that event, then the application should try sending an email using a MAIL API
        logger.warning(
            f"Failed to send email with error {err}, using alternative to send email"
        )
        try:
            response = email_svc.send_email(
                sender=sender,
                recipients=recipients,
                ccs=ccs,
                bcc=bccs,
                subject=subject,
                message=message,
                attachments=attachments,
            )
            return response
        # pylint: disable=broad-except
        except Exception as error:
            logger.error(f"Failed to send message with alternative with error {error}")
            raise EmailSendingException(
                f"Failed to send email message from {sender} to {recipients}"
            ) from error
