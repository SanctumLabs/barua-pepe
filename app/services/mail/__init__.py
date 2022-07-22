"""
Mail services
"""
from .email_service import EmailService
from .sendgrid_email_service import SendGridEmailService
from .mailchimp_email_service import MailChimpEmailService
from .smtp_proxy import SmtpServer
from .mailer import send_plain_mail
