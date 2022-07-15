class AppException(Exception):
    """
    Base exception for all errors raised by the Application
    """

    def __init__(self, msg=None):
        if msg is None:
            # default error message
            msg = "An error occurred in the EmailService App"
        super(AppException, self).__init__(msg)
