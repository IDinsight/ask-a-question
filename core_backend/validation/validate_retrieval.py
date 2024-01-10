import asyncio
import uuid
from typing import Dict, List, Union

import pandas as pd
from litellm import aembedding, embedding
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from core_backend.app.configs.app_config import EMBEDDING_MODEL, QDRANT_VECTOR_SIZE
from core_backend.app.db.vector_db import (
    create_qdrant_collection,
    get_qdrant_client,
    get_search_results,
)
from core_backend.app.schemas import UserQueryBase, UserQuerySearchResult

VALIDATION_COLLECTION_NAME = "validation_collection"
QUESTION_COL = "question"
CONTENT_LABEL_COL = "faq_name"
CONTENT_TEXT_COL = "faq_content_to_send"


async def aget_similar_content(
    question: UserQueryBase,
    qdrant_client: QdrantClient,
    n_similar: int,
    qdrant_collection_name: str,
) -> Dict[int, UserQuerySearchResult]:
    """
    Get the most similar points in the vector db asynchronously
    """
    response = await aembedding(EMBEDDING_MODEL, question.query_text)
    question_embedding = response.data[0]["embedding"]

    return get_search_results(
        question_embedding, qdrant_client, n_similar, qdrant_collection_name
    )


def get_rank(row: pd.Series) -> Union[int, None]:
    """Get the rank of label in the retrieved content IDs"""
    label = row[CONTENT_LABEL_COL]
    ranked_list = row["retrieved_content_titles"]
    try:
        return ranked_list.index(label) + 1
    except ValueError:
        return None


def get_retrieved_content_labels(
    retrieval_results: Dict[int, UserQuerySearchResult]
) -> List:
    """Extract retrieved content IDs from results dict"""
    i = 0
    retrieved_content_labels = []
    while i in retrieval_results:
        label = retrieval_results[i].retrieved_title
        retrieved_content_labels.append(label)
        i += 1
    return retrieved_content_labels


def load_content_to_qdrant(content_dataframe: pd.DataFrame) -> QdrantClient:
    """Load content to qdrant collection"""
    client = get_qdrant_client()

    if VALIDATION_COLLECTION_NAME not in {
        collection.name for collection in client.get_collections().collections
    }:
        create_qdrant_collection(VALIDATION_COLLECTION_NAME, QDRANT_VECTOR_SIZE)

    # get embeddings
    embedding_results = embedding(
        EMBEDDING_MODEL, input=content_dataframe["content_text"].tolist()
    )
    content_embeddings = [x["embedding"] for x in embedding_results.data]

    # upsert to qdrant collection
    points = [
        PointStruct(
            id=str(content_id),
            vector=content_embedding,
            payload=payload,
        )
        for content_id, content_embedding, payload in zip(
            content_dataframe["content_id"],
            content_embeddings,
            content_dataframe[["content_title", "content_text"]].to_dict("records"),
        )
    ]
    client.upsert(
        collection_name=VALIDATION_COLLECTION_NAME,
        points=points,
    )

    return client


async def retrieve(
    query_text: str, client: QdrantClient, n: int
) -> Dict[int, UserQuerySearchResult]:
    """Retrieve n most similar content from vector db for a given query"""
    query_obj = UserQueryBase(query_text=query_text)
    results_dict = await aget_similar_content(
        query_obj, client, n, VALIDATION_COLLECTION_NAME
    )
    return results_dict


async def retrieve_results(
    df: pd.DataFrame, client: QdrantClient, n: int
) -> pd.DataFrame:
    """Asynchronousely retrieve similar content for all queries in validation data"""
    tasks = [retrieve(query, client, n) for query in df[QUESTION_COL]]
    df["retrieval_results"] = await asyncio.gather(*tasks)
    return df


def validate_retrieval(
    validation_data_path: str,
    content_data: str,
    n: int = 10,
    aws_profile: Union[str, None] = None,
) -> None:
    """Validate retrieval model on validation data"""
    val_df = pd.read_csv(
        validation_data_path, storage_options=dict(profile=aws_profile)
    )
    content_df = pd.read_csv(content_data, storage_options=dict(profile=aws_profile))

    content_df["content_id"] = [uuid.uuid4() for _ in range(len(content_df))]
    content_df = content_df.rename(
        columns={CONTENT_LABEL_COL: "content_title", CONTENT_TEXT_COL: "content_text"}
    )

    client = load_content_to_qdrant(content_df)

    try:
        val_df = asyncio.run(retrieve_results(val_df, client, n))

        val_df["retrieved_content_titles"] = val_df["retrieval_results"].apply(
            get_retrieved_content_labels
        )
        val_df["rank"] = val_df.apply(get_rank, axis=1)

        # TODO: add validation metrics
        top5 = (val_df["rank"] <= 5).mean()
        print(f"Top-5 accuracy: {top5:.1%}")
    finally:
        client.delete_collection(collection_name=VALIDATION_COLLECTION_NAME)
