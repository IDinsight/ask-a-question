"""This module contains functions for the topic modeling pipeline."""

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Coroutine, cast

import numpy as np
import pandas as pd
from bertopic import BERTopic
from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer
from umap import UMAP

from ..llm_call.dashboard import generate_topic_label
from ..utils import setup_logger
from .config import TOPIC_MODELING_CONTEXT
from .schemas import BokehContentItem, Topic, TopicsData, UserQuery

logger = setup_logger()

# Check if LLM functionalities are disabled for dashboard.
DISABLE_DASHBOARD_LLM = (
    os.environ.get("DISABLE_DASHBOARD_LLM", "false").lower() == "true"
)


def add_reduced_embeddings(*, results_df: pd.DataFrame, topic_model: BERTopic) -> None:
    """Add reduced embeddings (2D) to the results DataFrame.

    Parameters
    ----------
    results_df
        A DataFrame containing the topic modeling results.
    topic_model
        A fitted BERTopic model.
    """

    reduced_embeddings = topic_model.umap_model.embedding_
    results_df["x"] = reduced_embeddings[:, 0]
    results_df["y"] = reduced_embeddings[:, 1]


def fit_topic_model(*, embeddings: np.ndarray, texts: list[str]) -> BERTopic:
    """Fit a BERTopic model on the provided texts and embeddings.

    Parameters
    ----------
    embeddings
        An array of embeddings for the provided texts.
    texts
        A list of strings to fit the topic model on.

    Returns
    -------
    BERTopic
        A fitted BERTopic model.
    """

    umap_model = UMAP(
        metric="cosine", min_dist=0.0, n_components=2, n_neighbors=15, random_state=42
    )
    hdbscan_model = HDBSCAN(
        cluster_selection_method="eom",
        metric="euclidean",
        min_cluster_size=20,
        prediction_data=True,
    )
    topic_model = BERTopic(
        calculate_probabilities=True,
        hdbscan_model=hdbscan_model,
        umap_model=umap_model,
        verbose=False,
    )
    topic_model.fit(texts, embeddings)

    return topic_model


def generate_embeddings(*, texts: list[str]) -> np.ndarray:
    """Generate embeddings for the provided texts using SentenceTransformer.

    Parameters
    ----------
    texts
        A list of strings to generate embeddings for.

    Returns
    -------
    np.ndarray
        An array of embeddings for the provided texts.
    """

    sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings_any = sentence_model.encode(
        texts, convert_to_numpy=True, convert_to_tensor=False, show_progress_bar=False
    )
    embeddings = cast(np.ndarray, embeddings_any)  # Needed for mypy issues
    return embeddings


async def generate_topic_labels_async(
    *, results_df: pd.DataFrame, topic_model: BERTopic, workspace_id: int
) -> dict[int, dict[str, str]]:
    """Generate topic labels asynchronously using an LLM or alternative method.

    Parameters
    ----------
    results_df
        A DataFrame containing the topic modeling results.
    topic_model
        A fitted BERTopic model.
    workspace_id
        The ID of the workspace.

    Returns
    -------
    dict[int, dict[str, str]]
        A dictionary mapping topic IDs to their labels.
    """

    tasks: list[Coroutine[Any, Any, dict[str, str]]] = []
    topic_ids: list[int] = []

    # Ensure `topic_id` is integer type.
    results_df["topic_id"] = results_df["topic_id"].astype(int)

    # Group by `topic_id`.
    grouped = results_df.groupby("topic_id")
    for topic_id_any, topic_df in grouped:
        topic_id = cast(int, topic_id_any)  # For type checking
        if topic_id == -1:  # Skip noise/unclassified topics
            continue

        # Get top 5 query samples for the topic.
        topic_queries = topic_df[topic_df["type"] == "query"]["text"].head(5).tolist()

        # Create task for generating topic label.
        topic_id_int = int(topic_id)
        tasks.append(
            generate_topic_label(
                context=TOPIC_MODELING_CONTEXT,
                sample_texts=topic_queries,
                topic_id=topic_id_int,
                topic_model=topic_model,
                workspace_id=workspace_id,
            )
        )
        topic_ids.append(topic_id_int)

    # Run tasks concurrently if there are tasks.
    topic_dicts = await asyncio.gather(*tasks) if tasks else []

    # Map `topic_ids` to `topic_dicts`.
    topic_labels = dict(zip(topic_ids, topic_dicts))

    # Logging for debugging.
    logger.debug(f"Generated topic_labels: {topic_labels}")

    return topic_labels


def get_topic_title(*, row: pd.Series, topic_labels: dict[int, dict[str, str]]) -> str:
    """Get the topic title for a given row.

    Parameters
    ----------
    row
        A row from the DataFrame.
    topic_labels
        A dictionary mapping topic IDs to their labels.

    Returns
    -------
    str
        The topic title for the given row.
    """

    if row["topic_id"] == -1:
        return "Unclassified"
    if row["type"] == "content":
        return "Content"
    return topic_labels.get(row["topic_id"], {}).get("topic_title", "Unknown Topic")


