"""HTTP tests for the question-answer endpoints in `app.question_answer.router`.

Tests that need real search results go through the whole stack (API key, quota,
database). Tests that only check how a handler turns a service result into an HTTP
response use `stub_auth` and replace the service function imported by the router,
so they need neither the database nor any API quota.
"""

import os
from io import BytesIO
from types import SimpleNamespace
from typing import Any, Generator
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.auth.router import authenticate_key, rate_limiter
from app.core.config import N_TOP_CONTENT
from app.core.utils import LLMCallException
from app.main import app
from app.question_answer.schemas import (
    ErrorType,
    QueryAudioResponse,
    QueryBase,
    QueryResponse,
    QueryResponseError,
)
from app.question_answer.service import (
    INTERNAL_SERVER_ERROR_MESSAGE,
    LLM_CALL_ERROR_MESSAGE,
    TURNIO_ACK_MESSAGE,
)
from tests.conftest import (
    TEST_ADMIN_USERNAME_1,
    TEST_ADMIN_USERNAME_2,
)


class TestApiCallQuota:
    """Test API call quota for different user types."""

    @pytest.mark.parametrize(
        "temp_workspace_api_key_and_api_quota",
        [
            {
                "api_daily_quota": 0,
                "username": "temp_user_llm_api_limit_0",
                "workspace_name": "temp_workspace_llm_api_limit_0",
            },
            {
                "api_daily_quota": 2,
                "username": "temp_user_llm_api_limit_2",
                "workspace_name": "temp_workspace_llm_api_limit_2",
            },
            {
                "api_daily_quota": 5,
                "username": "temp_user_llm_api_limit_5",
                "workspace_name": "temp_workspace_llm_api_limit_5",
            },
        ],
        indirect=True,
    )
    async def test_api_call_llm_quota_integer(
        self, client: TestClient, temp_workspace_api_key_and_api_quota: tuple[str, int]
    ) -> None:
        """Test API call quota for LLM API.

        Parameters
        ----------
        client
            FastAPI test client.
        temp_workspace_api_key_and_api_quota
            Tuple containing temporary workspace API key and daily quota.
        """

        temp_api_key, api_daily_limit = temp_workspace_api_key_and_api_quota

        for _ in range(api_daily_limit):
            response = client.post(
                "/search",
                headers={"Authorization": f"Bearer {temp_api_key}"},
                json={"generate_llm_response": False, "query_text": "Test question"},
            )
            assert response.status_code == status.HTTP_200_OK

        response = client.post(
            "/search",
            headers={"Authorization": f"Bearer {temp_api_key}"},
            json={"generate_llm_response": False, "query_text": "Test question"},
        )
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.parametrize(
        "temp_workspace_api_key_and_api_quota",
        [
            {
                "api_daily_quota": 0,
                "username": "temp_user_emb_api_limit_0",
                "workspace_name": "temp_workspace_emb_api_limit_0",
            },
            {
                "api_daily_quota": 2,
                "username": "temp_user_emb_api_limit_2",
                "workspace_name": "temp_workspace_emb_api_limit_2",
            },
            {
                "api_daily_quota": 5,
                "username": "temp_user_emb_api_limit_5",
                "workspace_name": "temp_workspace_emb_api_limit_5",
            },
        ],
        indirect=True,
    )
    async def test_api_call_embeddings_quota_integer(
        self, client: TestClient, temp_workspace_api_key_and_api_quota: tuple[str, int]
    ) -> None:
        """Test API call quota for embeddings API.

        Parameters
        ----------
        client
            FastAPI test client.
        temp_workspace_api_key_and_api_quota
            Tuple containing temporary workspace API key and daily quota.
        """

        temp_api_key, api_daily_limit = temp_workspace_api_key_and_api_quota

        for _ in range(api_daily_limit):
            response = client.post(
                "/search",
                json={"generate_llm_response": False, "query_text": "Test question"},
                headers={"Authorization": f"Bearer {temp_api_key}"},
            )
            assert response.status_code == status.HTTP_200_OK

        response = client.post(
            "/search",
            json={"generate_llm_response": False, "query_text": "Test question"},
            headers={"Authorization": f"Bearer {temp_api_key}"},
        )
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.parametrize(
        "temp_workspace_api_key_and_api_quota",
        [
            {
                "api_daily_quota": 0,
                "username": "temp_user_mix_api_limit_0",
                "workspace_name": "temp_workspace_mix_api_limit_0",
            },
            {
                "api_daily_quota": 2,
                "username": "temp_user_mix_api_limit_2",
                "workspace_name": "temp_workspace_mix_api_limit_2",
            },
            {
                "api_daily_quota": 5,
                "username": "temp_user_mix_api_limit_5",
                "workspace_name": "temp_workspace_mix_api_limit_5",
            },
        ],
        indirect=True,
    )
    async def test_api_call_mix_quota_integer(
        self, client: TestClient, temp_workspace_api_key_and_api_quota: tuple[str, int]
    ) -> None:
        """Test API call quota for mixed API.

        Parameters
        ----------
        client
            FastAPI test client.
        temp_workspace_api_key_and_api_quota
            Tuple containing temporary workspace API key and daily quota.
        """

        temp_api_key, api_daily_limit = temp_workspace_api_key_and_api_quota

        for i in range(api_daily_limit):
            if i // 2 == 0:
                response = client.post(
                    "/search",
                    headers={"Authorization": f"Bearer {temp_api_key}"},
                    json={"generate_llm_response": True, "query_text": "Test question"},
                )
            else:
                response = client.post(
                    "/search",
                    headers={"Authorization": f"Bearer {temp_api_key}"},
                    json={
                        "generate_llm_response": False,
                        "query_text": "Test question",
                    },
                )
            assert response.status_code == status.HTTP_200_OK

        if api_daily_limit % 2 == 0:
            response = client.post(
                "/search",
                headers={"Authorization": f"Bearer {temp_api_key}"},
                json={"generate_llm_response": True, "query_text": "Test question"},
            )
        else:
            response = client.post(
                "/search",
                headers={"Authorization": f"Bearer {temp_api_key}"},
                json={"generate_llm_response": False, "query_text": "Test question"},
            )
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.parametrize(
        "temp_workspace_api_key_and_api_quota",
        [
            {
                "api_daily_quota": None,
                "username": "temp_user_api_unlimited",
                "workspace_name": "temp_workspace_api_unlimited",
            }
        ],
        indirect=True,
    )
    async def test_api_quota_unlimited(
        self, client: TestClient, temp_workspace_api_key_and_api_quota: tuple[str, int]
    ) -> None:
        """Test API call quota for unlimited API.

        Parameters
        ----------
        client
            FastAPI test client.
        temp_workspace_api_key_and_api_quota
            Tuple containing temporary workspace API key and daily quota.
        """

        temp_api_key, _ = temp_workspace_api_key_and_api_quota

        response = client.post(
            "/search",
            headers={"Authorization": f"Bearer {temp_api_key}"},
            json={
                "generate_llm_response": False,
                "query_text": "Tell me about a good sport to play",
            },
        )
        assert response.status_code == status.HTTP_200_OK


