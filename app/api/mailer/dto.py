from typing import List
from pydantic import BaseModel, validator, EmailStr


class EmailSenderDto(BaseModel):
    email: EmailStr
    name: str

    @validator("name")
    def name_must_be_valid(cls, n):
        if n == "":
            raise ValueError("must not be empty")
        return n


class EmailAttachmentDto(BaseModel):
    content: str
    filename: str


class EmailRequestDto(BaseModel):
    from_: EmailSenderDto
    to: List[EmailStr]
    cc: List[EmailStr] | None
    bcc: List[EmailStr] | None
    subject: str
    message: str
    attachments: List[EmailAttachmentDto] | None
