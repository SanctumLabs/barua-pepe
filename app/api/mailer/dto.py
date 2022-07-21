from typing import List
from pydantic import BaseModel, validator, Field
from app.domain.entities.email_sender import EmailSender
from app.domain.entities.email_recipient import EmailRecipient
from app.domain.entities.email_attachment import EmailAttachment


class EmailSenderDto(EmailSender):
    """Email Sender Payload"""


class EmailRecipientDto(EmailRecipient):
    """Email Recipient Payload"""


class EmailAttachmentDto(EmailAttachment):
    """Email Attachment Payload"""


class EmailRequestDto(BaseModel):
    from_: EmailSenderDto = Field(alias="from")
    to: List[EmailRecipientDto]
    cc: List[EmailRecipientDto] | None
    bcc: List[EmailRecipientDto] | None
    subject: str
    message: str
    attachments: List[EmailAttachmentDto] | None

    @validator("subject")
    def subject_must_be_valid(cls, s):
        if len(s) == 0:
            raise ValueError("must not be empty")
        return s

    @validator("message")
    def message_must_be_valid(cls, m):
        if len(m) == 0:
            raise ValueError("must not be empty")
        return m


class EmailResponseDto(BaseModel):
    status: int
    message: str