def prepare_dataframes(
    *, content_data: list[BokehContentItem], query_data: list[UserQuery]
) -> pd.DataFrame:
    """Prepare a unified dataframe combining queries and content data.

    Parameters
    ----------
    content_data
        A list of `BokehContentItem` objects containing content data.
    query_data
        A list of `UserQuery` objects containing the raw queries and their datetime
        stamps.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the combined data from queries and content.
    """

    # Convert to DataFrames.
    content_df = pd.DataFrame.from_records([x.model_dump() for x in content_data])
    content_df["type"] = "content"

    query_df = pd.DataFrame.from_records([x.model_dump() for x in query_data])
    query_df["type"] = "query"
    query_df["query_datetime_utc"] = query_df["query_datetime_utc"].astype(str)

    # Combine queries and content.
    full_texts = query_df["query_text"].tolist() + content_df["content_text"].tolist()
    types = query_df["type"].tolist() + content_df["type"].tolist()
    datetimes = query_df["query_datetime_utc"].tolist() + [""] * len(content_df)

    # Create combined DataFrame.
    results_df = pd.DataFrame(
        {"text": full_texts, "type": types, "datetime": datetimes}
    )

    return results_df


def prepare_topics_data(
    *, results_df: pd.DataFrame, topic_labels: dict[int, dict[str, str]]
) -> TopicsData:
    """Prepare the `TopicsData` object for the frontend.

    Parameters
    ----------
    results_df
        A DataFrame containing the topic modeling results.
    topic_labels
        A dictionary mapping topic IDs to their labels.

    Returns
    -------
    TopicsData
        A `TopicsData` object containing the topics and their details.
    """

    topics_list = []

    # Group by `topic_id`.
    grouped = results_df.groupby("topic_id")

    for topic_id_any, topic_df in grouped:
        topic_id = cast(int, topic_id_any)  # For type checking
        only_queries = topic_df[topic_df["type"] == "query"]

        # Collect unclassified queries.
        if topic_id == -1:
            continue

        # Get topic information.
        topic_dict = topic_labels.get(
            topic_id, {"topic_title": "Unknown", "topic_summary": ""}
        )

        # Get topic samples.
        topic_samples_slice = only_queries[["text", "datetime"]].head(20)
        string_topic_samples = [
            {
                "query_text": str(sample["text"]),
                "query_datetime_utc": str(sample["datetime"]),
            }
            for sample in topic_samples_slice.to_dict(orient="records")
        ]

        # Create the `Topic` object.
        topic = Topic(
            topic_id=int(topic_id),
            topic_name=topic_dict["topic_title"],
            topic_popularity=len(only_queries),
            topic_samples=string_topic_samples,
            topic_summary=topic_dict["topic_summary"],
        )
        topics_list.append(topic)

    # Sort topics by popularity.
    topics_list = sorted(topics_list, key=lambda x: -x.topic_popularity)

    # Prepare `TopicsData` object.
    topics_data = TopicsData(
        data=topics_list,
        refreshTimeStamp=datetime.now(timezone.utc).isoformat(),
        status="completed",
    )

    return topics_data


async def topic_model_queries(
    *,
    content_data: list[BokehContentItem],
    query_data: list[UserQuery],
    workspace_id: int,
) -> tuple[TopicsData, pd.DataFrame]:
    """Perform topic modeling on user queries and content data.

    Parameters
    ----------
    content_data
        A list of `BokehContentItem` objects containing content data.
    query_data
        A list of `UserQuery` objects containing the raw queries and their datetime
        stamps.
    workspace_id
        The ID of the workspace.

    Returns
    -------
    tuple[TopicsData, pd.DataFrame]
        A tuple containing `TopicsData` objects for the frontend and a DataFrame with
        embeddings.
    """

    if not query_data:
        logger.warning("No queries to cluster")
        return (
            TopicsData(
                data=[],
                error_message="No queries to cluster",
                failure_step="Run topic modeling",
                refreshTimeStamp=datetime.now(timezone.utc).isoformat(),
                status="error",
            ),
            pd.DataFrame(),
        )

    if not content_data:
        logger.warning("No content data to cluster")
        return (
            TopicsData(
                data=[],
                error_message="No content data to cluster",
                failure_step="Run topic modeling",
                refreshTimeStamp=datetime.now(timezone.utc).isoformat(),
                status="error",
            ),
            pd.DataFrame(),
        )

    n_queries = len(query_data)
    n_contents = len(content_data)

    if not sum([n_queries, n_contents]) >= 500:
        logger.warning("Not enough data to cluster")
        return (
            TopicsData(
                data=[],
                error_message="""Not enough data to cluster.
                Please provide at least 500 total queries and content items.""",
                failure_step="Run topic modeling",
                refreshTimeStamp=datetime.now(timezone.utc).isoformat(),
                status="error",
            ),
            pd.DataFrame(),
        )

    # Prepare dataframes.
    results_df = prepare_dataframes(content_data=content_data, query_data=query_data)

    # Generate embeddings.
    embeddings = generate_embeddings(texts=results_df["text"].tolist())

    # Fit the BERTopic model.
    topic_model = fit_topic_model(
        embeddings=embeddings, texts=results_df["text"].tolist()
    )

    # Transform documents to get topics and probabilities.
    topics, _ = topic_model.transform(results_df["text"], embeddings)
    results_df["topic_id"] = topics

    # Add reduced embeddings (for visualization).
    add_reduced_embeddings(results_df=results_df, topic_model=topic_model)

    # Generate topic labels using LLM or alternative method.
    topic_labels = await generate_topic_labels_async(
        results_df=results_df, topic_model=topic_model, workspace_id=workspace_id
    )

    # Add topic titles to the dataFrame.
    results_df["topic_title"] = results_df.apply(
        lambda row: get_topic_title(row=row, topic_labels=topic_labels), axis=1
    )

    # Prepare `TopicsData` for frontend.
    topics_data = prepare_topics_data(results_df=results_df, topic_labels=topic_labels)

    return topics_data, results_df
