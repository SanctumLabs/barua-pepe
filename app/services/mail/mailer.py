"""
Send email service wrapper. This handles sending the actual email to recipients and handles connection to an SMTP client
if provided with the credentials. If that fails, this will use an alternative to send an email using an External API.
Ensure that the correct environment variables have been set for the SMTP client and External API for this method to work
These env variables are imported and included in the config.py file under the Config class for these to be available in
the current application context
"""
from typing import List, Dict
from app.logger import log as logger
from .exceptions import EmailSendingException
from .smtp_proxy import SmtpServer
from .sendgrid_email_service import SendGridEmailService

smtp_server = SmtpServer()
email_svc = SendGridEmailService()


@logger.catch
# pylint: disable=too-many-arguments
def send_plain_mail(
    sender: Dict[str, str],
    recipients: List[Dict[str, str]],
    subject: str,
    message: str,
    ccs: List[Dict[str, str]] | None = None,
    bcc: List[Dict[str, str]] | None = None,
    attachments: List[Dict[str, str]] | None = None,
):
    """
    Sends a plain text email to a list of recipients with optional Carbon Copies and Blind Carbon Copies. This includes
    an option for sending email attachments
    :param dict sender: sender of email (Optional), will default to value set in MAIL_DEFAULT_SENDER config
    This is a dictionary with the email and name key value pairs
    :param list attachments: List of attachments to send in the email
    :param list ccs: Carbon Copy recipients (Optional)
    :param list bcc: Blind Carbon copy recipients (Optional)
    :param str message: Message to send in body of email
    :param list recipients: List of recipients of this email
    :param str subject: The subject of the email
    """
    logger.info(
        f"Sending email message to {recipients}, cc: {ccs}, bcc:{bcc} from {sender}"
    )
    try:
        response = smtp_server.sendmail(
            sender=sender,
            recipients=recipients,
            ccs=ccs,
            bcc=bcc,
            subject=subject,
            message=message,
            attachments=attachments,
        )

        return response
    # pylint: disable=broad-except
    except Exception as err:
        # this should only happen if there is a fallback and we fail to send emails with the default setting
        # if in that event, then the application should try sending an email using a MAIL API
        logger.warning(
            f"Failed to send email with error {err}, using alternative to send email"
        )
        try:
            response = email_svc.send_email(
                sender=sender,
                recipients=recipients,
                ccs=ccs,
                bcc=bcc,
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
