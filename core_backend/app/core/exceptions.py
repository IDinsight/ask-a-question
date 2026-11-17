"""Domain exceptions raised by the service layer.

Services must not depend on FastAPI. Instead of raising `HTTPException`, a service
raises one of the exceptions below. `register_exception_handlers` (called from
`app.main`) converts them into JSON responses with the same shape that
`HTTPException` produces (`{"detail": ...}`), so API clients see no difference.
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.observability import setup_logger

_logger = setup_logger()


class AppError(Exception):
    """Base class for errors that map to an HTTP response.

    Subclasses only pin `status_code`; the `detail` passed in is returned to the
    client verbatim, exactly like `HTTPException(detail=...)`.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        detail: Any = None,
        *,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize the error.

        Parameters
        ----------
        detail
            The message (or structured payload) returned to the client.
        status_code
            Optional override for the class-level status code. Use it only for
            one-off codes that have no dedicated subclass.
        headers
            Optional response headers (e.g. `Retry-After`).
        """

        super().__init__(detail)
        self.detail = detail
        self.headers = headers
        if status_code is not None:
            self.status_code = status_code


class BadRequestError(AppError):
    """The request is invalid for the current state (HTTP 400)."""

    status_code = status.HTTP_400_BAD_REQUEST


class UnauthorizedError(AppError):
    """The caller is not authenticated (HTTP 401)."""

    status_code = status.HTTP_401_UNAUTHORIZED


class ForbiddenError(AppError):
    """The caller lacks the role or permission required (HTTP 403)."""

    status_code = status.HTTP_403_FORBIDDEN


class NotFoundError(AppError):
    """The requested resource does not exist (HTTP 404)."""

    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(AppError):
    """The request conflicts with existing state (HTTP 409)."""

    status_code = status.HTTP_409_CONFLICT


class UnprocessableError(AppError):
    """The request is well-formed but semantically invalid (HTTP 422)."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT


class TooManyRequestsError(AppError):
    """A quota or rate limit was exceeded (HTTP 429)."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS


class InternalServerError(AppError):
    """An unexpected failure the caller cannot fix (HTTP 500)."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


async def _app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Translate an `AppError` into the same JSON body `HTTPException` would produce.

    Parameters
    ----------
    request
        The incoming request (unused; required by the handler signature).
    exc
        The raised exception. Always an `AppError` because of how it is registered.

    Returns
    -------
    JSONResponse
        `{"detail": exc.detail}` with the exception's status code and headers.
    """

    assert isinstance(exc, AppError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a generic 500 for any exception no other handler caught.

    The client never sees the exception type, message or traceback (which can carry
    SQL, file paths or secrets). The full error is logged server-side, and Starlette
    re-raises it after this response so Sentry still records it.

    Parameters
    ----------
    request
        The incoming request; only its method and path are logged.
    exc
        The unhandled exception.

    Returns
    -------
    JSONResponse
        `{"detail": "Internal server error."}` with status 500.
    """

    _logger.error(
        "Unhandled error on %s %s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error."},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the domain-exception and catch-all handlers to the FastAPI app.

    Parameters
    ----------
    app
        The application instance.
    """

    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
