from pydantic import BaseModel, EmailStr


class EmailRecipient(BaseModel):
    email: EmailStr
    name: str | None
