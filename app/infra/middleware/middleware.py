"""
This attaches middleware to the Application
"""
import time
from fastapi import Request, FastAPI
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from app.logger import log, bind_request_context
from app.config import config
import uuid


def attach_middlewares(app: FastAPI):
    """
    Attaches middleware to the application
    """
    if config.sentry_enabled and config.sentry_dsn != "":
        sentry_sdk.init(
            dsn=config.sentry_dsn,
            traces_sample_rate=config.sentry_traces_sample_rate,
            debug=config.sentry_debug_enabled,
            environment=config.environment,
        )

        asgi_app = SentryAsgiMiddleware(app=app)
        log.debug(f"Sentry Configured: {asgi_app.app}")

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        """
        Adds a request_id and binds a contextual logger to the request. The bound logger is
        available as request.state.log for handlers that want to emit logs with the request_id.
        Also emits timing info using the bound logger and injects X-Request-Id into the response.
        """
        request_id = str(uuid.uuid4())
        # store on request state for handlers to access
        request.state.request_id = request_id
        # create a bound logger that includes request_id and path/method
        bound_logger = bind_request_context(request_id=request_id, path=str(request.url.path), method=request.method)
        request.state.log = bound_logger

        start_time = time.time()
        try:
            # use bound logger for middleware-level log
            bound_logger.info(f"Starting request {request.method} {request.url}")
            response = await call_next(request)
            return response
        finally:
            process_time = time.time() - start_time
            bound_logger.info(f"Request {request.method} {request.url} completed in {process_time:.3f}s")

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
        # attach request id to response for tracing
        request_id = getattr(request.state, "request_id", None)
        if request_id:
            response.headers["X-Request-Id"] = request_id
        return response