class TestEmbeddingsSearch:
    """Tests for embeddings search."""

    @pytest.mark.parametrize(
        "token, expected_status_code",
        [("api_key_incorrect", 401), ("api_key_correct", 200)],
    )
    def test_search_results(
        self,
        token: str,
        expected_status_code: int,
        api_key_workspace_1: str,
        client: TestClient,
        faq_contents_in_workspace_1: list[int],
    ) -> None:
        """Create a search request and check the response.

        Parameters
        ----------
        token
            API key token.
        expected_status_code
            Expected status code.
        api_key_workspace_1
            API key for workspace 1.
        client
            FastAPI test client.
        faq_contents_in_workspace_1
            FAQ contents in workspace 1.
        """

        request_token = api_key_workspace_1 if token == "api_key_correct" else token
        response = client.post(
            "/search",
            headers={"Authorization": f"Bearer {request_token}"},
            json={
                "generate_llm_response": False,
                "query_text": "Tell me about a good sport to play",
            },
        )
        assert response.status_code == expected_status_code

        if expected_status_code == status.HTTP_200_OK:
            json_search_results = response.json()["search_results"]
            assert len(json_search_results.keys()) == int(N_TOP_CONTENT)

    @pytest.fixture
    def question_response(
        self, client: TestClient, api_key_workspace_1: str
    ) -> QueryResponse:
        """Create a search request and return the response.

        Parameters
        ----------
        client
            FastAPI test client.
        api_key_workspace_1
            API key for workspace 1.

        Returns
        -------
        QueryResponse
            The query response object.
        """

        response = client.post(
            "/search",
            headers={"Authorization": f"Bearer {api_key_workspace_1}"},
            json={
                "generate_llm_response": False,
                "query_text": "Tell me about a good sport to play",
            },
        )
        return response.json()

    @pytest.mark.parametrize(
        "outcome, expected_status_code, endpoint",
        [
            ("incorrect", 401, "/response-feedback"),
            ("correct", 200, "/response-feedback"),
            ("incorrect", 401, "/content-feedback"),
            ("correct", 200, "/content-feedback"),
        ],
    )
    def test_response_feedback_correct_token(
        self,
        outcome: str,
        expected_status_code: int,
        endpoint: str,
        api_key_workspace_1: str,
        client: TestClient,
        faq_contents_in_workspace_1: list[int],
        question_response: dict[str, Any],
    ) -> None:
        """Test response feedback with correct token.

        Parameters
        ----------
        outcome
            The expected outcome.
        expected_status_code
            Expected status code.
        endpoint
            API endpoint.
        api_key_workspace_1
            API key for workspace 1.
        client
            FastAPI test client.
        faq_contents_in_workspace_1
            FAQ contents in workspace 1.
        question_response
            The question response.
        """

        query_id = question_response["query_id"]
        feedback_secret_key = question_response["feedback_secret_key"]
        token = api_key_workspace_1 if outcome == "correct" else "api_key_incorrect"
        json_ = {
            "feedback_secret_key": feedback_secret_key,
            "feedback_sentiment": "positive",
            "feedback_text": "This is feedback",
            "query_id": query_id,
        }

        if endpoint == "/content-feedback":
            json_["content_id"] = faq_contents_in_workspace_1[0]

        response = client.post(
            endpoint, headers={"Authorization": f"Bearer {token}"}, json=json_
        )
        assert response.status_code == expected_status_code

    @pytest.mark.parametrize("endpoint", ["/response-feedback", "/content-feedback"])
    def test_response_feedback_incorrect_secret(
        self,
        endpoint: str,
        client: TestClient,
        api_key_workspace_1: str,
        question_response: dict[str, Any],
    ) -> None:
        """Test response feedback with incorrect secret key.

        Parameters
        ----------
        endpoint
            API endpoint.
        client
            FastAPI test client.
        api_key_workspace_1
            API key for workspace 1.
        question_response
            The question response.
        """

        query_id = question_response["query_id"]

        json_ = {
            "feedback_secret_key": "incorrect_key",
            "feedback_text": "This feedback has the wrong secret key",
            "query_id": query_id,
        }

        if endpoint == "/content-feedback":
            json_["content_id"] = 1

        response = client.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key_workspace_1}"},
            json=json_,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("endpoint", ["/response-feedback", "/content-feedback"])
    async def test_response_feedback_incorrect_query_id(
        self,
        endpoint: str,
        client: TestClient,
        api_key_workspace_1: str,
        question_response: dict[str, Any],
    ) -> None:
        """Test response feedback with incorrect query ID.

        Parameters
        ----------
        endpoint
            API endpoint.
        client
            FastAPI test client.
        api_key_workspace_1
            API key for workspace 1.
        question_response
            The question response.
        """

        feedback_secret_key = question_response["feedback_secret_key"]
        json_ = {
            "feedback_secret_key": feedback_secret_key,
            "feedback_text": "This feedback has the wrong query id",
            "query_id": 99999,
        }
        if endpoint == "/content-feedback":
            json_["content_id"] = 1

        response = client.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key_workspace_1}"},
            json=json_,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("endpoint", ["/response-feedback", "/content-feedback"])
    async def test_response_feedback_incorrect_sentiment(
        self,
        endpoint: str,
        client: TestClient,
        api_key_workspace_1: str,
        question_response: dict[str, Any],
    ) -> None:
        """Test response feedback with incorrect sentiment.

        Parameters
        ----------
        endpoint
            API endpoint.
        client
            FastAPI test client.
        api_key_workspace_1
            API key for workspace 1.
        question_response
            The question response.
        """

        feedback_secret_key = question_response["feedback_secret_key"]
        query_id = question_response["query_id"]

        json_ = {
            "feedback_secret_key": feedback_secret_key,
            "feedback_sentiment": "incorrect",
            "feedback_text": "This feedback has the wrong sentiment",
            "query_id": query_id,
        }

        if endpoint == "/content-feedback":
            json_["content_id"] = 1

        response = client.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key_workspace_1}"},
            json=json_,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.parametrize("endpoint", ["/response-feedback", "/content-feedback"])
    async def test_response_feedback_sentiment_only(
        self,
        endpoint: str,
        client: TestClient,
        api_key_workspace_1: str,
        faq_contents_in_workspace_1: list[int],
        question_response: dict[str, Any],
    ) -> None:
        """Test response feedback with sentiment only.

        Parameters
        ----------
        endpoint
            API endpoint.
        client
            FastAPI test client.
        api_key_workspace_1
            API key for workspace 1.
        faq_contents_in_workspace_1
            FAQ contents in workspace 1.
        question_response
            The question response.
        """

        query_id = question_response["query_id"]
        feedback_secret_key = question_response["feedback_secret_key"]

        json_ = {
            "feedback_secret_key": feedback_secret_key,
            "feedback_sentiment": "positive",
            "query_id": query_id,
        }
        if endpoint == "/content-feedback":
            json_["content_id"] = faq_contents_in_workspace_1[0]

        response = client.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key_workspace_1}"},
            json=json_,
        )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize(
        "username, expect_found",
        [(TEST_ADMIN_USERNAME_1, True), (TEST_ADMIN_USERNAME_2, False)],
    )
    def test_admin_2_access_admin_1_content(
        self,
        username: str,
        expect_found: bool,
        api_key_workspace_1: str,
        api_key_workspace_2: str,
        client: TestClient,
        faq_contents_in_workspace_1: list[int],
    ) -> None:
        """Test admin 2 can access admin 1 content.

        Parameters
        ----------
        username
            The user name.
        expect_found
            Specifies whether to expect content to be found.
        api_key_workspace_1
            API key for workspace 1.
        api_key_workspace_2
            API key for workspace 2.
        client
            FastAPI test client.
        faq_contents_in_workspace_1
            FAQ contents in workspace 1.
        """

        token = (
            api_key_workspace_1
            if username == TEST_ADMIN_USERNAME_1
            else api_key_workspace_2
        )

        response = client.post(
            "/search",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "generate_llm_response": False,
                "query_text": "Tell me about camping",
            },
        )
        assert response.status_code == status.HTTP_200_OK

        if response.status_code == status.HTTP_200_OK:
            all_retireved_content_ids = [
                value["id"] for value in response.json()["search_results"].values()
            ]
            if expect_found:
                # Admin user 1 has contents in DB uploaded by the
                # `faq_contents_in_workspace_1` fixture.
                assert len(all_retireved_content_ids) > 0
            else:
                # Admin user 2 should not have any content.
                assert len(all_retireved_content_ids) == 0

    @pytest.mark.parametrize(
        "content_id_valid, response_code", ([True, 200], [False, 400])
    )
    def test_content_feedback_check_content_id(
        self,
        content_id_valid: str,
        response_code: int,
        client: TestClient,
        api_key_workspace_1: str,
        faq_contents_in_workspace_1: list[int],
        question_response: dict[str, Any],
    ) -> None:
        """Test content feedback with correct content ID.

        Parameters
        ----------
        content_id_valid
            Specifies whether the content ID is valid.
        response_code
            Expected response code.
        client
            FastAPI test client.
        api_key_workspace_1
            API key for workspace 1.
        faq_contents_in_workspace_1
            FAQ contents in workspace 1.
        question_response
            The question response.
        """

        query_id = question_response["query_id"]
        feedback_secret_key = question_response["feedback_secret_key"]
        content_id = faq_contents_in_workspace_1[0] if content_id_valid else 99999
        response = client.post(
            "/content-feedback",
            json={
                "content_id": content_id,
                "feedback_secret_key": feedback_secret_key,
                "feedback_sentiment": "positive",
                "feedback_text": "This feedback has the wrong content id",
                "query_id": query_id,
            },
            headers={"Authorization": f"Bearer {api_key_workspace_1}"},
        )

        assert response.status_code == response_code


