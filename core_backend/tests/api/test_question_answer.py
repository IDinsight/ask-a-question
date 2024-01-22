from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from core_backend.app.configs.app_config import (
    QDRANT_N_TOP_SIMILAR,
    QUESTION_ANSWER_SECRET,
)
from core_backend.app.configs.llm_prompts import AlignmentScore
from core_backend.app.llm_call.check_output import _build_evidence, _check_align_score
from core_backend.app.schemas import (
    ErrorType,
    ResultState,
    UserQueryResponse,
    UserQueryResponseError,
    UserQuerySearchResult,
)


class TestEmbeddingsSearch:
    @pytest.mark.parametrize(
        "token, expected_status_code",
        [(f"{QUESTION_ANSWER_SECRET}_incorrect", 401), (QUESTION_ANSWER_SECRET, 200)],
    )
    def test_content_response(
        self,
        token: str,
        expected_status_code: int,
        client: TestClient,
        faq_contents: pytest.FixtureRequest,
    ) -> None:
        response = client.post(
            "/embeddings-search",
            json={"query_text": "Tell me about a good sport to play"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == expected_status_code

        if expected_status_code == 200:
            json_content_response = response.json()["content_response"]
            assert len(json_content_response.keys()) == int(QDRANT_N_TOP_SIMILAR)

    @pytest.fixture
    def question_response(self, client: TestClient) -> UserQueryResponse:
        response = client.post(
            "/embeddings-search",
            json={
                "query_text": "Tell me about a good sport to play",
            },
            headers={"Authorization": f"Bearer {QUESTION_ANSWER_SECRET}"},
        )
        return response.json()

    @pytest.mark.parametrize(
        "token, expected_status_code",
        [(f"{QUESTION_ANSWER_SECRET}_incorrect", 401), (QUESTION_ANSWER_SECRET, 200)],
    )
    def test_feedback_correct(
        self,
        token: str,
        expected_status_code: int,
        client: TestClient,
        question_response: Dict[str, Any],
    ) -> None:
        query_id = question_response["query_id"]
        feedback_secret_key = question_response["feedback_secret_key"]

        response = client.post(
            "/feedback",
            json={
                "feedback_text": "This is feedback",
                "query_id": query_id,
                "feedback_secret_key": feedback_secret_key,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == expected_status_code

    def test_feedback_incorrect_secret(
        self, client: TestClient, question_response: Dict[str, Any]
    ) -> None:
        query_id = question_response["query_id"]
        response = client.post(
            "/feedback",
            json={
                "feedback_text": "This feedback has the wrong secret key",
                "query_id": query_id,
                "feedback_secret_key": "incorrect_key",
            },
            headers={"Authorization": f"Bearer {QUESTION_ANSWER_SECRET}"},
        )
        assert response.status_code == 400

    def test_feedback_incorrect_query_id(
        self, client: TestClient, question_response: Dict[str, Any]
    ) -> None:
        feedback_secret_key = question_response["feedback_secret_key"]
        response = client.post(
            "/feedback",
            json={
                "feedback_text": "This feedback has the wrong query id",
                "query_id": 99999,
                "feedback_secret_key": feedback_secret_key,
            },
            headers={"Authorization": f"Bearer {QUESTION_ANSWER_SECRET}"},
        )
        assert response.status_code == 400


class TestLLMSearch:
    @pytest.mark.parametrize(
        "token, expected_status_code",
        [(f"{QUESTION_ANSWER_SECRET}_incorrect", 401), (QUESTION_ANSWER_SECRET, 200)],
    )
    def test_llm_response(
        self,
        token: str,
        expected_status_code: int,
        client: TestClient,
        faq_contents: pytest.FixtureRequest,
    ) -> None:
        response = client.post(
            "/llm-response",
            json={"query_text": "Tell me about a good sport to play"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == expected_status_code

        if expected_status_code == 200:
            llm_response = response.json()["llm_response"]
            assert len(llm_response) != 0

        if expected_status_code == 200:
            content_response = response.json()["content_response"]
            assert len(content_response) != 0


class TestAlignScore:
    @pytest.fixture
    def user_query_response(self) -> UserQueryResponse:
        return UserQueryResponse(
            query_id=124,
            content_response={
                1: UserQuerySearchResult(
                    retrieved_title="World",
                    retrieved_text="hello world",
                    score=0.2,
                ),
                2: UserQuerySearchResult(
                    retrieved_title="Universe",
                    retrieved_text="goodbye universe",
                    score=0.2,
                ),
            },
            llm_response="This is a response",
            feedback_secret_key="abc123",
            debug_info={},
            state=ResultState.IN_PROGRESS,
        )

    @pytest.mark.asyncio
    async def test_score_less_than_threshold(
        self, user_query_response: UserQueryResponse, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_get_align_score(*args: Any, **kwargs: Any) -> AlignmentScore:
            return AlignmentScore(score=0.2, reason="test - low score")

        monkeypatch.setattr(
            "core_backend.app.llm_call.check_output._get_alignScore_score",
            mock_get_align_score,
        )
        monkeypatch.setattr(
            "core_backend.app.llm_call.check_output._get_llm_align_score",
            mock_get_align_score,
        )
        monkeypatch.setattr(
            "core_backend.app.llm_call.check_output.ALIGN_SCORE_THRESHOLD",
            0.7,
        )
        update_query_response = await _check_align_score(user_query_response)
        assert isinstance(update_query_response, UserQueryResponseError)
        assert update_query_response.error_type == ErrorType.ALIGNMENT_TOO_LOW
        assert update_query_response.debug_info["factual_consistency"]["score"] == 0.2

    @pytest.mark.asyncio
    async def test_score_greater_than_threshold(
        self, user_query_response: UserQueryResponse, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_get_align_score(*args: Any, **kwargs: Any) -> AlignmentScore:
            return AlignmentScore(score=0.9, reason="test - high score")

        monkeypatch.setattr(
            "core_backend.app.llm_call.check_output._get_alignScore_score",
            mock_get_align_score,
        )
        monkeypatch.setattr(
            "core_backend.app.llm_call.check_output.ALIGN_SCORE_THRESHOLD",
            0.7,
        )
        monkeypatch.setattr(
            "core_backend.app.llm_call.check_output._get_llm_align_score",
            mock_get_align_score,
        )
        update_query_response = await _check_align_score(user_query_response)
        assert isinstance(update_query_response, UserQueryResponse)
        assert update_query_response.debug_info["factual_consistency"]["score"] == 0.9

    def test_build_evidence(
        self, user_query_response: UserQueryResponse, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        evidence = _build_evidence(user_query_response)
        assert evidence == "hello world\ngoodbye universe\n"
