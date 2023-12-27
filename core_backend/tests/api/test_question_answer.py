import pytest
from fastapi.testclient import TestClient

from core_backend.app.configs.app_config import (
    QDRANT_N_TOP_SIMILAR,
    QUESTION_ANSWER_SECRET,
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
    def question_response(self, client: TestClient) -> None:
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
        question_response: pytest.FixtureRequest,
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
        self, client: TestClient, question_response: pytest.FixtureRequest
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
        self, client: TestClient, question_response: pytest.FixtureRequest
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
