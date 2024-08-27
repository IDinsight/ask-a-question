"""
This module contains the main function for the topic modelling pipeline.
"""

import asyncio

import pandas as pd
from bertopic import BERTopic
from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer

from ..llm_call.dashboard import generate_topic_label
from .config import TOPIC_MODELING_CONTEXT
from .schemas import Topic, TopicsData, UserQuery


async def topic_model_queries(user_id: int, data: list[UserQuery]) -> TopicsData:
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

    if not data:
        return TopicsData(n_topics=0, topics=[], unclustered_queries=[])

    # Establish Query DataFrame
    query_df = pd.DataFrame.from_records([x.model_dump() for x in data])
    docs = query_df["query_text"].tolist()

    sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = sentence_model.encode(docs, show_progress_bar=False)

    # Create topic model
    hdbscan_model = HDBSCAN(
        min_cluster_size=15,
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )
    topic_model = BERTopic(hdbscan_model=hdbscan_model).fit(docs, embeddings)
    query_df["topic_id"], query_df["probs"] = topic_model.transform(docs, embeddings)

    unclustered_examples = list(
        query_df.loc[
            query_df["topic_id"] == -1, ["query_text", "query_datetime_utc"]
        ].itertuples(index=False, name=None)
    )

    query_df = query_df.loc[query_df["probs"] > 0.8]

    _idx = 0
    topic_data = []
    tasks = []
    for _, topic_df in query_df.groupby("topic_id"):
        topic_samples = topic_df[["query_text", "query_datetime_utc"]][:5]
        tasks.append(
            generate_topic_label(
                user_id,
                TOPIC_MODELING_CONTEXT,
                topic_samples["query_text"].tolist(),
            )
        )

    topics = await asyncio.gather(*tasks)
    print("Topic:", topics, "\n\n")
    for topic, (topic_id, topic_df) in zip(topics, query_df.groupby("topic_id")):
        topic_samples = topic_df[["query_text", "query_datetime_utc"]][:5]
        topic_data.append(
            Topic(
                topic_id=int(topic_id) if isinstance(topic_id, int) else -1,
                topic_name=topic,
                topic_samples=topic_samples.values.tolist(),
                topic_popularity=len(topic_df),
            )
        )

    return TopicsData(
        n_topics=len(topic_data),
        topics=topic_data,
        unclustered_queries=unclustered_examples,
    )
