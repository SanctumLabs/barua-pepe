import time
from fastapi import Request, FastAPI
from app.logger import log


def attach_middlewares(app: FastAPI):
    @app.middleware("http")
    async def log_request_time(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        log.info(f"Request: {request.url} took {process_time}")
        return response

    @app.middleware("http")
    async def after_request(request: Request, call_next):
        """
        Is handled after each request and can be used to add headers to the response or handle further processing
        :param request: Request object that is received from client
        :param call_next: receives request as parameters and passes it to the next execution
        """
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response
