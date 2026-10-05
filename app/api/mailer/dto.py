"""
DTO objects for mail endpoint
"""
from typing import List

# pylint: disable=no-name-in-module
from pydantic import BaseModel, ConfigDict, Field, root_validator
from app.domain.entities.email_request import EmailRequest
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
class EmailRequestDto(EmailRequest):
    """
    Email Request Payload
    """

    sender: EmailSenderDto = Field(alias="from")
    recipients: List[EmailRecipientDto] = Field(alias="to")
    ccs: List[EmailRecipientDto] | None = Field(default=None, alias="cc")
    bccs: List[EmailRecipientDto] | None = Field(default=None, alias="bcc")
    attachments: List[EmailAttachmentDto] | None = None

    model_config = ConfigDict(populate_by_name=True)

    @root_validator(pre=True)
    # pylint: disable=no-self-argument
    def accept_from_field_name(cls, values):
        """Accepts the historical ``from_`` spelling as well as ``from``."""
        if isinstance(values, dict) and "from" not in values and "from_" in values:
            values = dict(values)
            values["from"] = values.pop("from_")
        return values

    def to_email_request(self) -> EmailRequest:
        """Converts the HTTP representation into the canonical request."""
        return EmailRequest.parse_obj(self.dict())


# pylint: disable=too-few-public-methods
class EmailResponseDto(BaseModel):
    """
    Email Response Payload
    """

    status: int
    message: str
