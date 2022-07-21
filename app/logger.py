"""
Logger configurations, this uses loguru to handle logs
Reference: https://github.com/Delgan/loguru
"""

import os
import sys
import logging
from loguru import logger as log
import uvicorn.logging

logging.root.setLevel(logging.INFO)
console_formatter = uvicorn.logging.ColourizedFormatter(
    "{levelprefix:<8} {name}: {message}", style="{", use_colors=True
)
root = logging.getLogger()
for handler in root.handlers:
    handler.setFormatter(console_formatter)


def configure_log_sink(log_type: str):
    return (
        f"logs/{log_type}.log" if os.environ.get("ENV") == "development" else sys.stdout
    )


def backtrace() -> bool:
    return True if os.environ.get("ENV", "development") == "development" else False


# info log configurations
log.add(
    sink=configure_log_sink("info"),
    backtrace=backtrace(),
    colorize=True,
    format="<green>{time}</green> <level>{message}</level>",
    # format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    enqueue=True,
    level="INFO",
)

# error logs
log.add(
    sink=configure_log_sink("error"),
    backtrace=backtrace(),
    colorize=True,
    format="<green>{time}</green> <level>{message}</level>",
    # format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    enqueue=True,
    level="ERROR",
)

# debug logs
log.add(
    sink=configure_log_sink("debug"),
    backtrace=backtrace(),
    colorize=True,
    format="<green>{time}</green> <level>{message}</level>",
    # format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    enqueue=True,
    level="DEBUG",
)

# warning logs
log.add(
    sink=configure_log_sink("warn"),
    backtrace=backtrace(),
    colorize=True,
    format="<green>{time}</green> <level>{message}</level>",
    # format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    enqueue=True,
    level="WARNING",
)

# critical logs
log.add(
    sink=configure_log_sink("critical"),
    backtrace=backtrace(),
    colorize=True,
    format="<green>{time}</green> <level>{message}</level>",
    # format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    enqueue=True,
    level="CRITICAL",
)

# trace logs
log.add(
    sink=configure_log_sink("trace"),
    backtrace=backtrace(),
    colorize=True,
    format="<green>{time}</green> <level>{message}</level>",
    # format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    enqueue=True,
    level="TRACE",
)
