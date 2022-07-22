"""
Task Exceptions
"""
from app.exceptions import AppException


class TaskException(AppException):
    """
    Task Exception
    """

    def __init__(self, message=None):
        super().__init__(message or "Worker failed to execute task")
