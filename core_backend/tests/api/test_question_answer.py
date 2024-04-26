from functools import partial
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from core_backend.app.auth.config import USER1_RETRIEVAL_SECRET
from core_backend.app.llm_call.check_output import _build_evidence, _check_align_score
from core_backend.app.llm_call.llm_prompts import AlignmentScore, IdentifiedLanguage
from core_backend.app.llm_call.parse_input import _classify_safety, _translate_question
from core_backend.app.question_answer.config import N_TOP_CONTENT_FOR_SEARCH
from core_backend.app.question_answer.schemas import (
    ErrorType,
    ResultState,
    UserQueryRefined,
    UserQueryResponse,
    UserQueryResponseError,
    UserQuerySearchResult,
)


class TestEmbeddingsSearch:
    @pytest.mark.parametrize(
        "token, expected_status_code",
        [(f"{USER1_RETRIEVAL_SECRET}_incorrect", 401), (USER1_RETRIEVAL_SECRET, 200)],
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
            assert len(json_content_response.keys()) == int(N_TOP_CONTENT_FOR_SEARCH)

    @pytest.fixture
    def question_response(self, client: TestClient) -> UserQueryResponse:
        response = client.post(
            "/embeddings-search",
            json={
                "query_text": "Tell me about a good sport to play",
            },
            headers={"Authorization": f"Bearer {USER1_RETRIEVAL_SECRET}"},
        )
        return response.json()

    @pytest.mark.parametrize(
        "token, expected_status_code, endpoint",
        [
            (f"{USER1_RETRIEVAL_SECRET}_incorrect", 401, "/response-feedback"),
            (USER1_RETRIEVAL_SECRET, 200, "/response-feedback"),
            (f"{USER1_RETRIEVAL_SECRET}_incorrect", 401, "/content-feedback"),
            (USER1_RETRIEVAL_SECRET, 200, "/content-feedback"),
        ],
    )
    def test_response_feedback_correct_token(
        self,
        token: str,
        expected_status_code: int,
        endpoint: str,
        client: TestClient,
        question_response: Dict[str, Any],
        faq_contents: Dict[str, Any],
    ) -> None:
        query_id = question_response["query_id"]
        feedback_secret_key = question_response["feedback_secret_key"]

        json = {
            "feedback_text": "This is feedback",
            "query_id": query_id,
            "feedback_sentiment": "positive",
            "feedback_secret_key": feedback_secret_key,
        }

        if endpoint == "/content-feedback":
            json["content_id"] = 1

        print(json)
        response = client.post(
            endpoint,
            json=json,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == expected_status_code

    @pytest.mark.parametrize("endpoint", ["/response-feedback", "/content-feedback"])
    def test_response_feedback_incorrect_secret(
        self,
        endpoint: str,
        client: TestClient,
        question_response: Dict[str, Any],
    ) -> None:
        query_id = question_response["query_id"]

        json = {
            "feedback_text": "This feedback has the wrong secret key",
            "query_id": query_id,
            "feedback_secret_key": "incorrect_key",
        }

        if endpoint == "/content-feedback":
            json["content_id"] = 1

        response = client.post(
            endpoint,
            json=json,
            headers={"Authorization": f"Bearer {USER1_RETRIEVAL_SECRET}"},
        )
        assert response.status_code == 400

    @pytest.mark.parametrize("endpoint", ["/response-feedback", "/content-feedback"])
    def test_response_feedback_incorrect_query_id(
        self, endpoint: str, client: TestClient, question_response: Dict[str, Any]
    ) -> None:
        feedback_secret_key = question_response["feedback_secret_key"]
        json = {
            "feedback_text": "This feedback has the wrong query id",
            "query_id": 99999,
            "feedback_secret_key": feedback_secret_key,
        }
        if endpoint == "/content-feedback":
            json["content_id"] = 1

        response = client.post(
            endpoint,
            json=json,
            headers={"Authorization": f"Bearer {USER1_RETRIEVAL_SECRET}"},
        )
        assert response.status_code == 400

    @pytest.mark.parametrize("endpoint", ["/response-feedback", "/content-feedback"])
    def test_response_feedback_incorrect_sentiment(
        self, endpoint: str, client: TestClient, question_response: Dict[str, Any]
    ) -> None:
        query_id = question_response["query_id"]
        feedback_secret_key = question_response["feedback_secret_key"]

        json = {
            "feedback_text": "This feedback has the wrong sentiment",
            "query_id": query_id,
            "feedback_sentiment": "incorrect",
            "feedback_secret_key": feedback_secret_key,
        }

        if endpoint == "/content-feedback":
            json["content_id"] = 1

        response = client.post(
            endpoint,
            json=json,
            headers={"Authorization": f"Bearer {USER1_RETRIEVAL_SECRET}"},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("endpoint", ["/response-feedback", "/content-feedback"])
    def test_response_feedback_sentiment_only(
        self, endpoint: str, client: TestClient, question_response: Dict[str, Any]
    ) -> None:
        query_id = question_response["query_id"]
        feedback_secret_key = question_response["feedback_secret_key"]

        json = {
            "query_id": query_id,
            "feedback_sentiment": "positive",
            "feedback_secret_key": feedback_secret_key,
        }
        if endpoint == "/content-feedback":
            json["content_id"] = 1

        response = client.post(
            endpoint,
            json=json,
            headers={"Authorization": f"Bearer {USER1_RETRIEVAL_SECRET}"},
        )
        assert response.status_code == 200

    @pytest.mark.parametrize("content_id, response_code", ([1, 200], [999, 400]))
    def test_content_feedback_check_content_id(
        self,
        content_id: int,
        response_code: int,
        client: TestClient,
        question_response: Dict[str, Any],
        faq_contents: Dict[str, Any],
    ) -> None:
        query_id = question_response["query_id"]
        feedback_secret_key = question_response["feedback_secret_key"]
        response = client.post(
            "/content-feedback",
            json={
                "query_id": query_id,
                "content_id": content_id,
                "feedback_text": "This feedback has the wrong content id",
                "feedback_sentiment": "positive",
                "feedback_secret_key": feedback_secret_key,
            },
            headers={"Authorization": f"Bearer {USER1_RETRIEVAL_SECRET}"},
        )
        assert response.status_code == response_code


class TestLLMSearch:
    @pytest.mark.parametrize(
        "token, expected_status_code",
        [(f"{USER1_RETRIEVAL_SECRET}_incorrect", 401), (USER1_RETRIEVAL_SECRET, 200)],
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

            content_response = response.json()["content_response"]
            assert len(content_response) != 0

            result_state = response.json()["state"]
            assert result_state == ResultState.FINAL


class TestErrorResponses:
    VALID_LANGUAGE = IdentifiedLanguage.get_supported_languages()[-1]

    @pytest.fixture
    def user_query_response(
        self,
    ) -> UserQueryResponse:
        return UserQueryResponse(
            query_id=124,
            content_response={},
            llm_response=None,
            feedback_secret_key="abc123",
            debug_info={},
            state=ResultState.IN_PROGRESS,
        )

    @pytest.fixture
    def user_query_refined(self, request: pytest.FixtureRequest) -> UserQueryRefined:
        if hasattr(request, "param"):
            language = request.param
        else:
            language = None
        return UserQueryRefined(
            query_text="This is a basic query",
            original_language=language,
            query_text_original="This is a query original",
        )

    @pytest.mark.parametrize(
        "user_query_refined,should_error",
        [("ENGLISH", False), ("MADE_UP_LANGUAGE", True), (VALID_LANGUAGE, False)],
        indirect=["user_query_refined"],
    )
    async def test_translate_error(
        self,
        user_query_refined: UserQueryRefined,
        user_query_response: UserQueryResponse,
        should_error: bool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async def mock_ask_llm(*args: Any, **kwargs: Any) -> str:
            return "This is a translated LLM response"

        monkeypatch.setattr(
            "core_backend.app.llm_call.parse_input._ask_llm_async", mock_ask_llm
        )
        query, response = await _translate_question(
            user_query_refined, user_query_response
        )
        if should_error:
            assert isinstance(response, UserQueryResponseError)
            assert response.error_type == ErrorType.UNKNOWN_LANGUAGE
        else:
            assert isinstance(response, UserQueryResponse)
            if query.original_language == "ENGLISH":
                assert query.query_text == "This is a basic query"
            else:
                assert query.query_text == "This is a translated LLM response"

    @pytest.mark.parametrize(
        "classification, should_error",
        [("SAFE", False), ("INAPPROPRIATE_LANGUAGE", True), ("PROMPT_INJECTION", True)],
    )
    async def test_unsafe_query_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        user_query_refined: UserQueryRefined,
        user_query_response: UserQueryResponse,
        classification: str,
        should_error: bool,
    ) -> None:
        async def mock_ask_llm(llm_response: str, *args: Any, **kwargs: Any) -> str:
            return llm_response

        monkeypatch.setattr(
            "core_backend.app.llm_call.parse_input._ask_llm_async",
            partial(mock_ask_llm, classification),
        )
        query, response = await _classify_safety(
            user_query_refined, user_query_response
        )

        if should_error:
            assert isinstance(response, UserQueryResponseError)
            assert response.error_type == ErrorType.QUERY_UNSAFE
        else:
            assert isinstance(response, UserQueryResponse)
            assert query.query_text == "This is a basic query"


class TestAlignScore:
    @pytest.fixture
    def user_query_response(self) -> UserQueryResponse:
        return UserQueryResponse(
            query_id=124,
            content_response={
                1: UserQuerySearchResult(
                    retrieved_title="World",
                    retrieved_text="hello world",
                    retrieved_content_id=1,
                    score=0.2,
                ),
                2: UserQuerySearchResult(
                    retrieved_title="Universe",
                    retrieved_text="goodbye universe",
                    retrieved_content_id=2,
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
        assert isinstance(update_query_response, UserQueryResponse)
        assert update_query_response.debug_info["factual_consistency"]["score"] == 0.2
        assert update_query_response.llm_response is None

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
