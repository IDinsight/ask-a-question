"""This module contains tests for the question-answer API endpoints."""

import os
import time
from functools import partial
from io import BytesIO
from typing import Any

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from core_backend.app.llm_call.llm_prompts import (
    AlignmentScore,
    IdentifiedLanguage,
)
from core_backend.app.llm_call.process_input import (
    _classify_safety,
    _identify_language,
    _translate_question,
)
from core_backend.app.llm_call.process_output import _check_align_score
from core_backend.app.question_answer.config import N_TOP_CONTENT
from core_backend.app.question_answer.schemas import (
    ErrorType,
    QueryRefined,
    QueryResponse,
    QueryResponseError,
    QuerySearchResult,
)
from core_backend.app.question_answer.utils import (
    get_context_string_from_search_results,
)
from core_backend.tests.api.conftest import (
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
        access_token_admin_1: str,
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
        access_token_admin_1
            Admin access token in workspace 1.
        api_key_workspace_1
            API key for workspace 1.
        client
            FastAPI test client.
        faq_contents_in_workspace_1
            FAQ contents in workspace 1.
        """

        while True:
            response = client.get(
                "/content", headers={"Authorization": f"Bearer {access_token_admin_1}"}
            )
            time.sleep(2)
            if len(response.json()) == 9:
                break

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
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

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
        access_token_admin_1: str,
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
        access_token_admin_1
            Admin access token in workspace 1.
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

        while True:
            response = client.get(
                "/content", headers={"Authorization": f"Bearer {access_token_admin_1}"}
            )
            time.sleep(2)
            if len(response.json()) == 9:
                break

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
            "core_backend.app.question_answer.routers.transcribe_audio",
            async_fake_transcribe_audio,
        )
        monkeypatch.setattr(
            "core_backend.app.llm_call.process_output.synthesize_speech",
            async_fake_generate_tts_on_gcs,
        )
        monkeypatch.setattr(
            "core_backend.app.question_answer.routers.post_to_speech_stt",
            dummy_post_to_speech_stt,
        )
        monkeypatch.setattr(
            "core_backend.app.question_answer.routers.download_file_from_url",
            dummy_download_file_from_url,
        )
        monkeypatch.setattr(
            "core_backend.app.llm_call.process_output.post_to_internal_tts",
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


class TestErrorResponses:
    """Tests for error responses."""

    SUPPORTED_LANGUAGE = IdentifiedLanguage.get_supported_languages()[-1]

    @pytest.fixture
    def user_query_response(self) -> QueryResponse:
        """Create a query response.

        Returns
        -------
        QueryResponse
            The query response object.
        """

        return QueryResponse(
            debug_info={},
            feedback_secret_key="abc123",
            llm_response=None,
            query_id=124,
            search_results={},
            session_id=None,
        )

    @pytest.fixture
    def user_query_refined(self, request: pytest.FixtureRequest) -> QueryRefined:
        """Create a query refined object.

        Parameters
        ----------
        request
            Pytest request object.

        Returns
        -------
        QueryRefined
            The query refined object.
        """

        language = request.param if hasattr(request, "param") else None
        return QueryRefined(
            generate_llm_response=False,
            generate_tts=False,
            original_language=language,
            query_text="This is a basic query",
            query_text_original="This is a query original",
            workspace_id=124,
        )

    @pytest.mark.parametrize(
        "identified_lang_str,identified_script_str,should_error,expected_error_type",
        [
            ("ENGLISH", "Latin", False, None),
            ("HINDI", "Devanagari", False, None),
            ("UNINTELLIGIBLE", "Latin", True, ErrorType.UNINTELLIGIBLE_INPUT),
            ("UNINTELLIGIBLE", "Unknown", True, ErrorType.UNSUPPORTED_SCRIPT),
            ("GIBBERISH", "Unknwon", True, ErrorType.UNSUPPORTED_SCRIPT),
            ("GIBBERISH", "Latin", True, ErrorType.UNSUPPORTED_LANGUAGE),
            ("UNSUPPORTED", "Latin", True, ErrorType.UNSUPPORTED_LANGUAGE),
            ("SOME_UNSUPPORTED_LANG", "Unknown", True, ErrorType.UNSUPPORTED_LANGUAGE),
            ("don't kow", "Latin", True, ErrorType.UNSUPPORTED_LANGUAGE),
        ],
    )
    async def test_language_identify_error(
        self,
        identified_lang_str: str,
        identified_script_str: str,
        should_error: bool,
        expected_error_type: ErrorType,
        monkeypatch: pytest.MonkeyPatch,
        user_query_response: QueryResponse,
    ) -> None:
        """Test language identification errors.

        Parameters
        ----------
        identified_lang_str
            Identified language string.
        should_error
            Specifies whether an error is expected.
        expected_error_type
            Expected error type.
        monkeypatch
            Pytest monkeypatch.
        user_query_response
            The user query response.
        """

        user_query_refined = QueryRefined(
            generate_llm_response=False,
            generate_tts=False,
            original_language=None,
            original_script=None,
            query_text="This is a basic query",
            query_text_original="This is a query original",
            workspace_id=124,
        )

        async def mock_ask_llm(  # pylint: disable=W0613
            *args: Any, **kwargs: Any
        ) -> str:
            """Return the identified language string.

            Parameters
            ----------
            args
                Additional positional arguments.
            kwargs
                Additional keyword arguments.

            Returns
            -------
            str
                The identified language and script model json string.
            """

            return f"""
            {{"language": "{identified_lang_str}", "script": "{identified_script_str}"}}
            """.strip()

        monkeypatch.setattr(
            "core_backend.app.llm_call.process_input._ask_llm_async", mock_ask_llm
        )

        query, response = await _identify_language(
            query_refined=user_query_refined, response=user_query_response
        )

        if should_error:
            assert isinstance(response, QueryResponseError)
            assert response.error_type == expected_error_type
        else:
            assert isinstance(response, QueryResponse)
            assert query.original_language == getattr(
                IdentifiedLanguage, identified_lang_str
            )

    @pytest.mark.parametrize(
        "user_query_refined,should_error,expected_error_type",
        [("ENGLISH", False, None), (SUPPORTED_LANGUAGE, False, None)],
        indirect=["user_query_refined"],
    )
    async def test_translate_error(
        self,
        user_query_refined: QueryRefined,
        should_error: bool,
        expected_error_type: ErrorType,
        monkeypatch: pytest.MonkeyPatch,
        user_query_response: QueryResponse,
    ) -> None:
        """Test translation errors.

        Parameters
        ----------
        user_query_refined
            The user query refined object.
        should_error
            Specifies whether an error is expected.
        expected_error_type
            Expected error type.
        monkeypatch
            Pytest monkeypatch.
        user_query_response
            The user query response object.
        """

        async def mock_ask_llm(  # pylint: disable=W0613
            *args: Any, **kwargs: Any
        ) -> str:
            """Mock the LLM response.

            Parameters
            ----------
            args
                Additional positional arguments.
            kwargs
                Additional keyword arguments.

            Returns
            -------
            str
                The mocked LLM response.
            """

            return "This is a translated LLM response"

        monkeypatch.setattr(
            "core_backend.app.llm_call.process_input._ask_llm_async", mock_ask_llm
        )
        query, response = await _translate_question(
            query_refined=user_query_refined, response=user_query_response
        )

        if should_error:
            assert isinstance(response, QueryResponseError)
            assert response.error_type == expected_error_type
        else:
            assert isinstance(response, QueryResponse)
            if query.original_language == "ENGLISH":
                assert query.query_text == "This is a basic query"
            else:
                assert query.query_text == "This is a translated LLM response"

    async def test_translate_before_language_id_errors(
        self, monkeypatch: pytest.MonkeyPatch, user_query_response: QueryResponse
    ) -> None:
        """Test translation before language identification errors.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch.
        user_query_response
            The user query response object.
        """

        async def mock_ask_llm(  # pylint: disable=W0613
            *args: Any, **kwargs: Any
        ) -> str:
            """Mock the LLM response.

            Parameters
            ----------
            args
                Additional positional arguments.
            kwargs
                Additional keyword arguments.

            Returns
            -------
            str
                The mocked LLM response.
            """

            return "This is a translated LLM response"

        monkeypatch.setattr(
            "core_backend.app.llm_call.process_input._ask_llm_async", mock_ask_llm
        )

        user_query_refined = QueryRefined(
            generate_llm_response=False,
            generate_tts=False,
            original_language=None,
            original_script=None,
            query_text="This is a basic query",
            query_text_original="This is a query original",
            workspace_id=124,
        )

        with pytest.raises(ValueError):
            _, _ = await _translate_question(
                query_refined=user_query_refined, response=user_query_response
            )

    @pytest.mark.parametrize(
        "classification, should_error",
        [("SAFE", False), ("INAPPROPRIATE_LANGUAGE", True), ("PROMPT_INJECTION", True)],
    )
    async def test_unsafe_query_error(
        self,
        classification: str,
        should_error: bool,
        monkeypatch: pytest.MonkeyPatch,
        user_query_refined: QueryRefined,
        user_query_response: QueryResponse,
    ) -> None:
        """Test unsafe query errors.

        Parameters
        ----------
        classification
            The classification of the query.
        should_error
            Specifies whether an error is expected.
        monkeypatch
            Pytest monkeypatch.
        user_query_refined
            The user query refined object.
        user_query_response
            The user query response object.
        """

        async def mock_ask_llm(  # pylint: disable=W0613
            llm_response: str, *args: Any, **kwargs: Any
        ) -> str:
            """Mock the LLM response.

            Parameters
            ----------
            llm_response
                The LLM response.
            args
                Additional positional arguments.
            kwargs
                Additional keyword arguments.

            Returns
            -------
            str
                The mocked LLM response.
            """

            return llm_response

        monkeypatch.setattr(
            "core_backend.app.llm_call.process_input._ask_llm_async",
            partial(mock_ask_llm, classification),
        )
        query, response = await _classify_safety(
            query_refined=user_query_refined, response=user_query_response
        )

        if should_error:
            assert isinstance(response, QueryResponseError)
            assert response.error_type == ErrorType.QUERY_UNSAFE
        else:
            assert isinstance(response, QueryResponse)
            assert query.query_text == "This is a basic query"


class TestAlignScore:
    """Tests for alignment score."""

    @pytest.fixture
    def user_query_response(self) -> QueryResponse:
        """Create a query response.

        Returns
        -------
        QueryResponse
            The query response object
        """

        return QueryResponse(
            debug_info={},
            feedback_secret_key="abc123",
            llm_response="This is a response",
            query_id=124,
            search_results={
                1: QuerySearchResult(
                    distance=0.2, id=1, text="hello world", title="World"
                ),
                2: QuerySearchResult(
                    distance=0.2, id=2, text="goodbye universe", title="Universe"
                ),
            },
            session_id=None,
        )

    async def test_score_less_than_threshold(
        self, monkeypatch: pytest.MonkeyPatch, user_query_response: QueryResponse
    ) -> None:
        """Test alignment score less than threshold.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch.
        user_query_response
            The user query response.
        """

        async def mock_get_align_score(  # pylint: disable=W0613
            *args: Any, **kwargs: Any
        ) -> AlignmentScore:
            """Mock the alignment score.

            Parameters
            ----------
            args
                Additional positional arguments.
            kwargs
                Additional keyword arguments.

            Returns
            -------
            AlignmentScore
                The alignment score.
            """

            return AlignmentScore(reason="test - low score", score=0.2)

        monkeypatch.setattr(
            "core_backend.app.llm_call.process_output._get_llm_align_score",
            mock_get_align_score,
        )
        monkeypatch.setattr(
            "core_backend.app.llm_call.process_output.ALIGN_SCORE_THRESHOLD", 0.7
        )
        update_query_response = await _check_align_score(response=user_query_response)
        assert isinstance(update_query_response, QueryResponse)
        assert update_query_response.debug_info["factual_consistency"]["score"] == 0.2
        assert update_query_response.llm_response is None

    async def test_score_greater_than_threshold(
        self, monkeypatch: pytest.MonkeyPatch, user_query_response: QueryResponse
    ) -> None:
        """Test alignment score greater than threshold.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch.
        user_query_response
            The user query response.
        """

        async def mock_get_align_score(  # pylint: disable=W0613
            *args: Any, **kwargs: Any
        ) -> AlignmentScore:
            """Mock the alignment score.

            Parameters
            ----------
            args
                Additional positional arguments.
            kwargs
                Additional keyword arguments.

            Returns
            -------
            AlignmentScore
                The alignment score.
            """

            return AlignmentScore(reason="test - high score", score=0.9)

        monkeypatch.setattr(
            "core_backend.app.llm_call.process_output.ALIGN_SCORE_THRESHOLD", 0.7
        )
        monkeypatch.setattr(
            "core_backend.app.llm_call.process_output._get_llm_align_score",
            mock_get_align_score,
        )
        update_query_response = await _check_align_score(response=user_query_response)
        assert isinstance(update_query_response, QueryResponse)
        assert update_query_response.debug_info["factual_consistency"]["score"] == 0.9

    async def test_get_context_string_from_search_results(
        self, user_query_response: QueryResponse
    ) -> None:
        """Test getting context string from search results.

        Parameters
        ----------
        user_query_response
            The user query response.
        """

        assert user_query_response.search_results is not None  # Type assertion for mypy

        context_string = get_context_string_from_search_results(
            search_results=user_query_response.search_results
        )

        expected_context_string = (
            "1. World\nhello world\n\n2. Universe\ngoodbye universe"
        )
        assert context_string == expected_context_string
