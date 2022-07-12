from pydantic.generics import GenericModel
from typing import Generic, TypeVar, Optional

DataT = TypeVar("DataT")


class ApiError(Exception):
    def __init__(
        self, status: int, message: Optional[str] = None, data: Optional[any] = None
    ):
        self.status = status
        self.message = message
        self.data = data


class ApiResponse(GenericModel, Generic[DataT]):
    status: int = 200
    data: Optional[DataT]
    message: Optional[str] = None

    class Config:
        schema_extra = {"example": {"status": 200}}


class BadRequest(ApiResponse):
    status: int = 400

    class Config:
        schema_extra = {"example": {"status": 400, "message": "Invalid JSON"}}
