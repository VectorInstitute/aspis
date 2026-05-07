"""Logging setup for the Aspis application."""

import logging
import os
from typing import Literal


_logger = None


def setup_logging(runtime: Literal["api", "ui"]) -> None:
    """Setup the logging for the given runtime.

    It should be run at the beginning of the execution for each runtime (API or UI).
    The LOG_LEVEL environment variable is used to set the logging level. If not set,
    the default is INFO.

    It will set a global variable with the logger instance, which should be accessed
    by using the `get_logger` function.

    Args:
        runtime: The runtime to setup the logging for. Can be "api" or "ui".
    """
    level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)

    if runtime == "api":
        logger = logging.getLogger("uvicorn.access")
        logger.setLevel(level)
    else:
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        logger = logging.getLogger(__name__)

    global _logger  # noqa: PLW0603
    _logger = logger


def get_logger() -> logging.Logger:
    """Get the logger instance.

    It will raise a ValueError if the logger is not setup by the
    `setup_logging` function.

    Returns:
        The logger instance.
    """
    if _logger is None:
        raise ValueError("Logger not setup")

    return _logger
