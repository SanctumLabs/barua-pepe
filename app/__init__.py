from fastapi import FastAPI
from app.logger import log
from app.config import config
from app.api import monitoring_router, mail_router
from app.infra.handlers import attach_exception_handlers
from app.infra.middleware import attach_middlewares


async def on_startup():
    log.info("Starting Up")


async def on_teardown():
    log.info("Shutting down")


app = FastAPI(
    title="BaruaPepe",
    description="Simple RESTful Email Server",
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
