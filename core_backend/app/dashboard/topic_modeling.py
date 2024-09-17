"""
This module contains functions for the topic modeling pipeline.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import pandas as pd
from bertopic import BERTopic
from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer
from umap import UMAP

from ..llm_call.dashboard import generate_topic_label  # Adjust import as necessary
from ..utils import setup_logger
from .config import TOPIC_MODELING_CONTEXT
from .schemas import InsightContent, Topic, TopicsData, UserQuery

logger = setup_logger()


async def topic_model_queries(
    user_id: int, query_data: List[UserQuery], content_data: List[InsightContent]
) -> Tuple[TopicsData, pd.DataFrame]:
    """Perform topic modeling on user queries and content data.

    Parameters
    ----------
    user_id : int
        The ID of the user making the request.
    query_data : List[UserQuery]
        A list of UserQuery objects containing the raw queries and their
        datetime stamps.
    content_data : List[InsightContent]
        A list of InsightContent objects containing content data.

    Returns
    -------
    Tuple[TopicsData, pd.DataFrame]
        A tuple containing TopicsData for the frontend and a DataFrame with embeddings.
    """
    if not query_data:
        logger.info("No queries to cluster")
        return (
            TopicsData(
                refreshTimeStamp="",
                data=[],
                unclustered_queries=[],
                embeddings_dataframe={},
            ),
            pd.DataFrame(),
        )

    if not content_data:
        logger.info("No content data to cluster")
        return (
            TopicsData(
                refreshTimeStamp="",
                data=[],
            ),
            pd.DataFrame(),
        )

    # Prepare dataframes
    results_df = prepare_dataframes(query_data, content_data)

    # Generate embeddings
    embeddings = generate_embeddings(results_df["text"].tolist())

    # Fit the BERTopic model
    topic_model = fit_topic_model(results_df["text"].tolist(), embeddings)

    # Transform documents to get topics and probabilities
    topics, _ = topic_model.transform(results_df["text"], embeddings)
    results_df["topic_id"] = topics

    # Add reduced embeddings (for visualization)
    add_reduced_embeddings(results_df, topic_model)

    # Generate topic labels using LLM
    topic_labels = await generate_topic_labels_async(results_df, user_id)

    # Add topic titles to the DataFrame
    results_df["topic_title"] = results_df.apply(
        lambda row: get_topic_title(row, topic_labels), axis=1
    )

    # Prepare TopicsData for frontend
    topics_data = prepare_topics_data(results_df, topic_labels)

    return topics_data, results_df


def prepare_dataframes(
    query_data: List[UserQuery], content_data: List[InsightContent]
) -> pd.DataFrame:
    """Prepare a unified DataFrame combining queries and content data."""
    # Convert to DataFrames
    content_df = pd.DataFrame.from_records([x.model_dump() for x in content_data])
    content_df["type"] = "content"

    query_df = pd.DataFrame.from_records([x.model_dump() for x in query_data])
    query_df["type"] = "query"
    query_df["query_datetime_utc"] = query_df["query_datetime_utc"].astype(str)

    # Combine queries and content
    full_texts = query_df["query_text"].tolist() + content_df["content_text"].tolist()
    types = query_df["type"].tolist() + content_df["type"].tolist()
    datetimes = query_df["query_datetime_utc"].tolist() + [""] * len(content_df)

    # Create combined DataFrame
    results_df = pd.DataFrame(
        {"text": full_texts, "type": types, "datetime": datetimes}
    )

    return results_df


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts using SentenceTransformer."""
    sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = sentence_model.encode(texts, show_progress_bar=False)
    return embeddings


def fit_topic_model(texts: List[str], embeddings: List[List[float]]) -> BERTopic:
    """Fit a BERTopic model on the provided texts and embeddings."""
    umap_model = UMAP(
        n_components=2,
        n_neighbors=15,
        min_dist=0.0,
        metric="cosine",
        random_state=42,  # For reproducibility
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=20,
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )
    topic_model = BERTopic(
        hdbscan_model=hdbscan_model,
        umap_model=umap_model,
        calculate_probabilities=True,
        verbose=False,
    )
    topic_model.fit(texts, embeddings)
    return topic_model


def add_reduced_embeddings(results_df: pd.DataFrame, topic_model: BERTopic) -> None:
    """Add reduced embeddings (2D) to the results DataFrame."""
    reduced_embeddings = topic_model.umap_model.embedding_
    results_df["x"] = reduced_embeddings[:, 0]
    results_df["y"] = reduced_embeddings[:, 1]


async def generate_topic_labels_async(
    results_df: pd.DataFrame, user_id: int
) -> Dict[int, Dict[str, str]]:
    """Generate topic labels asynchronously using an LLM."""
    tasks = []
    topic_ids = []

    # Group by topic_id
    grouped = results_df.groupby("topic_id")

    for topic_id, topic_df in grouped:
        if topic_id == -1:
            continue  # Skip noise/unclassified topics

        # Get top 5 query samples for the topic
        topic_queries = topic_df[topic_df["type"] == "query"]["text"].head(5).tolist()

        # Create task for generating topic label
        tasks.append(
            generate_topic_label(
                topic_id,
                user_id,
                TOPIC_MODELING_CONTEXT,
                topic_queries,
            )
        )
        topic_ids.append(topic_id)

    # Run tasks concurrently
    topic_dicts = await asyncio.gather(*tasks)

    # Map topic_ids to topic_dicts
    topic_labels = {tid: tdict for tid, tdict in zip(topic_ids, topic_dicts)}

    return topic_labels


def get_topic_title(row: pd.Series, topic_labels: Dict[int, Dict[str, str]]) -> str:
    """Get the topic title for a given row."""
    if row["topic_id"] == -1:
        return "Unclassified"
    elif row["type"] == "content":
        return "Content"
    else:
        return topic_labels.get(row["topic_id"], {}).get("topic_title", "Unknown Topic")


def prepare_topics_data(
    results_df: pd.DataFrame, topic_labels: Dict[int, Dict[str, str]]
) -> TopicsData:
    """Prepare the TopicsData object for the frontend."""
    topics_list = []

    # Group by topic_id
    grouped = results_df.groupby("topic_id")

    for topic_id, topic_df in grouped:
        only_queries = topic_df[topic_df["type"] == "query"]

        # Collect unclassified queries
        if topic_id == -1:
            continue

        # Get topic information
        topic_dict = topic_labels.get(
            topic_id, {"topic_title": "Unknown", "topic_summary": ""}
        )

        # Get topic samples
        topic_samples_slice = only_queries[["text", "datetime"]].head(20)
        string_topic_samples = [
            {
                "query_text": str(sample["text"]),
                "query_datetime_utc": str(sample["datetime"]),
            }
            for sample in topic_samples_slice.to_dict(orient="records")
        ]

        # Create Topic object
        topic = Topic(
            topic_id=int(topic_id),
            topic_name=topic_dict["topic_title"],
            topic_summary=topic_dict["topic_summary"],
            topic_samples=string_topic_samples,
            topic_popularity=len(only_queries),
        )
        topics_list.append(topic)

    # Sort topics by popularity
    topics_list = sorted(topics_list, key=lambda x: -x.topic_popularity)

    # Prepare TopicsData
    topics_data = TopicsData(
        refreshTimeStamp=datetime.now(timezone.utc).isoformat(),
        data=topics_list,
    )

    return topics_data
