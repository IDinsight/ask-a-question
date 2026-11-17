"""Shared infrastructure helpers: outbound HTTP client, Google Cloud Storage,
LiteLLM chat-completion and embedding calls."""

import mimetypes
from io import BytesIO
from typing import Any, Optional
from uuid import uuid4

import aiohttp
from google.cloud import storage  # type: ignore
from langfuse.decorators import langfuse_context  # type: ignore  # type: ignore
from litellm import acompletion, aembedding

from app.core.config import (
    LITELLM_API_KEY,
    LITELLM_ENDPOINT,
    LITELLM_MODEL_DEFAULT,
    LITELLM_MODEL_EMBEDDING,
)
from app.core.observability import setup_logger

# ---- from core/http
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


def set_global_http_client(*, http_client: HttpClient) -> None:
    """Set the value for the global variable _HTTP_CLIENT.

    Parameters
    ----------
    http_client
        The value to set for the global variable _HTTP_CLIENT.
    """

    global _HTTP_CLIENT
    _HTTP_CLIENT = http_client()


# ---- from core/storage
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


# ---- from core/llm
logger = setup_logger(name="LLM_call")


async def ask_llm_async(
    *,
    json_: bool = False,
    litellm_endpoint: str | None = LITELLM_ENDPOINT,
    litellm_model: str | None = LITELLM_MODEL_DEFAULT,
    llm_generation_params: Optional[dict[str, Any]] = None,
    messages: Optional[list[dict[str, str | None]]] = None,
    metadata: dict | None = None,
    system_message: Optional[str] = None,
    user_message: Optional[str] = None,
) -> str:
    """This is a generic function to send an LLM call to a model provider using
    `litellm`.

    Parameters
    ----------
    json_
        Specifies whether the response should be returned as a JSON object.
    litellm_endpoint
        The litellm endpoint.
    litellm_model
        The name of the LLM model for the `litellm` proxy server.
    llm_generation_params
        The LLM generation parameters. If `None`, then a default set of parameters will
        be used.
    messages
        List of dictionaries containing the messages. Each dictionary must contain the
        keys `content` and `role` at a minimum. If `None`, then `user_message` and
        `system_message` must be provided.
    metadata
        Dictionary containing additional metadata for the `litellm` LLM call.
    system_message
        The system message. If `None`, then `messages` must be provided.
    user_message
        The user message. If `None`, then `messages` must be provided.

    Returns
    -------
    str
        The appropriate response from the LLM model.
    """
    if metadata is None:
        metadata = {}

    metadata["generation_name"] = litellm_model
    metadata["trace_id"] = langfuse_context.get_current_trace_id()

    extra_kwargs = {}
    if json_:
        extra_kwargs["response_format"] = {"type": "json_object"}

    if not messages:
        assert isinstance(user_message, str) and isinstance(system_message, str)
        messages = [
            {"content": system_message, "role": "system"},
            {"content": user_message, "role": "user"},
        ]

    llm_generation_params = llm_generation_params or {
        "max_tokens": 1024,
        "temperature": 1,
    }

    logger.info(f"LLM input: 'model': {litellm_model}, 'endpoint': {litellm_endpoint}")

    try:
        llm_response_raw = await acompletion(
            model=litellm_model,
            messages=messages,
            api_base=litellm_endpoint,
            api_key=LITELLM_API_KEY,
            metadata=metadata,
            **extra_kwargs,
            **llm_generation_params,
        )
    except Exception as err:
        logger.error("Error calling the LLM", exc_info=True)
        raise LLMCallException(f"Error during LLM call: {err}") from err

    # Optionally check if the returned response contains an error field
    if hasattr(llm_response_raw, "error") and llm_response_raw.error:
        error_msg = getattr(llm_response_raw, "error", "Unknown error")
        logger.error(f"LLM call returned an error: {error_msg}")
        raise LLMCallException(f"LLM call returned an error: {error_msg}")

    # Ensure that the response has valid content
    try:
        content = llm_response_raw.choices[0].message.content
    except (AttributeError, IndexError) as e:
        logger.error("LLM response structure is not as expected", exc_info=True)
        raise LLMCallException("LLM response structure is not as expected") from e

    logger.info(f"LLM output: {content}")
    return content


class LLMCallException(Exception):
    """Custom exception for LLM call errors."""

    pass


def format_prompt(
    *,
    prompt: str,
    prompt_kws: Optional[dict[str, Any]] = None,
    remove_leading_blank_spaces: bool = True,
) -> str:
    """Format prompt.

    Parameters
    ----------
    prompt
        String denoting the prompt.
    prompt_kws
        If not `None`, then a dictionary containing <key, value> pairs of parameters to
        use for formatting `prompt`.
    remove_leading_blank_spaces
        Specifies whether to remove leading blank spaces from the prompt.

    Returns
    -------
    str
        The formatted prompt.
    """

    if remove_leading_blank_spaces:
        prompt = "\n".join([m.lstrip() for m in prompt.split("\n")])
    return prompt.format(**prompt_kws) if prompt_kws else prompt


def remove_json_markdown(*, text: str) -> str:
    """Remove json markdown from text.

    Parameters
    ----------
    text
        The text containing the json markdown.

    Returns
    -------
    str
        The text with the json markdown removed.
    """

    text = text.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text.removeprefix("```json").removesuffix("```")
    text = text.replace(r"\{", "{").replace(r"\}", "}")
    return text.strip()


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
    if metadata is None:
        metadata = {}

    metadata["trace_id"] = langfuse_context.get_current_trace_id()

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
