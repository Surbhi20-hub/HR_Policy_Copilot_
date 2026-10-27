"""Tests for src/logging_utils.py: employee IDs must never appear in a log line."""
import io
import logging

import pytest

from src.logging_utils import MaskingFormatter, get_logger, mask_text, setup_logging


def test_mask_text_hides_the_last_three_digits_of_every_id() -> None:
    assert mask_text("E1001") == "E1***"
    assert mask_text("lookup for E1001 and I2001, not E12") == "lookup for E1*** and I2***, not E12"
    assert mask_text("nothing to hide") == "nothing to hide"
    assert mask_text("E10012") == "E10012"  # not an ID: a longer number is left alone


@pytest.fixture
def log_output():
    """Attach a masking handler to our logger and give back what it prints."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(MaskingFormatter("%(levelname)s %(message)s"))
    logger = logging.getLogger("copilot")
    old_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    yield stream
    logger.removeHandler(handler)
    logger.setLevel(old_level)


def test_logger_output_is_masked_even_with_arguments_and_tracebacks(log_output) -> None:
    logger = get_logger("test")
    logger.info("hello %s", "E1003")
    try:
        raise ValueError("bad employee I2001")
    except ValueError:
        logger.exception("failed for E1002")
    text = log_output.getvalue()
    assert "E1***" in text and "I2***" in text
    assert "E1003" not in text and "E1002" not in text and "I2001" not in text


def test_setup_logging_masks_and_does_not_add_a_second_handler() -> None:
    root = logging.getLogger()
    before = len(root.handlers)
    try:
        setup_logging()
        after_first = len(root.handlers)
        setup_logging()
        assert len(root.handlers) == after_first and after_first <= before + 1
        assert all(isinstance(h.formatter, MaskingFormatter) for h in root.handlers)
    finally:
        for handler in root.handlers[:]:
            if getattr(handler, "masks_ids", False):
                root.removeHandler(handler)