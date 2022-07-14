from app.exceptions import EmailGatewayError


class TaskException(EmailGatewayError):
    def __init__(self, message=None):
        if message is None:
            self.message = "Worker failed to execute task"
