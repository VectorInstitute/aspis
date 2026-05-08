"""Logging setup for the Aspis application."""

import logging
import os


def get_logger_level() -> int:
    """Get the logging level from the LOG_LEVEL environment variable.

    If not set, the default is INFO.

    Returns:
        The logging level.
    """
    return getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)


def setup_logger() -> logging.Logger:
    """Sets up the logging for the given runtime, detected dynamically.

    The LOG_LEVEL environment variable is used to set the logging level. If not set,
    the default is INFO.

    Returns:
        The configuredlogger instance.
    """
    if "uvicorn.access" in logging.Logger.manager.loggerDict:
        logger = logging.getLogger("uvicorn.access")
        logger.setLevel(get_logger_level())
    else:
        logging.basicConfig(
            level=get_logger_level(),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        logger = logging.getLogger(__name__)

    return logger


logger = setup_logger()
