import argparse
import asyncio
import os
import uuid
from datetime import datetime
from typing import Dict, List, Union

import boto3
import pandas as pd
from dateutil import tz
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

parser = argparse.ArgumentParser()
parser.add_argument("--validation_data_path", type=str, help="Path to validation data")
parser.add_argument("--content_data_path", type=str, help="Path to validation data")
parser.add_argument(
    "--validation_data_question_col",
    type=str,
    help="Question column in validation data",
)
parser.add_argument(
    "--validation_data_label_col",
    type=str,
    help="Content label column in validation data",
)
parser.add_argument(
    "--content_data_label_col", type=str, help="Content label column in content data"
)
parser.add_argument(
    "--content_data_text_col", type=str, help="Content text body column in content data"
)
parser.add_argument(
    "--notification_topic", type=str, help="SNS topic to send notification to"
)
parser.add_argument(
    "--n_similar",
    "-n",
    type=int,
    help="Number of top similar content to retrieve",
    default=10,
)
parser.add_argument(
    "--aws_profile",
    type=str,
    help="AWS profile name",
    default=None,
)
args = parser.parse_args()


VALIDATION_COLLECTION_NAME = "validation_collection"


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
    label = row[args.content_data_label_col]
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
    tasks = [
        retrieve(query, client, n) for query in df[args.validation_data_question_col]
    ]
    df["retrieval_results"] = await asyncio.gather(*tasks)
    return df


def prepare_content_data() -> pd.DataFrame:
    """Prepare content data for loading to qdrant collection"""
    df = pd.read_csv(
        args.content_data_path, storage_options=dict(profile=args.aws_profile)
    )
    df["content_id"] = [uuid.uuid4() for _ in range(len(df))]
    df = df.rename(
        columns={
            args.content_data_label_col: "content_title",
            args.content_data_text_col: "content_text",
        }
    )
    return df


def generate_retrieval_results(client: QdrantClient) -> pd.DataFrame:
    """Generate retrieval results for all queries in validation data"""
    df = pd.read_csv(
        args.validation_data_path, storage_options=dict(profile=args.aws_profile)
    )
    df = asyncio.run(retrieve_results(df, client, args.n_similar))

    df["retrieved_content_titles"] = df["retrieval_results"].apply(
        get_retrieved_content_labels
    )
    df["rank"] = df.apply(get_rank, axis=1)
    return df


def get_top_k_accuracy_table(df: pd.DataFrame) -> List[float]:
    """Get top K accuracy table for validation results"""
    accuracies = []
    for i in range(1, args.n_similar + 1):
        acc = (df["rank"] <= i).mean()
        accuracies.append(acc)
    return accuracies


def generate_message(accuracies: List[float]) -> Dict[str, str]:
    """Generate messages for validation results"""
    ist = tz.gettz("Asia/Kolkata")
    timestamp = datetime.now(tz=ist).strftime("%Y-%m-%d %H:%M:%S IST")

    accuracy_message = "\n".join(
        [f"   • Top-{i + 1} accuracy: {acc:.1%}" for i, acc in enumerate(accuracies)]
    )

    message = (
        f"Content retrieval validation results\n"
        f"--------------------------------------------\n"
        f"\n"
        f"• Timestamp: {timestamp}\n"
        f"• Dataset:\n"
        f"   • Validation data: {args.validation_data_path}\n"
        f"   • Content data: {args.content_data_path}\n"
        f"• Embedding model: {EMBEDDING_MODEL}\n"
        f"• Top N accuracies:\n" + accuracy_message
    )

    if os.environ.get("GITHUB_ACTIONS") == "true":
        current_branch = os.environ.get("BRANCH_NAME")
        repo_name = os.environ.get("REPO")
        commit = os.environ.get("HASH")

        branch_url = f"https://github.com/{repo_name}/tree/{current_branch}"
        commit_url = f"https://github.com/{repo_name}/commit/{commit}"

        message += (
            f"\n\n"
            f"Repository: {repo_name}\n"
            f"Branch: {current_branch} ({branch_url})\n"
            f"Commit: {commit} ({commit_url})\n"
        )

    return {
        "Subject": f"Retrieval validation results ({timestamp})",
        "Message": message,
    }


def send_notification(
    message_dict: Dict[str, str],
    topic: str,
) -> None:
    """
    Function to send notification
    """
    boto3.setup_default_session(profile_name=args.aws_profile)
    sns = boto3.client("sns")

    sns.publish(
        TopicArn=topic,
        **message_dict,
    )
    print("Successfully sent message to SNS topic")


if __name__ == "__main__":
    content_df = prepare_content_data()
    client = load_content_to_qdrant(content_df)

    try:
        val_df = generate_retrieval_results(client)
    finally:
        client.delete_collection(collection_name=VALIDATION_COLLECTION_NAME)

    acc_table = get_top_k_accuracy_table(val_df)

    message_dict = generate_message(acc_table)

    print(message_dict["Message"])

    if args.notification_topic is not None:
        send_notification(message_dict, topic=args.notification_topic)
