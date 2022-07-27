"""
This attaches middleware to the Application
"""
import time
from fastapi import Request, FastAPI
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from app.logger import log
from app.config import config


def attach_middlewares(app: FastAPI):
    """
    Attaches middleware to the application
    """
    if config.sentry_enabled and config.sentry_dsn != "":
        sentry_sdk.init(
            dsn=config.sentry_dsn,
            traces_sample_rate=config.sentry_traces_sample_rate,
            debug=config.sentry_debug_enabled,
            environment=config.environment
        )

        asgi_app = SentryAsgiMiddleware(app=app)
        log.debug(f"Sentry Configured: {asgi_app.app}")

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
        response.headers["server"] = config.server_name
        return response
