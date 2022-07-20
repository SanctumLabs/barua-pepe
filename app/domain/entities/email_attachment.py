from pydantic import BaseModel, validator


class EmailAttachment(BaseModel):
    content: str
    filename: str
    type: str

    @validator("content")
    def subject_must_be_valid(cls, s):
        if len(s) == 0:
            raise ValueError("must not be empty")
        return s

    @validator("filename")
    def message_must_be_valid(cls, m):
        if len(m) == 0:
            raise ValueError("must not be empty")
        return m
