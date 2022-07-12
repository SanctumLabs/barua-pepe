from fastapi import FastAPI
from app.logger import log
from app.config import config
from app.api import monitoring_router, mail_router


async def on_startup():
    log.info("Starting Up")


async def on_teardown():
    log.info("Shutting down")


app = FastAPI(
    title="BaruaSeva",
    description="Simple RESTful Email Server",
    version="0.0.1",
    on_startup=[on_startup],
    on_teardown=[on_teardown],
    docs_url=None if config.docs_disabled else "/docs",
    redoc_url=None if config.docs_disabled else "/redoc",
)

app.include_router(monitoring_router)
app.include_router(mail_router)
