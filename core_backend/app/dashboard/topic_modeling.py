"""
This module contains the main function for the topic modelling pipeline.
"""

import asyncio
from datetime import datetime, timezone
from typing import Tuple

import pandas as pd
from bertopic import BERTopic
from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer
from umap import UMAP

from ..llm_call.dashboard import generate_topic_label
from ..utils import setup_logger
from .config import TOPIC_MODELING_CONTEXT
from .schemas import InsightContent, Topic, TopicsData, UserQuery

logger = setup_logger()


async def topic_model_queries(
    user_id: int, query_data: list[UserQuery], content_data: list[InsightContent]
) -> Tuple[TopicsData, pd.DataFrame]:
    """Turn a list of raw queries, run them through a BERTopic pipeline
    and return the Data for the front end.

    Parameters
    ----------
    user_id : int
        The ID of the user making the request.
    data
        A list of UserQuery objects containing the raw queries and their
    corresponding datetime stamps.

    Returns
    -------
    list[tuple[str, datetime]]
        A list of tuples where each tuple contains the raw query
    (query_text) and its corresponding datetime stamp (query_datetime_utc).
    """
    if not query_data:
        logger.info("No queries to cluster")
        return TopicsData(refreshTimeStamp="", data=[], embeddings_dataframe={})

    if not content_data:
        logger.info("No content data to cluster")
        return TopicsData(refreshTimeStamp="", data=[], embeddings_dataframe={})

    # Set up the dataframes
    content_df = pd.DataFrame.from_records([x.model_dump() for x in content_data])
    content_df["type"] = "content"

    query_df = pd.DataFrame.from_records([x.model_dump() for x in query_data])
    query_df["type"] = "query"
    query_df["query_datetime_utc"] = query_df["query_datetime_utc"].astype(str)

    # Prepare datetimes column
    combined_datetimes = query_df["query_datetime_utc"].tolist() + [""] * len(
        content_df
    )
    # Combine all the text together and create a uniform DataFrame
    full_docs = query_df["query_text"].tolist() + content_df["content_text"].tolist()
    results_df = pd.DataFrame(full_docs, columns=["text"])
    results_df["type"] = query_df["type"].tolist() + content_df["type"].tolist()
    results_df["datetime"] = combined_datetimes

    # Prepare BertTopic to model the data
    sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = sentence_model.encode(results_df["text"], show_progress_bar=False)
    umap_model = UMAP(n_components=2, n_neighbors=15, min_dist=0.0, metric="cosine")
    hdbscan_model = HDBSCAN(
        min_cluster_size=20,
        metric="euclidean",
        cluster_selection_method="eom",  # Choosing 'leaf' -> smaller cluster
        prediction_data=True,
    )

    # Fit the model
    topic_model = BERTopic(hdbscan_model=hdbscan_model, umap_model=umap_model).fit(
        full_docs, embeddings
    )
    results_df["topic_id"], results_df["probs"] = topic_model.transform(
        results_df["text"], embeddings
    )

    # Extract reduced embeddings from BertTOPIC model and add to results_df
    reduced_embeddings = topic_model.umap_model.embedding_
    results_df["x_coord"] = reduced_embeddings[:, 0]
    results_df["y_coord"] = reduced_embeddings[:, 1]

    # Queries with low probability of being in a cluster assigned -1

    tasks = []
    topic_ids = []

    for topic_id, topic_df in results_df.groupby("topic_id"):
        # Only include the top 5 samples for each topic and only queries
        topic_queries = topic_df[topic_df["type"] == "query"]
        selected_queries = topic_queries["text"][:5].tolist()
        tasks.append(
            generate_topic_label(
                topic_id,
                user_id,
                TOPIC_MODELING_CONTEXT,
                selected_queries,
            )
        )
        topic_ids.append(topic_id)

    topic_dicts = await asyncio.gather(*tasks)
    topic_labels = {
        topic_id: topic_dict for topic_id, topic_dict in zip(topic_ids, topic_dicts)
    }

    def get_topic_title(x: int) -> str:
        """Get the topic title from the topic_id"""

        if x == -1:
            return "Unclassified"
        else:
            return topic_labels.get(x, {}).get("topic_title", "Unknown Topic")

    # The topic_dicts are a list of dictionaries containing the topic title and summary
    # Add the title as a column in the results_df
    results_df["topic_title"] = results_df["topic_id"].apply(get_topic_title)
    # Manually set all "Content" type to "Unclassified"
    results_df.loc[results_df["type"] == "content", "topic_title"] = "Content"

    topic_data = []

    for topic_id, topic_df in results_df.groupby("topic_id"):
        topic_dict = topic_labels.get(
            topic_id, {"topic_title": "Unknown", "topic_summary": ""}
        )
        only_queries = topic_df[topic_df["type"] == "query"]
        topic_samples_slice = only_queries[["text", "datetime"]][:20]
        string_topic_samples = [
            {
                "query_text": str(sample["text"]),
                "query_datetime_utc": str(sample["datetime"]),
            }
            for sample in topic_samples_slice.to_dict(orient="records")
        ]
        topic_data.append(
            Topic(
                topic_id=int(topic_id),
                topic_name=topic_dict["topic_title"],
                topic_summary=topic_dict["topic_summary"],
                topic_samples=string_topic_samples,
                topic_popularity=len(only_queries),
            )
        )

    topic_data = sorted(
        topic_data, key=lambda x: (x.topic_id == -1, -x.topic_popularity)
    )

    topics_data = TopicsData(
        refreshTimeStamp=datetime.now(timezone.utc).isoformat(),
        data=topic_data,
    )

    return topics_data, results_df
