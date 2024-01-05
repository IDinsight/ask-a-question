from typing import Dict, List, Union

import pandas as pd
from litellm import embedding
from qdrant_client import PointStruct, QdrantClient

from ..app.configs.app_config import EMBEDDING_MODEL
from ..app.db.vector_db import get_qdrant_client, get_similar_content
from ..app.schemas import UserQueryBase, UserQuerySearchResult

VALIDATION_COLLECTION_NAME = "validation_collection"
question_col = "question"
label_content_id_col = "faq_name"
content_id_col = "faq_name"
content_text_col = "faq_content_to_send"


def get_retrieved_content_ids(
    retrieval_results: Dict[int, UserQuerySearchResult]
) -> List:
    """Extract retrieved content IDs from results dict"""
    i = 0
    retrieved_content_ids = []
    while i in retrieval_results:
        content_id = retrieval_results[i].retrieved_content_id
        retrieved_content_ids.append(content_id)
        i += 1
    return retrieved_content_ids


def load_content_to_qdrant(content_dataframe: pd.DataFrame) -> QdrantClient:
    """Load content to qdrant collection"""
    client = get_qdrant_client()

    client.add_collection(VALIDATION_COLLECTION_NAME)

    # get embeddings
    embedding_results = embedding(
        EMBEDDING_MODEL, input=content_dataframe[content_text_col].tolist()
    )
    content_embeddings = [x["embedding"] for x in embedding_results.data]

    # upsert to qdrant collection
    points = [
        PointStruct(
            id=str(row.idx),
            vector=content_embedding,
            payload=payload,
        )
        for row, content_embedding, payload in zip(
            content_dataframe[content_id_col].tolist(),
            content_embeddings,
            content_dataframe[[content_id_col, content_text_col]].to_dict("records"),
        )
    ]
    client.upsert(
        collection_name=VALIDATION_COLLECTION_NAME,
        points=points,
    )
    return client


def validate_retrieval(
    validation_data_path: str,
    content_data: str,
    n: int = 10,
    aws_profile: Union[str, None] = None,
) -> None:
    """Validate retrieval model on validation data"""
    val_df = pd.read_csv(validation_data_path, profile=aws_profile)
    content_df = pd.read_csv(content_data, profile=aws_profile)

    client = load_content_to_qdrant(content_df)

    def retrieve(query_text: str) -> Dict[int, UserQuerySearchResult]:
        """Retrieve top content for a given query"""
        query_obj = UserQueryBase(query_text=query_text)
        results_dict = get_similar_content(query_obj, client, n)
        return results_dict

    val_df["retrieval_results"] = val_df[question_col].apply(retrieve)
    val_df["retrieved_content_ids"] = val_df["retrieval_results"].apply(
        get_retrieved_content_ids
    )
    val_df["rank"] = val_df.apply(get_rank, axis=1)

    # add validation metrics
    top5 = (val_df["rank"] <= 5).mean()
    print(f"Top-5 accuracy: {top5:.1%}")


def get_rank(row: pd.Series) -> Union[int, None]:
    """Get the rank of label in the retrieved content IDs"""
    label = row[label_content_id_col]
    ranked_list = row["retrieved_content_ids"]
    try:
        return ranked_list.index(label) + 1
    except ValueError:
        return None