class TestGenerateResponse:
    """Tests for generating responses."""

    @pytest.mark.parametrize(
        "outcome, expected_status_code", [("incorrect", 401), ("correct", 200)]
    )
    def test_llm_response(
        self,
        outcome: str,
        expected_status_code: int,
        client: TestClient,
        api_key_workspace_1: str,
        faq_contents_in_workspace_1: list[int],
    ) -> None:
        """Test LLM response.

        Parameters
        ----------
        outcome
            Specifies whether the outcome is correct.
        expected_status_code
            Expected status code.
        client
            FastAPI test client.
        api_key_workspace_1
            API key for workspace 1.
        faq_contents_in_workspace_1
            FAQ content in workspace 1.
        """

        token = api_key_workspace_1 if outcome == "correct" else "api_key_incorrect"
        response = client.post(
            "/search",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "generate_llm_response": True,
                "query_text": "Tell me about a good sport to play",
            },
        )
        assert response.status_code == expected_status_code

        if expected_status_code == status.HTTP_200_OK:
            llm_response = response.json()["llm_response"]
            assert len(llm_response) != 0

            search_results = response.json()["search_results"]
            assert len(search_results) != 0

    @pytest.mark.parametrize(
        "username, expect_found",
        [(TEST_ADMIN_USERNAME_1, True), (TEST_ADMIN_USERNAME_2, False)],
    )
    def test_admin_2_access_admin_1_content(
        self,
        username: str,
        expect_found: bool,
        api_key_workspace_1: str,
        api_key_workspace_2: str,
        client: TestClient,
        faq_contents_in_workspace_1: list[int],
    ) -> None:
        """Test admin 2 can access admin 1 content.

        Parameters
        ----------
        username
            The user name.
        expect_found
            Specifies whether to expect content to be found.
        api_key_workspace_1
            API key for workspace 1.
        api_key_workspace_2
            API key for workspace 2.
        client
            FastAPI test client.
        faq_contents_in_workspace_1
            FAQ contents in workspace 1.
        """

        token = (
            api_key_workspace_1
            if username == TEST_ADMIN_USERNAME_1
            else api_key_workspace_2
        )
        response = client.post(
            "/search",
            headers={"Authorization": f"Bearer {token}"},
            json={"generate_llm_response": True, "query_text": "Tell me about camping"},
        )
        assert response.status_code == status.HTTP_200_OK

        all_retrieved_content_ids = [
            value["id"] for value in response.json()["search_results"].values()
        ]
        if expect_found:
            # Admin user 1 has contents in DB uploaded by the
            # `faq_contents_in_workspace_1` fixture.
            assert len(all_retrieved_content_ids) > 0
        else:
            # Admin user 2 should not have any content.
            assert len(all_retrieved_content_ids) == 0


