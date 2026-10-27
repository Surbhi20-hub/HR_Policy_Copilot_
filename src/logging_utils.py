"""Logging helper: every log line has employee IDs masked (E1001 -> E1***).

Use it like this:
    from src.logging_utils import get_logger, setup_logging
    setup_logging()                      # once, at program start
    logger = get_logger("graph")
    logger.info("looked up %s", "E1001")  # prints: ... looked up E1***
"""
import logging
import os
import re

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
APP_LOGGER = "copilot"  # all our loggers are children of this one, so one setting controls them
EMPLOYEE_ID = re.compile(r"\b([EI]\d)\d{3}\b")  # E1001, E1002, E1003, I2001 ...


def mask_text(text: str) -> str:
    """Hide the last 3 digits of every employee ID inside a text: 'E1001 and I2001' -> 'E1*** and I2***'."""
    return EMPLOYEE_ID.sub(r"\1***", text)


class MaskingFormatter(logging.Formatter):
    """A formatter that masks the finished line, including any traceback text."""

    def format(self, record: logging.LogRecord) -> str:
        return mask_text(super().format(record))


def get_logger(name: str) -> logging.Logger:
    """A logger such as 'copilot.graph'."""
    return logging.getLogger(f"{APP_LOGGER}.{name}")


def setup_logging(level: str | None = None) -> None:
    """Print our logs to the console with IDs masked. Safe to call many times."""
    root = logging.getLogger()
    root.setLevel(logging.WARNING)  # libraries (httpx, langchain...) stay quiet
    if not any(getattr(handler, "masks_ids", False) for handler in root.handlers):
        handler = logging.StreamHandler()
        handler.masks_ids = True  # a marker, so a second call does not add a second handler
        root.addHandler(handler)
    for handler in root.handlers:  # also cover handlers that were added earlier by someone else
        handler.setFormatter(MaskingFormatter(LOG_FORMAT))
    logging.getLogger(APP_LOGGER).setLevel((level or os.getenv("LOG_LEVEL", "INFO")).upper())