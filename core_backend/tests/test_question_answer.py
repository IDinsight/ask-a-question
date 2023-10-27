import json
import uuid

import pytest
from fastapi.testclient import TestClient
from litellm import embedding
from qdrant_client.models import PointStruct

from core_backend.app.configs.app_config import (
    EMBEDDING_MODEL,
    QDRANT_COLLECTION_NAME,
    QDRANT_N_TOP_SIMILAR,
    QUESTION_ANSWER_SECRET,
)
from core_backend.app.db.vector_db import get_qdrant_client
from core_backend.app.routers.manage_content import _create_payload_for_qdrant_upsert

from .conftest import fake_embedding


class TestEmbeddingsSearch:
    @pytest.fixture
    def faq_contents(self, client: TestClient) -> None:
        with open("tests/data/content.json", "r") as f:
            json_data = json.load(f)

        points = []
        for content in json_data:
            point_id = str(uuid.uuid4())
            content_embedding = (
                fake_embedding(EMBEDDING_MODEL, content["content_text"])
                .data[0]
                .embedding
            )
            metadata = content.get("content_metadata", {})
            payload = _create_payload_for_qdrant_upsert(
                content["content_text"], metadata
            )
            points.append(
                PointStruct(id=point_id, vector=content_embedding, payload=payload)
            )

        qdrant_client = get_qdrant_client()
        qdrant_client.upsert(collection_name=QDRANT_COLLECTION_NAME, points=points)

    @pytest.mark.parametrize(
        "token, expected_status_code",
        [(f"{QUESTION_ANSWER_SECRET}_incorrect", 401), (QUESTION_ANSWER_SECRET, 200)],
    )
    def test_faq_response(
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
            json_faq_response = response.json()["faq_response"]
            assert len(json_faq_response.keys()) == int(QDRANT_N_TOP_SIMILAR)


class TestLLMSearch:
    @pytest.fixture
    def faq_contents(self, client: TestClient) -> None:
        with open("tests/data/content.json", "r") as f:
            json_data = json.load(f)

        points = []
        for content in json_data:
            point_id = str(uuid.uuid4())
            content_embedding = (
                embedding(EMBEDDING_MODEL, content["content_text"]).data[0].embedding
            )
            payload = content.get("content_metadata", {})
            points.append(
                PointStruct(id=point_id, vector=content_embedding, payload=payload)
            )

        qdrant_client = get_qdrant_client()
        qdrant_client.upsert(collection_name=QDRANT_COLLECTION_NAME, points=points)

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
