"""This module contains general utility functions for the backend application."""

# pylint: disable=global-statement
import hashlib
import logging
import mimetypes
import os
import random
import secrets
import string
from datetime import datetime, timedelta, timezone
from io import BytesIO
from logging import Logger
from typing import Optional
from uuid import uuid4

import aiohttp
import litellm
from google.cloud import storage  # type: ignore
from litellm import aembedding
from redis import asyncio as aioredis

from .config import (
    LANGFUSE,
    LITELLM_API_KEY,
    LITELLM_ENDPOINT,
    LITELLM_MODEL_EMBEDDING,
    LOG_LEVEL,
)

# To make 32-byte API keys (results in 43 characters).
SECRET_KEY_N_BYTES = 32

# To prefix trace_id with project name.
LANGFUSE_PROJECT_NAME = None

if LANGFUSE == "True":
    langFuseLogger = litellm.utils.langFuseLogger
    if langFuseLogger is None:
        langFuseLogger = litellm.integrations.langfuse.LangFuseLogger()
        LANGFUSE_PROJECT_NAME = (
            langFuseLogger.Langfuse.client.projects.get().data[0].name
        )
    elif isinstance(langFuseLogger, litellm.integrations.langfuse.LangFuseLogger):
        LANGFUSE_PROJECT_NAME = (
            langFuseLogger.Langfuse.client.projects.get().data[0].name
        )


_HTTP_CLIENT: aiohttp.ClientSession | None = None


class HttpClient:
    """HTTP client for calling other endpoints."""

    session: aiohttp.ClientSession | None = None

    def __call__(self) -> aiohttp.ClientSession:
        """Get AIOHTTP session."""

        assert self.session is not None
        return self.session

    def start(self) -> None:
        """Create AIOHTTP session."""

        self.session = aiohttp.ClientSession()

    async def stop(self) -> None:
        """Close AIOHTTP session."""

        if self.session is not None:
            await self.session.close()
        self.session = None


def create_langfuse_metadata(
    *,
    feature_name: str | None = None,
    query_id: int | None = None,
    workspace_id: int | None = None,
) -> dict:
    """Create metadata for langfuse logging.

    Parameters
    ----------
    feature_name
        The name of the feature.
    query_id
        The ID of the query.
    workspace_id
        The ID of the workspace.

    Returns
    -------
    dict
        The metadata for langfuse logging.

    Raises
    ------
    ValueError
        If neither `query_id` nor `feature_name` is provided.
    """

    trace_id_elements = []
    if query_id is not None:
        trace_id_elements += ["query_id", str(query_id)]
    elif feature_name is not None:
        trace_id_elements += ["feature_name", feature_name]
    else:
        raise ValueError("Either `query_id` or `feature_name` must be provided.")

    if LANGFUSE_PROJECT_NAME is not None:
        trace_id_elements.insert(0, LANGFUSE_PROJECT_NAME)

    metadata = {"trace_id": "-".join(trace_id_elements)}
    if workspace_id is not None:
        metadata["trace_workspace_id"] = "workspace_id-" + str(workspace_id)

    return metadata


class EmbeddingCallException(Exception):
    """Custom exception for embedding call errors."""

    pass


async def embedding(
    *, metadata: Optional[dict] = None, text_to_embed: str
) -> list[float]:
    """Get embedding for the given text.

    Parameters
    ----------
    metadata
        Metadata for `LiteLLM` embedding API.
    text_to_embed
        The text to embed.

    Returns
    -------
    list[float]
        The embedding for the given text.
    """

    try:
        content_embedding = await aembedding(
            api_base=LITELLM_ENDPOINT,
            api_key=LITELLM_API_KEY,
            input=text_to_embed,
            metadata=metadata,
            model=LITELLM_MODEL_EMBEDDING,
        )
    except Exception as err:
        raise EmbeddingCallException(f"Error during embedding call: {err}") from err

    # Validate the response structure
    try:
        embedding_value = content_embedding.data[0]["embedding"]
    except (AttributeError, IndexError, KeyError) as err:
        raise EmbeddingCallException(
            "Embedding response structure is not as expected"
        ) from err
    return embedding_value


def encode_api_limit(*, api_limit: int | None) -> int | str:
    """Encode the API limit for Redis.

    Parameters
    ----------
    api_limit
        The API limit.

    Returns
    -------
    int | str
        The encoded API limit.
    """

    return int(api_limit) if api_limit is not None else "None"


def generate_key() -> str:
    """Generate API key (default 32 byte = 43 characters).

    Returns
    -------
    str
        The generated API key.
    """

    return secrets.token_urlsafe(SECRET_KEY_N_BYTES)


async def generate_public_url(*, blob_name: str, bucket_name: str) -> str:
    """Generate a public URL for a GCS blob.

    Parameters
    ----------
    blob_name
        The name of the blob in the bucket.
    bucket_name
        The name of the GCS bucket.

    Returns
    -------
    str
        A public URL that allows access to the GCS file.
    """

    public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
    return public_url


def generate_random_filename(*, extension: str) -> str:
    """Generate a random filename with the specified extension by concatenating
    multiple UUIDv4 strings.

    Parameters
    ----------
    extension
        The file extension (e.g., '.wav', '.mp3').

    Returns
    -------
    str
        The generated random filename.
    """

    random_filename = "".join([uuid4().hex for _ in range(5)])
    return f"{random_filename}{extension}"


def generate_secret_key() -> str:
    """Generate a secret key for the user query.

    Returns
    -------
    str
        The generated secret key.
    """

    return uuid4().hex


