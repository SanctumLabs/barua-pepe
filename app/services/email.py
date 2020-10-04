"""
Send email service wrapper. This handles sending the actual email to recipients and handles connection to an SMTP client
if provided with the credentials to. If that fails, this will use an alternative to send an email using Sendgrid API.
Ensure that the correct environment variables have been set for the SMTP client and Sendgrid for this method to work.
These env variables are imported and included in the config.py file under the Config class for these to be available in
the current application context
"""
from app import mail
from flask_mail import Message
from app.logger import log as logger
from flask import current_app
from .exceptions import EmailSendingException, ServiceIntegrationException
import requests


@logger.catch
def send_plain_mail(to: list, subject: str, message: str, from_: dict = None, bcc: list = None, cc: list = None,
                    attachments: list = None):
    """
    Sends a plain text email to a list of recipients with optiona Carbon Copies and Blind Carbon Copies. This includes
    an option for sending email attachments
    :param dict from_: sender of email (Optional), will default to value set in MAIL_DEFAULT_SENDER config
    This is a dictionary with the email and name key value pairs
    :param list attachments: List of attachments to send in the email
    :param list cc: Carbon Copy recipients (Optional)
    :param list bcc: Blind Carbon copy recipients (Optional)
    :param str message: Message to send in body of email
    :param list to: List of recipients of this email
    :param str subject: The subject of the email
    """

    try:
        logger.info(f"Sending email to {to}")

        # Set the message sender it it exists else default it
        sender = from_.get("email") if from_ else current_app.config.get("MAIL_DEFAULT_SENDER")

        msg = Message(
            sender=sender,
            subject=subject,
            recipients=to,
            cc=cc,
            bcc=bcc)

        if "<html" in message:
            msg.html = message
        else:
            msg.body = message

        if attachments:
            for attachment in attachments:
                msg.attach(filename=attachment.get("filename"), content_type=attachment.get("content"))

        mail.send(msg)
        return dict(success=True, message="Message successfully sent")
    except Exception as e:
        # this should only happen if there is a fallback and we fail to send emails with the default setting
        # if in that event, then the application should try sending an email using a MAIL API

        logger.error(f"Failed to send email with error {e}")
        logger.warning(f"Using alternative to send email")

        # get the token and base url
        token = current_app.config.get("MAIL_TOKEN")
        base_url = current_app.config.get("MAIL_API_URL")

        recipients_to = [{"email": email} for email in to]

        # this will be used to construct the recipients of the email
        recipients = dict(to=recipients_to)

        if cc:
            recipients_cc = [{"email": email} for email in cc]

            recipients.update(dict(cc=recipients_cc))

        if bcc:
            recipients_bcc = [{"email": email} for email in bcc]

            recipients.update(dict(bcc=recipients_bcc))

        sender = {"email": from_.get("email") if from_ else current_app.config.get("MAIL_DEFAULT_SENDER"),
                  "name": from_.get("name") if from_ else current_app.config.get("MAIL_DEFAULT_SENDER")}

        request_body = {
            "personalizations": [
                recipients
            ],
            "from": sender,
            "subject": subject,
            "content": [
                {
                    "type": "text/html",
                    "value": message
                }
            ]
        }

        # if we have attachments, add them to the request body
        if attachments:
            request_body.update(dict(attachments=attachments))

        try:

            headers = {"Authorization": f"Bearer {token}"}
            response = requests.post(url=base_url, json=request_body, headers=headers)

            if not response.ok:
                raise ServiceIntegrationException(f"Sending email failed with status code: {response.status_code}")
            else:
                return dict(
                    success=True,
                    message="Message successfully sent",
                )

        except Exception as e:
            logger.error(f"Failed to send message with alternative with error {e}")
            raise EmailSendingException(f"Failed to send email message with error {e}")
