from pydantic import BaseModel, validator, EmailStr


class EmailSender(BaseModel):
    email: EmailStr
    name: str

    @validator("name")
    def name_must_be_valid(cls, n):
        if n == "":
            raise ValueError("must not be empty")
        return n
