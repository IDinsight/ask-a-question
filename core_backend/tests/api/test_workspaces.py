"""This module contains tests for workspaces."""

from typing import Any

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from core_backend.app.auth.dependencies import (
    WorkspaceTokenNotFoundError,
    get_workspace_by_api_key,
)
from core_backend.app.utils import get_key_hash
from core_backend.app.workspaces.utils import (
    get_workspace_by_workspace_name,
    update_workspace_api_key,
)

from .conftest import TEST_WORKSPACE_API_KEY_1, TEST_WORKSPACE_NAME_2


@pytest.mark.order(-100000)  # Ensure this class always runs last!
class TestWorkspaceKeyManagement:
    """Tests for the PUT /workspace/rotate-key endpoint.

    NB: The tests in this class should always run LAST since API key generation is
    random. Running these tests first might cause unintended consequences for other
    tests/fixtures that require a known API key.
    """

    async def test_get_workspace_by_api_key(
        self, api_key_workspace_2: str, asession: AsyncSession
    ) -> None:
        """Test getting a workspace by the workspace API key.

        Parameters
        ----------
        api_key_workspace_2
            API key for workspace 2.
        asession
            The SQLAlchemy async session to use for all database connections.
        """

        retrieved_workspace_db = await get_workspace_by_api_key(
            asession=asession, token=api_key_workspace_2
        )
        assert retrieved_workspace_db.workspace_name == TEST_WORKSPACE_NAME_2

    @pytest.mark.order(after="test_get_workspace_by_api_key")
    def test_get_new_api_key_for_workspace_1(
        self, access_token_admin_1: str, client: TestClient
    ) -> None:
        """Test getting a new API key for workspace 1.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin 1 in workspace 1.
        client
            Test client.
        """

        response = client.put(
            "/workspace/rotate-key",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )

        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response["new_api_key"] != TEST_WORKSPACE_API_KEY_1

    @pytest.mark.order(after="test_get_new_api_key_for_workspace_1")
    def test_get_new_api_key_query_with_old_key(
        self, access_token_admin_1: str, client: TestClient
    ) -> None:
        """Test getting a new API key for workspace 1 and querying with the old key.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin 1 in workspace 1.
        client
            Test client.
        """

        # Get new API key (first time).
        rotate_key_response = client.put(
            "/workspace/rotate-key",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )
        assert rotate_key_response.status_code == status.HTTP_200_OK

        json_response = rotate_key_response.json()
        first_api_key = json_response["new_api_key"]

        # Make a QA call with this first key.
        search_response = client.post(
            "/search",
            headers={"Authorization": f"Bearer {first_api_key}"},
            json={"query_text": "Tell me about a good sport to play"},
        )
        assert search_response.status_code == status.HTTP_200_OK

        # Get new API key (second time).
        rotate_key_response = client.put(
            "/workspace/rotate-key",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )
        assert rotate_key_response.status_code == status.HTTP_200_OK

        json_response = rotate_key_response.json()
        second_api_key = json_response["new_api_key"]

        # Make a QA call with the second key.
        search_response = client.post(
            "/search",
            headers={"Authorization": f"Bearer {second_api_key}"},
            json={"query_text": "Tell me about a good sport to play"},
        )
        assert search_response.status_code == status.HTTP_200_OK

        # Make a QA call with the first key again.
        search_response = client.post(
            "/search",
            headers={"Authorization": f"Bearer {first_api_key}"},
            json={"query_text": "Tell me about a good sport to play"},
        )
        assert search_response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_workspace_by_api_key_no_workspace(
        self, asession: AsyncSession
    ) -> None:
        """Test getting a workspace by the workspace API key when the workspace does
        not exist.

        Parameters
        ----------
        asession
            The SQLAlchemy async session to use for all database connections.
        """

        with pytest.raises(WorkspaceTokenNotFoundError):
            await get_workspace_by_api_key(asession=asession, token="nonexistent")

    async def test_update_workspace_api_key(
        self, admin_user_1_in_workspace_1: dict[str, Any], asession: AsyncSession
    ) -> None:
        """Test updating the API key for a workspace.

        Parameters
        ----------
        admin_user_1_in_workspace_1
            The admin user in workspace 1.
        asession
            The SQLAlchemy async session to use for all database connections.
        """

        workspace_name = admin_user_1_in_workspace_1["workspace_name"]
        workspace_db = await get_workspace_by_workspace_name(
            asession=asession, workspace_name=workspace_name
        )
        updated_workspace_db = await update_workspace_api_key(
            asession=asession,
            new_api_key="new_key",  # pragma: allowlist secret
            workspace_db=workspace_db,
        )
        assert updated_workspace_db.hashed_api_key is not None
        assert updated_workspace_db.hashed_api_key == get_key_hash(key="new_key")
