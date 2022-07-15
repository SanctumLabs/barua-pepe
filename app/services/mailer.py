"""
Send email service wrapper. This handles sending the actual email to recipients and handles connection to an SMTP client
if provided with the credentials. If that fails, this will use an alternative to send an email using an External API.
Ensure that the correct environment variables have been set for the SMTP client and External API for this method to work
These env variables are imported and included in the config.py file under the Config class for these to be available in
the current application context
"""
from typing import List, Dict
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from app.config import config
from app.logger import log as logger
from .exceptions import EmailSendingException, ServiceIntegrationException
from .smtp_proxy import server as smtp_server
import requests


@logger.catch
def send_plain_mail(sender: Dict[str, str], recipients: List[Dict[str, str]], subject: str, message: str,
                    cc: List[Dict[str, str]] | None = None, bcc: List[Dict[str, str]] | None = None,
                    attachments: List[Dict[str, str]] | None = None):
    """
    Sends a plain text email to a list of recipients with optional Carbon Copies and Blind Carbon Copies. This includes
    an option for sending email attachments
    :param dict sender: sender of email (Optional), will default to value set in MAIL_DEFAULT_SENDER config
    This is a dictionary with the email and name key value pairs
    :param list attachments: List of attachments to send in the email
    :param list cc: Carbon Copy recipients (Optional)
    :param list bcc: Blind Carbon copy recipients (Optional)
    :param str message: Message to send in body of email
    :param list recipients: List of recipients of this email
    :param str subject: The subject of the email
    """
    try:
        logger.info(f"Sending email to {recipients}")

        body = MIMEMultipart()
        body["From"] = sender.get("email")
        body["To"] = [email.get("email") for email in recipients]
        body["Cc"] = [email.get("email") for email in cc]
        body["Bcc"] = [email.get("email") for email in bcc]
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

        smtp_server.sendmail(from_addr=sender.get("email"), to_addrs=[email.get("email") for email in recipients],
                             msg=text)

        return dict(success=True, message="Message successfully sent")
    except Exception as e:
        # this should only happen if there is a fallback and we fail to send emails with the default setting
        # if in that event, then the application should try sending an email using a MAIL API

        logger.error(f"Failed to send email with error {e}")
        logger.warning(f"Using alternative to send email")

        # get the token and base url
        token = config.mail_api_token
        base_url = config.mail_api_url

        recipients_to = [{"email": email.get("email")} for email in recipients]

        # this will be used to construct the recipients of the email
        recipients = dict(to=recipients_to)

        if cc:
            recipients_cc = [{"email": email.get("email")} for email in cc]

            recipients.update(dict(cc=recipients_cc))

        if bcc:
            recipients_bcc = [{"email": email.get("email")} for email in bcc]

            recipients.update(dict(bcc=recipients_bcc))

        sender = {
            "email": sender.get("email"),
            "name": sender.get("name")
        }

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
