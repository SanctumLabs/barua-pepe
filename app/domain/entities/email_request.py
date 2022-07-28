"""
Email Request
"""
from typing import List

# pylint: disable=no-name-in-module
from pydantic import BaseModel, validator
from .email_sender import EmailSender
from .email_attachment import EmailAttachment
from .email_recipient import EmailRecipient


# pylint: disable=too-few-public-methods
class EmailRequest(BaseModel):
    """
    Represents an email Request
    """

    sender: EmailSender
    recipient: List[EmailRecipient]
    cc: List[EmailRecipient] | None
    bcc: List[EmailRecipient] | None
    subject: str
    message: str
    attachments: List[EmailAttachment] | None

    @validator("subject")
    # pylint: disable=no-self-argument
    def subject_must_be_valid(cls, sub):
        """Validates subject"""
        if len(sub) == 0:
            raise ValueError("subject must not be empty")
        return sub

    @validator("message")
    # pylint: disable=no-self-argument
    def message_must_be_valid(cls, mes):
        """Validates message"""
        if len(mes) == 0:
            raise ValueError("message must not be empty")
        return mes
