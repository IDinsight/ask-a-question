"""Tests for the tag management API endpoints in `app.tags.router`."""

from typing import Any, Generator
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.exceptions import AppError, BadRequestError, NotFoundError


@pytest.fixture(scope="function", params=["Tag1", ("tag3",)])
def existing_tag_id_in_workspace_1(
    access_token_admin_1: str, client: TestClient, request: pytest.FixtureRequest
) -> Generator[str, None, None]:
    """Create a tag ID in workspace 1 and return the tag ID

    Parameters
    ----------
    access_token_admin_1
        Access token for admin user 1.
    client
        Test client.
    request
        Pytest request object.

    Yields
    ------
    Generator[str, None, None]
        Tag ID.
    """

    response = client.post(
        "/tag",
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
        json={"tag_name": request.param[0]},
    )
    tag_id = response.json()["tag_id"]

    yield tag_id

    client.delete(
        f"/tag/{tag_id}",
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )


class TestManageTags:
    """Tests for tag endpoints."""

    @pytest.mark.parametrize("tag_name", ["tag_first", "tag_second"])
    async def test_create_and_delete_tag(
        self, access_token_admin_1: str, client: TestClient, tag_name: str
    ) -> None:
        """Test creating and deleting a tag.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            Test client.
        tag_name
            Tag name.
        """

        response = client.post(
            "/tag",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={"tag_name": tag_name},
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert "tag_id" in json_response
        assert "workspace_id" in json_response

        response = client.delete(
            f"/tag/{json_response['tag_id']}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize("tag_name", ["TAG_FIRST", "TAG_SECOND"])
    def test_edit_and_retrieve_tag(
        self,
        access_token_admin_1: str,
        client: TestClient,
        existing_tag_id_in_workspace_1: int,
        tag_name: str,
    ) -> None:
        """Test editing and retrieving a tag.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            Test client.
        existing_tag_id_in_workspace_1
            Existing tag ID in workspace 1.
        tag_name
            Tag name.
        """

        response = client.put(
            f"/tag/{existing_tag_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={"tag_name": tag_name},
        )

        assert response.status_code == status.HTTP_200_OK

        response = client.get(
            f"/tag/{existing_tag_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["tag_name"] == tag_name

    def test_edit_tag_not_found(
        self, access_token_admin_1: str, client: TestClient
    ) -> None:
        """Test editing a tag that does not exist.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            Test client.
        """

        response = client.put(
            "/tag/12345",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={"tag_name": "tag"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_tag(
        self,
        access_token_admin_1: str,
        client: TestClient,
        existing_tag_id_in_workspace_1: int,
    ) -> None:
        """Test listing tags.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            Test client.
        existing_tag_id_in_workspace_1
            Existing tag ID in workspace 1.
        """

        response = client.get(
            "/tag", headers={"Authorization": f"Bearer {access_token_admin_1}"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) > 0

    @pytest.mark.parametrize(
        "tag_name_1,tag_name_2", [("TAG1", "TAG1"), ("Tag2", "TAG2")]
    )
    def test_add_tag_same_name_fails(
        self,
        access_token_admin_1: str,
        client: TestClient,
        tag_name_1: str,
        tag_name_2: str,
    ) -> None:
        """TEst adding a tag with the same name.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            Test client.
        tag_name_1
            Tag name 1.
        tag_name_2
            Tag name 2.
        """

        response = client.post(
            "/tag",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={"tag_name": tag_name_1},
        )
        assert response.status_code == status.HTTP_200_OK

        response = client.post(
            "/tag",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={"tag_name": tag_name_2},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_tag(
        self,
        access_token_admin_1: str,
        client: TestClient,
        existing_tag_id_in_workspace_1: int,
    ) -> None:
        """Test deleting a tag.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            Test client.
        existing_tag_id_in_workspace_1
            Existing tag ID in workspace 1.
        """

        response = client.delete(
            f"/tag/{existing_tag_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_admin_2_get_admin_1_tag_fails(
        self,
        access_token_admin_2: str,
        client: TestClient,
        existing_tag_id_in_workspace_1: int,
    ) -> None:
        """Test admin 2 getting admin 1's tag fails.

        Parameters
        ----------
        access_token_admin_2
            Access token for admin user 2.
        client
            Test client.
        existing_tag_id_in_workspace_1
            Existing tag ID in workspace 1.
        """

        response = client.get(
            f"/tag/{existing_tag_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_2}"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_add_tag_admin_1_edit_admin_2_fails(
        self, access_token_admin_1: str, access_token_admin_2: str, client: TestClient
    ) -> None:
        """Test admin 1 adding a tag and admin 2 editing it fails.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        access_token_admin_2
            Access token for admin user 2.
        client
            Test client.
        """

        response = client.post(
            "/tag",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={"tag_name": "tag"},
        )
        assert response.status_code == status.HTTP_200_OK

        tag_id = response.json()["tag_id"]
        response = client.put(
            f"/tag/{tag_id}",
            headers={"Authorization": f"Bearer {access_token_admin_2}"},
            json={"tag_name": "tag"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# Every tag endpoint with a request that would otherwise be valid.
ALL_ENDPOINTS: list[tuple[str, str, dict[str, Any]]] = [
    ("post", "/tag/", {"json": {"tag_name": "auth_check"}}),
    ("put", "/tag/1", {"json": {"tag_name": "auth_check"}}),
    ("get", "/tag/", {}),
    ("delete", "/tag/1", {}),
    ("get", "/tag/1", {}),
]
ADMIN_ONLY_ENDPOINTS = [e for e in ALL_ENDPOINTS if e[0] != "get"]


class TestAuthAndValidation:
    """Authentication, authorization and request-validation failures."""

    @pytest.mark.parametrize(
        "headers",
        [{}, {"Authorization": "Bearer not-a-valid-jwt"}],
        ids=["no_token", "invalid_token"],
    )
    @pytest.mark.parametrize("method, path, kwargs", ALL_ENDPOINTS)
    def test_unauthenticated_request_returns_401(
        self,
        client: TestClient,
        headers: dict[str, str],
        kwargs: dict[str, Any],
        method: str,
        path: str,
    ) -> None:
        """Requests without a valid access token are rejected.

        Parameters
        ----------
        client
            Test client.
        headers
            The request headers (missing or invalid token).
        kwargs
            Extra arguments for the request (body).
        method
            The HTTP method.
        path
            The endpoint path.
        """

        response = client.request(method, path, headers=headers, **kwargs)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("method, path, kwargs", ADMIN_ONLY_ENDPOINTS)
    def test_read_only_user_is_forbidden(
        self,
        access_token_read_only_1: str,
        client: TestClient,
        kwargs: dict[str, Any],
        method: str,
        path: str,
    ) -> None:
        """Read-only users cannot create, edit or delete tags.

        Parameters
        ----------
        access_token_read_only_1
            Access token for read-only user 1 (workspace 1).
        client
            Test client.
        kwargs
            Extra arguments for the request (body).
        method
            The HTTP method.
        path
            The endpoint path.
        """

        response = client.request(
            method,
            path,
            headers={"Authorization": f"Bearer {access_token_read_only_1}"},
            **kwargs,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_read_only_user_can_list(
        self, access_token_read_only_1: str, client: TestClient
    ) -> None:
        """Read-only users can list tags.

        Parameters
        ----------
        access_token_read_only_1
            Access token for read-only user 1 (workspace 1).
        client
            Test client.
        """

        response = client.get(
            "/tag/", headers={"Authorization": f"Bearer {access_token_read_only_1}"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    @pytest.mark.parametrize(
        "method, path, kwargs",
        [
            ("post", "/tag/", {"json": {}}),
            ("post", "/tag/", {"json": {"tag_name": "x" * 51}}),
            ("put", "/tag/not-an-int", {"json": {"tag_name": "x"}}),
            ("put", "/tag/1", {"json": {"tag_name": None}}),
            ("get", "/tag/?limit=abc", {}),
            ("get", "/tag/not-an-int", {}),
            ("delete", "/tag/not-an-int", {}),
        ],
        ids=[
            "create_missing_name",
            "create_name_too_long",
            "edit_bad_id",
            "edit_null_name",
            "list_bad_limit",
            "get_bad_id",
            "delete_bad_id",
        ],
    )
    def test_invalid_request_returns_422(
        self,
        access_token_admin_1: str,
        client: TestClient,
        kwargs: dict[str, Any],
        method: str,
        path: str,
    ) -> None:
        """Malformed requests are rejected before reaching the service.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            Test client.
        kwargs
            Extra arguments for the request (body).
        method
            The HTTP method.
        path
            The endpoint path.
        """

        response = client.request(
            method,
            path,
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            **kwargs,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestRouterWiring:
    """Check how the router hands requests to, and errors from, the service layer.

    Service functions are replaced with mocks, so only authentication touches the
    database.
    """

    def test_retrieve_tag_forwards_query_params(
        self,
        access_token_admin_1: str,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Paging parameters are passed through to the service.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            Test client.
        monkeypatch
            Pytest monkeypatch fixture.
        """

        fake = AsyncMock(return_value=[])
        monkeypatch.setattr("app.tags.router.service.retrieve_tag", fake)

        response = client.get(
            "/tag/?skip=4&limit=2",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
        assert fake.await_args is not None
        kwargs = fake.await_args.kwargs
        assert (kwargs["skip"], kwargs["limit"]) == (4, 2)
        assert kwargs["workspace_name"] == "test_workspace_1"

    @pytest.mark.parametrize(
        "error, expected_status",
        [
            (BadRequestError("exists"), status.HTTP_400_BAD_REQUEST),
            (NotFoundError("missing"), status.HTTP_404_NOT_FOUND),
            (AppError("boom"), status.HTTP_500_INTERNAL_SERVER_ERROR),
        ],
        ids=["bad_request", "not_found", "internal"],
    )
    def test_service_errors_map_to_http_errors(
        self,
        access_token_admin_1: str,
        client: TestClient,
        error: AppError,
        expected_status: int,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Domain errors raised by the service become JSON error responses.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            Test client.
        error
            The domain error raised by the (mocked) service.
        expected_status
            The expected HTTP status code.
        monkeypatch
            Pytest monkeypatch fixture.
        """

        monkeypatch.setattr(
            "app.tags.router.service.edit_tag", AsyncMock(side_effect=error)
        )

        response = client.put(
            "/tag/1",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={"tag_name": "x"},
        )

        assert response.status_code == expected_status
        assert response.json() == {"detail": error.detail}


@pytest.mark.parametrize(
    "method, path",
    [("get", "/tag/99999999"), ("delete", "/tag/99999999")],
    ids=["get", "delete"],
)
def test_missing_tag_returns_404(
    access_token_admin_1: str, client: TestClient, method: str, path: str
) -> None:
    """Fetching or deleting an unknown tag returns 404.

    Parameters
    ----------
    access_token_admin_1
        Access token for admin user 1.
    client
        Test client.
    method
        The HTTP method.
    path
        The endpoint path.
    """

    response = client.request(
        method, path, headers={"Authorization": f"Bearer {access_token_admin_1}"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
