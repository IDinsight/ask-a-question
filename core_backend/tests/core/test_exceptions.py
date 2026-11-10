"""Unit tests for `app.core.exceptions`."""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.core.exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
    TooManyRequestsError,
    UnauthorizedError,
    UnprocessableError,
    register_exception_handlers,
)


@pytest.fixture(scope="module")
def error_client() -> TestClient:
    """Build a tiny app whose routes raise domain errors.

    Returns
    -------
    TestClient
        Client for the tiny app.
    """

    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/not-found")
    async def not_found() -> None:
        """Raise a 404 domain error."""

        raise NotFoundError("Thing not found")

    @app.get("/rate-limited")
    async def rate_limited() -> None:
        """Raise a 429 with a `Retry-After` header and a structured detail."""

        raise TooManyRequestsError({"reason": "quota"}, headers={"Retry-After": "60"})

    return TestClient(app)


@pytest.mark.parametrize(
    "error_cls, status_code",
    [
        (AppError, status.HTTP_500_INTERNAL_SERVER_ERROR),
        (BadRequestError, status.HTTP_400_BAD_REQUEST),
        (UnauthorizedError, status.HTTP_401_UNAUTHORIZED),
        (ForbiddenError, status.HTTP_403_FORBIDDEN),
        (NotFoundError, status.HTTP_404_NOT_FOUND),
        (ConflictError, status.HTTP_409_CONFLICT),
        (UnprocessableError, status.HTTP_422_UNPROCESSABLE_CONTENT),
        (TooManyRequestsError, status.HTTP_429_TOO_MANY_REQUESTS),
        (InternalServerError, status.HTTP_500_INTERNAL_SERVER_ERROR),
    ],
)
def test_error_status_codes(error_cls: type[AppError], status_code: int) -> None:
    """Each error class pins its HTTP status and keeps the detail verbatim.

    Parameters
    ----------
    error_cls
        The error class.
    status_code
        The expected status code.
    """

    error = error_cls("detail")

    assert error.status_code == status_code
    assert error.detail == "detail"
    assert error.headers is None
    assert str(error) == "detail"


def test_status_code_override_is_per_instance() -> None:
    """An explicit status code overrides the class default for that instance."""

    error = AppError("locked", status_code=423)

    assert error.status_code == 423
    assert AppError.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_handler_returns_http_exception_shape(error_client: TestClient) -> None:
    """Domain errors render as `{"detail": ...}` with their status code.

    Parameters
    ----------
    error_client
        Client for the tiny app.
    """

    response = error_client.get("/not-found")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Thing not found"}


def test_handler_keeps_headers_and_structured_detail(
    error_client: TestClient,
) -> None:
    """Headers and non-string details are passed through to the response.

    Parameters
    ----------
    error_client
        Client for the tiny app.
    """

    response = error_client.get("/rate-limited")

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.headers["Retry-After"] == "60"
    assert response.json() == {"detail": {"reason": "quota"}}