def get_file_extension_from_mime_type(*, mime_type: Optional[str]) -> str:
    """Get file extension from MIME type.

    Parameters
    ----------
    mime_type
        The MIME type of the file.

    Returns
    -------
    str
        The file extension.
    """

    mime_to_extension = {
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/x-m4a": ".m4a",
        "audio/aac": ".aac",
        "audio/ogg": ".ogg",
        "audio/flac": ".flac",
        "audio/x-aiff": ".aiff",
        "audio/aiff": ".aiff",
        "audio/basic": ".au",
        "audio/mid": ".midi",
        "audio/x-midi": ".midi",
        "audio/webm": ".webm",
        "audio/x-ms-wma": ".wma",
        "audio/x-ms-asf": ".asf",
    }

    if mime_type:
        extension = mime_to_extension.get(mime_type, None)
        if extension:
            return extension
        extension = mimetypes.guess_extension(mime_type)
        return extension if extension else ".bin"

    return ".bin"


def get_global_http_client() -> Optional[aiohttp.ClientSession]:
    """Return the value for the global variable _HTTP_CLIENT.

    Returns
    -------
        The value for the global variable _HTTP_CLIENT.
    """

    return _HTTP_CLIENT


def get_http_client() -> aiohttp.ClientSession:
    """Get HTTP client.

    Returns
    -------
    aiohttp.ClientSession
        The HTTP client.
    """

    global_http_client = get_global_http_client()
    if global_http_client is None or global_http_client.closed:
        http_client = HttpClient()
        http_client.start()
        set_global_http_client(http_client=http_client)
    new_http_client = get_global_http_client()
    assert isinstance(new_http_client, aiohttp.ClientSession)
    return new_http_client


def get_key_hash(*, key: str) -> str:
    """Hash the API key using SHA256.

    Parameters
    ----------
    key
        The API key to hash.

    Returns
    -------
    str
        The hashed API key.
    """

    return hashlib.sha256(key.encode()).hexdigest()


def get_log_level_from_str(*, log_level_str: str = LOG_LEVEL) -> int:
    """Get log level from string.

    Parameters
    ----------
    log_level_str
        The log level string.

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


def get_password_salted_hash(*, key: str) -> str:
    """Hash the password using SHA256 with a salt.

    Parameters
    ----------
    key
        The password to hash.

    Returns
    -------
    str
        The hashed salted password.
    """

    salt = os.urandom(16)
    key_salt_combo = salt + key.encode()
    hash_obj = hashlib.sha256(key_salt_combo)
    return salt.hex() + hash_obj.hexdigest()


def get_random_int32() -> int:
    """Generate a random 32-bit integer.

    Returns
    -------
    int
        The generated 32-bit integer.
    """

    return random.randint(-(2**31), 2**31 - 1)


def get_random_string(*, size: int) -> str:
    """Generate a random string of fixed length.

    Parameters
    ----------
    size
        The size of the random string to generate.

    Returns
    -------
    str
        The generated random string.
    """

    return "".join(random.choices(string.ascii_letters + string.digits, k=size))


def set_global_http_client(*, http_client: HttpClient) -> None:
    """Set the value for the global variable _HTTP_CLIENT.

    Parameters
    ----------
    http_client
        The value to set for the global variable _HTTP_CLIENT.
    """

    global _HTTP_CLIENT
    _HTTP_CLIENT = http_client()


def setup_logger(*, log_level: Optional[int] = None, name: str = __name__) -> Logger:
    """Setup logger for the application.

    Parameters
    ----------
    log_level
        The log level for the logger.
    name
        The name of the logger.

    Returns
    -------
    Logger
        The configured logger.
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


def verify_password_salted_hash(*, key: str, stored_hash: str) -> bool:
    """Verify if the API key matches the hash.

    Parameters
    ----------
    key
        The API key to verify.
    stored_hash
        The stored hash to compare against.

    Returns
    -------
    bool
        Specifies if the API key matches the hash.
    """

    salt = bytes.fromhex(stored_hash[:32])
    original_hash = stored_hash[32:]
    key_salt_combo = salt + key.encode()
    hash_obj = hashlib.sha256(key_salt_combo)

    return hash_obj.hexdigest() == original_hash


async def update_api_limits(
    *, api_daily_quota: int | None, redis: aioredis.Redis, workspace_name: str
) -> None:
    """Update the API limits for the workspace in Redis.

    Parameters
    ----------
    api_daily_quota
        The daily API quota for the workspace.
    redis
        The Redis instance.
    workspace_name
        The name of the workspace.
    """

    now = datetime.now(timezone.utc)
    next_midnight = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    key = f"remaining-calls:{workspace_name}"
    expire_at = int(next_midnight.timestamp())
    await redis.set(key, encode_api_limit(api_limit=api_daily_quota))
    if api_daily_quota is not None:
        await redis.expireat(key, expire_at)


async def upload_file_to_gcs(
    *,
    bucket_name: str,
    content_type: Optional[str] = None,
    destination_blob_name: str,
    file_stream: BytesIO,
) -> None:
    """Upload a file stream to a Google Cloud Storage bucket and make it public.

    Parameters
    ----------
    bucket_name
        The name of the GCS bucket.
    content_type
        The content type of the file (e.g., 'audio/mpeg').
    destination_blob_name
        The name of the blob in the bucket.
    file_stream
        The file stream to upload.
    """

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    blob = bucket.blob(destination_blob_name)

    file_stream.seek(0)
    blob.upload_from_file(file_stream, content_type=content_type)
