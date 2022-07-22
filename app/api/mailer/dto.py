"""
DTO objects for mail endpoint
"""
from typing import List
# pylint: disable=no-name-in-module
from pydantic import BaseModel, validator, Field
from app.domain.entities.email_sender import EmailSender
from app.domain.entities.email_recipient import EmailRecipient
from app.domain.entities.email_attachment import EmailAttachment


# pylint: disable=too-few-public-methods
class EmailSenderDto(EmailSender):
    """Email Sender Payload"""


# pylint: disable=too-few-public-methods
class EmailRecipientDto(EmailRecipient):
    """Email Recipient Payload"""


# pylint: disable=too-few-public-methods
class EmailAttachmentDto(EmailAttachment):
    """Email Attachment Payload"""


# pylint: disable=too-few-public-methods
class EmailRequestDto(BaseModel):
    """
    Email Request Payload
    """
    from_: EmailSenderDto = Field(alias="from")
    to: List[EmailRecipientDto]
    cc: List[EmailRecipientDto] | None
    bcc: List[EmailRecipientDto] | None
    subject: str
    message: str
    attachments: List[EmailAttachmentDto] | None

    @validator("subject")
    # pylint: disable=no-self-argument
    def subject_must_be_valid(cls, sub):
        """
        Validates subject
        """
        if len(sub) == 0:
            raise ValueError("must not be empty")
        return sub

    @validator("message")
    # pylint: disable=no-self-argument
    def message_must_be_valid(cls, mes):
        """
        Validates message
        """
        if len(mes) == 0:
            raise ValueError("must not be empty")
        return mes


# pylint: disable=too-few-public-methods
class EmailResponseDto(BaseModel):
    """
    Email Response Payload
    """
    status: int
    message: str
