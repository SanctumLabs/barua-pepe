"""Application entry point"""

from fastapi import FastAPI, Depends
from app.logger import log
from app.config import config, Config
from app.api import monitoring_router, mail_router
from app.infra.handlers import attach_exception_handlers
from app.infra.middleware import attach_middlewares
from app.services.mail import SmtpServer
from app.services.auth import get_current_auth


async def on_startup():
    """
    on startup hook, we place startup code here that the application needs during runtime
    """
    log.info("Starting Up")
    if config.mail_smtp_enabled:
        SmtpServer().login(username=config.mail_username, password=config.mail_password)


async def on_teardown():
    """
    Performs application cleanup if necessary
    """
    log.info("Shutting down")
    if config.mail_smtp_enabled:
        SmtpServer().logout()


app = FastAPI(
    title=config.server_name,
    description=config.description,
    version="0.0.1",
    on_startup=[on_startup],
    on_teardown=[on_teardown],
    docs_url=None if config.docs_disabled else "/docs",
    redoc_url=None if config.docs_disabled else "/redoc",
)

app.include_router(monitoring_router)
app.include_router(
    mail_router, prefix=config.base_url, dependencies=[Depends(get_current_auth)]
)
attach_exception_handlers(app)
attach_middlewares(app)
