"""Tests for structured logging setup."""

import logging

import structlog

from analytis.logging import configure_logging, get_logger


def test_configure_logging_console_format() -> None:
    configure_logging(level="INFO", fmt="console")
    logger = get_logger("test")
    assert isinstance(logger, structlog.stdlib.BoundLogger)


def test_configure_logging_json_format() -> None:
    configure_logging(level="DEBUG", fmt="json")
    root = logging.getLogger()
    assert root.level == logging.DEBUG


def test_get_logger_returns_bound() -> None:
    configure_logging(level="INFO", fmt="console")
    logger = get_logger(__name__)
    logger = logger.bind(component="test")
    assert "component" in logger._context
