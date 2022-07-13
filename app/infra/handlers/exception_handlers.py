from fastapi import Request, FastAPI
from starlette.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.api.dto import ApiError


def _rewrite_error(e):
    field = e["loc"][-1]
    message = e["msg"].capitalize()
    typ = e["type"]

    if typ == "value_error.missing":
        message = "This field is required"

    return field, message


def attach_exception_handlers(app: FastAPI):
    @app.exception_handler(ApiError)
    async def api_exception_handler(request: Request, error: ApiError):
        return JSONResponse(
            status_code=error.status,
            content={
                "status": error.status,
                "message": error.message,
                "data": getattr(error, "data", {}),
            },
        )

    @app.exception_handler(HTTPException)
    async def api_exception_handler(request: Request, error: HTTPException):
        try:
            message = error.detail
        except Exception as e:
            message = "Internal server error"

        return JSONResponse(
            status_code=error.status_code,
            content={"status": error.status_code, "message": message},
        )

    @app.exception_handler(Exception)
    async def api_exception_handler(request: Request, error: Exception):
        return JSONResponse(
            status_code=500, content={"status": 500, "message": "Internal server error"}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        error_list = [_rewrite_error(e) for e in exc.errors()]
        errors = {}
        for error in error_list:
            errors.setdefault(error[0], []).append(error[1])

        return JSONResponse(
            status_code=400,
            content={
                "status": 400,
                "message": "Something went wrong, please check the error messages below",
                "data": {"errors": errors},
            },
        )
