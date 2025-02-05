"""This module contains utilities for the speech API."""

import logging
from logging import Logger
from typing import Optional

from .config import LOG_LEVEL


def get_log_level_from_str(*, log_level_str: str = LOG_LEVEL) -> int:
    """Get log level from string.

    Parameters
    ----------
    log_level_str
        The log level.

    Returns
    -------
    int
        The log level.
    """

    log_level_dict = {
        "CRITICAL": logging.CRITICAL,
        "DEBUG": logging.DEBUG,
        "ERROR": logging.ERROR,
        "INFO": logging.INFO,
        "NOTSET": logging.NOTSET,
        "WARNING": logging.WARNING,
    }

    return log_level_dict.get(log_level_str.upper(), logging.INFO)


def setup_logger(*, log_level: Optional[int] = None, name: str = __name__) -> Logger:
    """Setup logger for the application.

    Parameters
    ----------
    log_level
        The log level.
    name
        The name of the logger.

    Returns
    -------
    Logger
        The logger.
    """

    log_level = log_level or get_log_level_from_str()
    logger = logging.getLogger(name)

    # If the logger already has handlers, assume it was already configured and return
    # it.
    if logger.handlers:
        return logger

    logger.setLevel(log_level)

    formatter = logging.Formatter(
        "%(asctime)s %(filename)20s%(lineno)4s : %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
    )

    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger
