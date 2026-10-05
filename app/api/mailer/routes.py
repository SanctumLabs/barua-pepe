"""
Mail Router
"""

from fastapi import APIRouter, Request, Response
from starlette import status
from app.logger import log as logger
from app.api.dto import ApiResponse, BadRequest
from app.exceptions import AppException
from app.application.email_dispatch import dispatch_email
from app.infra.adapters.celery_email_dispatcher import celery_email_dispatcher
from .dto import EmailRequestDto, EmailResponseDto

router = APIRouter(tags=["Email"])


@logger.catch
@router.post(
    path="/sendmail",
    summary="Submit Email",
    description="Accepts an email request for asynchronous processing",
    response_model=EmailResponseDto,
    status_code=status.HTTP_202_ACCEPTED,
)
async def send_plain_email(
    payload: EmailRequestDto, request: Request, response: Response
):
    """
    Accept a validated email request and enqueue it for asynchronous processing.
    :return: JSON response to client
    :rtype: dict
    """

    if not payload:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return BadRequest(message="No data provided")

    try:
        email_request = payload.to_email_request()

        request_id = getattr(request.state, "request_id", None)
        bound_log = getattr(request.state, "log", logger)
        bound_log.info("Enqueuing email send", recipient_count=len(payload.recipients))
        dispatch_email(email_request, celery_email_dispatcher, request_id)

        return ApiResponse(
            status=status.HTTP_202_ACCEPTED,
            data=None,
            message="Email request accepted for processing",
        )
    except AppException as exc:
        logger.error(f"Failed to send email to {payload.recipients} with error {exc}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ApiResponse(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            data=None,
            message="Failed to send email",
        )