class TestSTTResponse:
    """Tests for speech-to-text response."""

    @pytest.mark.parametrize(
        "is_authorized, expected_status_code, mock_response",
        [
            (True, status.HTTP_200_OK, {"text": "Paris"}),
            (False, status.HTTP_401_UNAUTHORIZED, {"error": "Unauthorized"}),
            (True, status.HTTP_400_BAD_REQUEST, {"text": "Paris"}),
            (True, status.HTTP_500_INTERNAL_SERVER_ERROR, {}),
        ],
    )
    def test_voice_search(  # pylint: disable=R1260
        self,
        is_authorized: bool,
        expected_status_code: int,
        mock_response: dict,
        api_key_workspace_1: str,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test voice search.

        Parameters
        ----------
        is_authorized
            Specifies whether the user is authorized.
        expected_status_code
            Expected status code.
        mock_response
            Mock response.
        api_key_workspace_1
            API key for workspace 1.
        client
            FastAPI test client.
        monkeypatch
            Pytest monkeypatch.
        """

        token = api_key_workspace_1 if is_authorized else "api_key_incorrect"

        async def dummy_download_file_from_url(
            file_url: str,  # pylint: disable=W0613
        ) -> tuple[BytesIO, str, str]:
            """Return dummy audio content.

            Parameters
            ----------
            file_url
                File URL.

            Returns
            -------
            tuple[BytesIO, str, str]
                Tuple containing file content, content type, and extension.
            """

            return BytesIO(b"fake audio content"), "audio/mpeg", "mp3"

        async def dummy_post_to_speech_stt(  # pylint: disable=W0613
            file_path: str, endpoint_url: str
        ) -> dict:
            """Return dummy STT response.

            Parameters
            ----------
            file_path
                File path.
            endpoint_url
                Endpoint URL.

            Returns
            -------
            dict
                STT response.

            Raises
            ------
            ValueError
                If the status code is 500.
            """

            if expected_status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
                raise ValueError("Error from CUSTOM_STT_ENDPOINT")
            return mock_response

        async def dummy_post_to_speech_tts(  # pylint: disable=W0613
            text: str, endpoint_url: str, language: str
        ) -> BytesIO:
            """Return dummy audio content.

            Parameters
            ----------
            text
                Text.
            endpoint_url
                Endpoint URL.
            language
                Language.

            Returns
            -------
            BytesIO
                Audio content.

            Raises
            ------
            ValueError
                If the status code is 400.
            """

            if expected_status_code == status.HTTP_400_BAD_REQUEST:
                raise ValueError("Error from CUSTOM_TTS_ENDPOINT")
            return BytesIO(b"fake audio content")

        async def async_fake_transcribe_audio(  # pylint: disable=W0613
            *args: Any, **kwargs: Any
        ) -> str:
            """Return transcribed text.

            Parameters
            ----------
            args
                Additional positional arguments.
            kwargs
                Additional keyword arguments.

            Returns
            -------
            str
                Transcribed text.

            Raises
            ------
            ValueError
                If the status code is 500.
            """

            if expected_status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
                raise ValueError("Error from External STT service")
            return "transcribed text"

        async def async_fake_generate_tts_on_gcs(  # pylint: disable=W0613
            *args: Any, **kwargs: Any
        ) -> BytesIO:
            """Return dummy audio content.

            Parameters
            ----------
            args
                Additional positional arguments.
            kwargs
                Additional keyword arguments.

            Returns
            -------
            BytesIO
                Audio content.

            Raises
            ------
            ValueError
                If the status code is 400.
            """

            if expected_status_code == status.HTTP_400_BAD_REQUEST:
                raise ValueError("Error from External TTS service")
            return BytesIO(b"fake audio content")

        monkeypatch.setattr(
            "app.question_answer.service.transcribe_audio",
            async_fake_transcribe_audio,
        )
        monkeypatch.setattr(
            "app.question_answer.service.synthesize_speech",
            async_fake_generate_tts_on_gcs,
        )
        monkeypatch.setattr(
            "app.question_answer.service.post_to_speech_stt",
            dummy_post_to_speech_stt,
        )
        monkeypatch.setattr(
            "app.question_answer.service.download_file_from_url",
            dummy_download_file_from_url,
        )
        monkeypatch.setattr(
            "app.question_answer.service.post_to_internal_tts",
            dummy_post_to_speech_tts,
        )

        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)

        file_url = "http://example.com/test.mp3"

        response = client.post(
            "/voice-search",
            headers={"Authorization": f"Bearer {token}"},
            params={"file_url": file_url},
        )

        assert response.status_code == expected_status_code

        if expected_status_code == status.HTTP_200_OK:
            json_response = response.json()
            assert "llm_response" in json_response
            assert "tts_filepath" in json_response

        elif expected_status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
            json_response = response.json()
            assert "error" in json_response

        elif expected_status_code == status.HTTP_400_BAD_REQUEST:
            json_response = response.json()
            assert "error_message" in json_response

        if os.path.exists(temp_dir):
            for file_name in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(temp_dir)


# =====================================================================================
# Handler branches (service functions replaced, auth and quota stubbed)
# =====================================================================================

ROUTER = "app.question_answer.router"
# Auth is stubbed in these tests, so the key is never checked.
STUB_HEADERS = {"Authorization": "Bearer [API_KEY]"}  # pragma: allowlist secret
STUB_WORKSPACE = SimpleNamespace(doc_language="ENGLISH", workspace_id=1)


@pytest.fixture
def stub_auth() -> Generator[SimpleNamespace, None, None]:
    """Skip the API-key lookup and the daily quota for the duration of a test.

    Yields
    ------
    SimpleNamespace
        The workspace object handed to the endpoints.
    """

    app.dependency_overrides[authenticate_key] = lambda: STUB_WORKSPACE
    app.dependency_overrides[rate_limiter] = lambda: None
    yield STUB_WORKSPACE
    # Only remove our own overrides; other tests may have set theirs.
    app.dependency_overrides.pop(authenticate_key, None)
    app.dependency_overrides.pop(rate_limiter, None)


def _ok_response() -> QueryResponse:
    """Build a successful pipeline result.

    Returns
    -------
    QueryResponse
        The response.
    """

    return QueryResponse(
        debug_info={},
        feedback_secret_key="secret",
        llm_response="Drink water.",
        query_id=1,
        search_results={},
        session_id=7,
    )


def _audio_response() -> QueryAudioResponse:
    """Build a successful voice pipeline result.

    Returns
    -------
    QueryAudioResponse
        The response.
    """

    return QueryAudioResponse(
        **_ok_response().model_dump(), tts_filepath="https://example.com/a.wav"
    )


def _error_response() -> QueryResponseError:
    """Build a guardrail-failure pipeline result.

    Returns
    -------
    QueryResponseError
        The response.
    """

    return QueryResponseError(
        **_ok_response().model_dump(),
        error_message="Unsafe query.",
        error_type=ErrorType.QUERY_UNSAFE,
    )


@pytest.mark.parametrize(
    "endpoint, service_name",
    [("/search", "search_and_respond"), ("/chat", "process_chat")],
)
@pytest.mark.parametrize(
    "outcome, expected_status, expected_body",
    [
        (_ok_response(), status.HTTP_200_OK, {"llm_response": "Drink water."}),
        (
            _error_response(),
            status.HTTP_400_BAD_REQUEST,
            {"error_type": "query_unsafe", "error_message": "Unsafe query."},
        ),
        (
            LLMCallException("boom"),
            status.HTTP_502_BAD_GATEWAY,
            {"error_message": LLM_CALL_ERROR_MESSAGE},
        ),
        (
            None,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {"error_message": INTERNAL_SERVER_ERROR_MESSAGE},
        ),
    ],
    ids=["ok", "guardrail", "llm-error", "unexpected"],
)
def test_search_and_chat_status_codes(
    endpoint: str,
    service_name: str,
    outcome: Any,
    expected_status: int,
    expected_body: dict[str, Any],
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    stub_auth: SimpleNamespace,
) -> None:
    """Each pipeline result maps to the documented status code and body.

    Parameters
    ----------
    endpoint
        The endpoint under test.
    service_name
        The service function the endpoint calls.
    outcome
        What the service returns (or raises).
    expected_status
        The expected HTTP status.
    expected_body
        Fields expected in the JSON body.
    client
        FastAPI test client.
    monkeypatch
        Pytest monkeypatch.
    stub_auth
        Stubbed workspace.
    """

    # A one-item `side_effect` either returns the item or raises it.
    monkeypatch.setattr(f"{ROUTER}.{service_name}", AsyncMock(side_effect=[outcome]))

    response = client.post(
        endpoint, headers=STUB_HEADERS, json={"query_text": "How much water?"}
    )

    assert response.status_code == expected_status
    assert expected_body.items() <= response.json().items()


def test_chat_passes_session_and_reset_flag(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, stub_auth: SimpleNamespace
) -> None:
    """A chat without a session ID gets one, and the reset flag and app clients are
    passed to the service.

    Parameters
    ----------
    client
        FastAPI test client.
    monkeypatch
        Pytest monkeypatch.
    stub_auth
        Stubbed workspace.
    """

    mock_process_chat = AsyncMock(return_value=_ok_response())
    monkeypatch.setattr(f"{ROUTER}.process_chat", mock_process_chat)
    monkeypatch.setattr("app.question_answer.service.get_random_int32", lambda: 424242)

    response = client.post(
        "/chat",
        headers=STUB_HEADERS,
        json={"query_text": "How much water?"},
        params={"reset_chat_history": True},
    )

    assert response.status_code == status.HTTP_200_OK
    kwargs = mock_process_chat.call_args.kwargs
    assert kwargs["reset_chat_history"] is True
    assert kwargs["user_query"].session_id == 424242
    assert kwargs["redis_client"] is app.state.redis
    assert kwargs["crossencoder"] is getattr(app.state, "crossencoder", None)
    assert kwargs["workspace_db"] is stub_auth


def test_chat_turnio_returns_ack_and_schedules_task(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, stub_auth: SimpleNamespace
) -> None:
    """Turn.io chats get an immediate acknowledgement; the real work runs as a
    background task that receives the app's HTTP and Redis clients.

    Parameters
    ----------
    client
        FastAPI test client.
    monkeypatch
        Pytest monkeypatch.
    stub_auth
        Stubbed workspace.
    """

    scheduled: list[dict[str, Any]] = []

    async def fake_process_turnio_chat(**kwargs: Any) -> None:
        """Record the background task call.

        Parameters
        ----------
        kwargs
            The keyword arguments passed by the router.
        """

        scheduled.append(kwargs)

    mock_process_chat = AsyncMock()
    monkeypatch.setattr(f"{ROUTER}.process_turnio_chat", fake_process_turnio_chat)
    monkeypatch.setattr(f"{ROUTER}.process_chat", mock_process_chat)
    monkeypatch.setattr("app.question_answer.service.get_random_int32", lambda: 424242)

    # `TestClient` runs background tasks before `post` returns.
    response = client.post(
        "/chat",
        headers=STUB_HEADERS,
        json={
            "query_text": "hello",
            "turnio_api_key": "[TURNIO_API_KEY]",  # pragma: allowlist secret
            "wa_id": "whatsapp:+1234567890",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["llm_response"] == TURNIO_ACK_MESSAGE
    assert body["session_id"] == 424242
    assert (body["query_id"], body["feedback_secret_key"], body["search_results"]) == (
        None,
        None,
        None,
    )
    mock_process_chat.assert_not_called()
    assert len(scheduled) == 1
    task_kwargs = scheduled[0]
    assert task_kwargs["httpx_client"] is app.state.httpx_client
    assert task_kwargs["redis_client"] is app.state.redis
    assert task_kwargs["reset_chat_history"] is False
    assert isinstance(task_kwargs["user_query"], QueryBase)
    assert task_kwargs["user_query"].session_id == 424242
    assert task_kwargs["workspace_db"] is stub_auth


@pytest.mark.parametrize(
    "endpoint, service_name",
    [
        ("/voice-search", "voice_search_and_respond"),
        ("/voice-chat", "voice_chat_and_respond"),
    ],
)
@pytest.mark.parametrize(
    "outcome, expected_status, expected_body",
    [
        (
            _audio_response(),
            status.HTTP_200_OK,
            {"tts_filepath": "https://example.com/a.wav"},
        ),
        (
            _error_response(),
            status.HTTP_400_BAD_REQUEST,
            {"error_type": "query_unsafe"},
        ),
        # A plain (non-audio) response is unexpected for the voice endpoints.
        (
            _ok_response(),
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {"error": "Internal server error"},
        ),
        (
            ValueError("bad audio"),
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {"error": "Value error: bad audio"},
        ),
        (
            RuntimeError("boom"),
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {"error": "Internal server error"},
        ),
    ],
    ids=["ok", "guardrail", "not-audio", "value-error", "other-error"],
)
def test_voice_status_codes(
    endpoint: str,
    service_name: str,
    outcome: Any,
    expected_status: int,
    expected_body: dict[str, Any],
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    stub_auth: SimpleNamespace,
) -> None:
    """Each voice pipeline result maps to the documented status code and body.

    Parameters
    ----------
    endpoint
        The endpoint under test.
    service_name
        The service function the endpoint calls.
    outcome
        What the service returns (or raises).
    expected_status
        The expected HTTP status.
    expected_body
        Fields expected in the JSON body.
    client
        FastAPI test client.
    monkeypatch
        Pytest monkeypatch.
    stub_auth
        Stubbed workspace.
    """

    monkeypatch.setattr(f"{ROUTER}.{service_name}", AsyncMock(side_effect=[outcome]))

    response = client.post(
        endpoint, headers=STUB_HEADERS, params={"file_url": "http://x/a.mp3"}
    )

    assert response.status_code == expected_status
    assert expected_body.items() <= response.json().items()


@pytest.mark.parametrize(
    "endpoint, service_name, expected_status, expected_body",
    [
        (
            "/voice-chat",
            "voice_chat_and_respond",
            status.HTTP_502_BAD_GATEWAY,
            {"error_message": LLM_CALL_ERROR_MESSAGE},
        ),
        # Voice search reports LLM failures as a generic 500 (documented behaviour).
        (
            "/voice-search",
            "voice_search_and_respond",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {"error": "Internal server error"},
        ),
    ],
)
def test_voice_llm_call_error(
    endpoint: str,
    service_name: str,
    expected_status: int,
    expected_body: dict[str, Any],
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    stub_auth: SimpleNamespace,
) -> None:
    """LLM call failures are a 502 for voice chat but a 500 for voice search.

    Parameters
    ----------
    endpoint
        The endpoint under test.
    service_name
        The service function the endpoint calls.
    expected_status
        The expected HTTP status.
    expected_body
        The expected JSON body.
    client
        FastAPI test client.
    monkeypatch
        Pytest monkeypatch.
    stub_auth
        Stubbed workspace.
    """

    monkeypatch.setattr(
        f"{ROUTER}.{service_name}", AsyncMock(side_effect=LLMCallException("boom"))
    )

    response = client.post(
        endpoint, headers=STUB_HEADERS, params={"file_url": "http://x/a.mp3"}
    )

    assert response.status_code == expected_status
    assert response.json() == expected_body


def test_voice_chat_passes_session_and_reset_flag(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, stub_auth: SimpleNamespace
) -> None:
    """Voice chat forwards the session ID, reset flag and Redis client.

    Parameters
    ----------
    client
        FastAPI test client.
    monkeypatch
        Pytest monkeypatch.
    stub_auth
        Stubbed workspace.
    """

    mock_voice_chat = AsyncMock(return_value=_audio_response())
    monkeypatch.setattr(f"{ROUTER}.voice_chat_and_respond", mock_voice_chat)

    response = client.post(
        "/voice-chat",
        headers=STUB_HEADERS,
        params={
            "file_url": "http://x/a.mp3",
            "session_id": 9,
            "reset_chat_history": True,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    kwargs = mock_voice_chat.call_args.kwargs
    assert (kwargs["file_url"], kwargs["session_id"]) == ("http://x/a.mp3", 9)
    assert kwargs["reset_chat_history"] is True
    assert kwargs["redis_client"] is app.state.redis
    assert kwargs["workspace_db"] is stub_auth


@pytest.mark.parametrize(
    "endpoint, request_kwargs",
    [
        ("/chat", {"json": {"query_text": "hi"}}),
        ("/search", {"json": {"query_text": "hi"}}),
        ("/voice-search", {"params": {"file_url": "http://x/a.mp3"}}),
        ("/voice-chat", {"params": {"file_url": "http://x/a.mp3"}}),
        ("/response-feedback", {"json": {}}),
        ("/content-feedback", {"json": {}}),
    ],
)
def test_invalid_api_key_is_rejected(
    endpoint: str, request_kwargs: dict[str, Any], client: TestClient
) -> None:
    """Every question-answer endpoint requires a valid workspace API key.

    Parameters
    ----------
    endpoint
        The endpoint under test.
    request_kwargs
        The request body or query parameters.
    client
        FastAPI test client.
    """

    response = client.post(
        endpoint, headers={"Authorization": "Bearer not-a-real-key"}, **request_kwargs
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    "endpoint, request_kwargs, bad_field",
    [
        ("/chat", {"json": {}}, "query_text"),
        ("/search", {"json": {"query_text": "hi", "session_id": "abc"}}, "session_id"),
        ("/voice-search", {}, "file_url"),
        (
            "/voice-chat",
            {"params": {"file_url": "http://x/a.mp3", "session_id": "abc"}},
            "session_id",
        ),
        ("/response-feedback", {"json": {"query_id": 1}}, "feedback_secret_key"),
        (
            "/content-feedback",
            {"json": {"feedback_secret_key": "k", "query_id": 1}},
            "content_id",
        ),
    ],
)
def test_invalid_payload_is_rejected(
    endpoint: str,
    request_kwargs: dict[str, Any],
    bad_field: str,
    client: TestClient,
    stub_auth: SimpleNamespace,
) -> None:
    """Missing or mistyped fields are rejected with a 422 naming the field.

    Parameters
    ----------
    endpoint
        The endpoint under test.
    request_kwargs
        The request body or query parameters.
    bad_field
        The field the validation error should point at.
    client
        FastAPI test client.
    stub_auth
        Stubbed workspace.
    """

    response = client.post(endpoint, headers=STUB_HEADERS, **request_kwargs)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert bad_field in [error["loc"][-1] for error in response.json()["detail"]]
