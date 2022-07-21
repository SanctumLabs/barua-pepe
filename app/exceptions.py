"""
Application exceptions
"""
from typing import Optional


class AppException(Exception):
    """
    Base exception for all errors raised by the Application
    """

    def __init__(self, msg: Optional[str] = "An error occurred in the App"):
        # pylint: disabled=super-with-arguments
        super(AppException, self).__init__(msg)
