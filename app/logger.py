"""
Logger configurations, this uses loguru to handle logs.
This file now initializes optional Sentry integration and emits structured JSON logs
when running outside the development environment so logs are easier to ingest by
log aggregators.
Reference: https://github.com/Delgan/loguru
"""

import os
import sys
import logging
from loguru import logger as log
import uvicorn.logging

# Import configuration (contains sentry toggles)
from app.config import get_config

try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
except Exception:
    sentry_sdk = None

config = get_config()

# Initialize Sentry if enabled
if getattr(config, "sentry_enabled", False) and getattr(config, "sentry_dsn", "") and sentry_sdk:
    sentry_logging = LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
    sentry_sdk.init(
        dsn=config.sentry_dsn,
        integrations=[sentry_logging],
        traces_sample_rate=getattr(config, "sentry_traces_sample_rate", 0.0),
        debug=getattr(config, "sentry_debug_enabled", False),
    )


logging.root.setLevel(logging.INFO)
console_formatter = uvicorn.logging.ColourizedFormatter(
    "{levelprefix:<8} {name}: {message}", style="{", use_colors=True
)
root = logging.getLogger()
for handler in root.handlers:
    handler.setFormatter(console_formatter)


def configure_log_sink(log_type: str):
    """
    Configures log sink based on the log type and the environment
    Returns either a file path (development) or stdout (production/containerized)
    """
    return (
        f"logs/{log_type}.log" if os.environ.get("ENV") == "development" else sys.stdout
    )


def backtrace() -> bool:
    """Configures backtrace based on the env"""
    return os.environ.get("ENV", "development") == "development"


is_dev = os.environ.get("ENV", "development") == "development"


# Add sinks per level. When running non-development and writing to stdout we emit JSON
# by enabling loguru's `serialize=True` so logs are structured for aggregators.
for level, lvl_name in [
    ("INFO", "info"),
    ("ERROR", "error"),
    ("DEBUG", "debug"),
    ("WARNING", "warn"),
    ("CRITICAL", "critical"),
    ("TRACE", "trace"),
]:
    sink = configure_log_sink(lvl_name)
    # serialize only when sink is stdout in non-dev environments
    serialize = (not is_dev) and (sink is sys.stdout)
    colorize = is_dev
    fmt = (
        "<green>{time}</green> <level>{message}</level>"
        if is_dev and not serialize
        else "{\"time\": \"{time}\", \"level\": \"{level}\", \"message\": {message!r}, \"module\": \"{module}\", \"extra\": {extra} }"
    )

    log.add(
        sink=sink,
        backtrace=backtrace(),
        colorize=colorize,
        format=fmt,
        enqueue=True,
        level=level,
        serialize=serialize,
    )

# Provide a convenience wrapper to log structured events with extra context
def bind_request_context(**kwargs):
    """Bind contextual fields (request_id, user, etc.) to future log calls."""
    return log.bind(**kwargs)
