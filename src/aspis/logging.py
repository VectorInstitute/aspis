"""Logging setup for the Aspis application."""

import logging
import os
from typing import Literal


_logger = None


def setup_logging(runtime: Literal["api", "ui"]) -> None:
    """
    Set up module-level logging for the specified runtime.
    
    Configures the logging level from the `LOG_LEVEL` environment variable (defaults to `INFO`) and initializes the module-global logger used by `get_logger`. For `runtime == "api"` the function adjusts the `"uvicorn.access"` logger; for other values it configures basic logging and uses the module logger.
    
    Args:
        runtime: The runtime to configure logging for, expected to be `"api"` or `"ui"`.
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
    """
    Retrieve the module-level logger configured by `setup_logging`.
    
    Returns:
        logging.Logger: The configured logger instance.
    
    Raises:
        ValueError: If the logger has not been configured via `setup_logging`.
    """
    if _logger is None:
        raise ValueError("Logger not setup")

    return _logger
