from functools import lru_cache
from fastapi import FastAPI
from app.logger import log
from app.config import config, Config
from app.api import monitoring_router, mail_router
from app.infra.handlers import attach_exception_handlers
from app.infra.middleware import attach_middlewares
from app.services.smtp_proxy import login_to_smtp_server, logout_from_smtp


async def on_startup():
    log.info("Starting Up")
    login_to_smtp_server(username=config.mail_username, password=config.mail_password)


async def on_teardown():
    log.info("Shutting down")
    logout_from_smtp()


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
app.include_router(mail_router, prefix=config.base_url)
attach_exception_handlers(app)
attach_middlewares(app)


@lru_cache()
def get_config():
    return Config()
