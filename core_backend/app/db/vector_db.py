from typing import Dict, List

from litellm import aembedding, embedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSelectorInclude,
    VectorParams,
)

from core_backend.app.configs.llm_prompts import IdentifiedLanguage

from ..configs.app_config import (
    EMBEDDING_MODEL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION_NAME,
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_URL,
)
from ..schemas import UserQueryBase, UserQuerySearchResult

_qdrant_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """
    Return QdrantClient instance. If an instance already exists, return it.
    """
    global _qdrant_client
    if _qdrant_client is None:
        if QDRANT_URL and QDRANT_API_KEY:
            _qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        elif QDRANT_HOST and QDRANT_PORT:
            _qdrant_client = QdrantClient(host=QDRANT_HOST, port=int(QDRANT_PORT))
        else:
            raise Exception("Unable to instantiate QdrantClient")

    return _qdrant_client


def create_qdrant_collection(collection_name: str, embeddings_dim: str) -> None:
    """
    Create a collection in Qdrant
    """
    qdrant_client = get_qdrant_client()
    result = qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=int(embeddings_dim), distance=Distance.COSINE),
    )

    if not result:
        raise Exception("Unable to create collection in Qdrant")


def get_similar_content(
    question: UserQueryBase,
    qdrant_client: QdrantClient,
    n_similar: int,
    qdrant_collection_name: str = QDRANT_COLLECTION_NAME,
) -> Dict[int, UserQuerySearchResult]:
    """
    Get the most similar points in the vector db
    """
    response = embedding(EMBEDDING_MODEL, question.query_text)
    question_embedding = response.data[0]["embedding"]
    question_language = question.original_language.value

    return get_search_results(
        question_embedding, question_language, qdrant_client, n_similar, qdrant_collection_name
    )


async def get_similar_content_async(
    question: UserQueryBase,
    qdrant_client: QdrantClient,
    n_similar: int,
    qdrant_collection_name: str = QDRANT_COLLECTION_NAME,
) -> Dict[int, UserQuerySearchResult]:
    """
    Get the most similar points in the vector db
    """
    response = await aembedding(EMBEDDING_MODEL, question.query_text)
    question_embedding = response.data[0]["embedding"]
    question_language = question.original_language.value

    return get_search_results(
        question_embedding, question_language, qdrant_client, n_similar, qdrant_collection_name
    )


def get_search_results(
    question_embedding: List[float],
    question_language: IdentifiedLanguage,
    qdrant_client: QdrantClient,
    n_similar: int,
    qdrant_collection_name: str = QDRANT_COLLECTION_NAME,
) -> Dict[int, UserQuerySearchResult]:
    """Get similar content to given embedding and return search results"""
    search_result = qdrant_client.search(
        collection_name=qdrant_collection_name,
        query_vector=question_embedding,
        limit=n_similar,
        with_payload=PayloadSelectorInclude(include=["content_title", "content_text"]),
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="content_language",
                    match=MatchValue(value=question_language.value),
                ),
            ]
        ),
    )

    results_dict = {}
    for i, r in enumerate(search_result):
        if r.payload is None:
            raise ValueError("Payload is empty. No content text found.")
        else:
            results_dict[i] = UserQuerySearchResult(
                retrieved_title=r.payload.get("content_title", ""),
                retrieved_text=r.payload.get("content_text", ""),
                score=r.score,
            )

    return results_dict
