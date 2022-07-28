"""
Email Attachment
"""
# pylint: disable=no-name-in-module
from pydantic import BaseModel, validator


# pylint: disable=too-few-public-methods
class EmailAttachment(BaseModel):
    """
    Represents an Email Attachment
    """

    content: str
    filename: str
    # Mimetype of the attachment document
    type: str

    @validator("content")
    # pylint: disable=no-self-argument
    def content_must_be_valid(cls, cont):
        """
        Validates content
        """
        if len(cont) == 0:
            raise ValueError("must not be empty")
        return cont

    @validator("filename")
    # pylint: disable=no-self-argument
    def file_must_be_valid(cls, file):
        """
        Validates filename
        """
        if len(file) == 0:
            raise ValueError("must not be empty")
        return file
