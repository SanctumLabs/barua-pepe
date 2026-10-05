"""Application operation for accepting email requests for asynchronous delivery."""

from typing import Protocol

from app.domain.entities import EmailRequest


# pylint: disable=too-few-public-methods
class EmailDispatcher(Protocol):
    """Interface for adapters that enqueue email requests for delivery."""

    def dispatch(self, request: EmailRequest, request_id: str | None = None) -> None:
        """Accept an email request for asynchronous processing."""


def dispatch_email(
    request: EmailRequest,
    dispatcher: EmailDispatcher,
    request_id: str | None = None,
) -> None:
    """Submit an email request through the configured dispatch adapter."""
    dispatcher.dispatch(request, request_id)
