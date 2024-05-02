import hashlib
import logging
from logging import Logger
from typing import List
from uuid import uuid4

import aiohttp
from litellm import aembedding

from .config import (
    LITELLM_API_KEY,
    LITELLM_ENDPOINT,
    LITELLM_MODEL_EMBEDDING,
    LOG_LEVEL,
)


def get_key_hash(retrieval_key: str) -> str:
    """Hashes the retrieval key using SHA256."""
    return hashlib.sha256(retrieval_key.encode()).hexdigest()


def get_log_level_from_str(log_level_str: str = LOG_LEVEL) -> int:
    """
    Get log level from string
    """
    log_level_dict = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }

    return log_level_dict.get(log_level_str.upper(), logging.INFO)


def generate_secret_key() -> str:
    """
    Generate a secret key for the user query
    """
    return uuid4().hex


async def embedding(text_to_embed: str) -> List[float]:
    """
    Get embedding for the given text
    """
    content_embedding = await aembedding(
        model=LITELLM_MODEL_EMBEDDING,
        input=text_to_embed,
        api_base=LITELLM_ENDPOINT,
        api_key=LITELLM_API_KEY,
    )

    return content_embedding.data[0]["embedding"]


def setup_logger(
    name: str = __name__, log_level: int = get_log_level_from_str()
) -> Logger:
    """
    Setup logger for the application
    """
    logger = logging.getLogger(name)

    # If the logger already has handlers,
    # assume it was already configured and return it.
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


class HttpClient:
    """
    HTTP client for call other endpoints
    """

    session: aiohttp.ClientSession | None = None

    def start(self) -> None:
        """
        Create AIOHTTP session
        """
        self.session = aiohttp.ClientSession()

    async def stop(self) -> None:
        """
        Close AIOHTTP session
        """
        if self.session is not None:
            await self.session.close()
        self.session = None

    def __call__(self) -> aiohttp.ClientSession:
        """
        Get AIOHTTP session
        """
        assert self.session is not None
        return self.session


_HTTP_CLIENT: aiohttp.ClientSession | None = None


def get_http_client() -> aiohttp.ClientSession:
    """
    Get HTTP client
    """
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.closed:
        http_client = HttpClient()
        http_client.start()
        _HTTP_CLIENT = http_client()
    return _HTTP_CLIENT
