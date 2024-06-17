import asyncio
from pathlib import Path
from typing import Dict, Hashable, List

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from core_backend.app.database import get_async_session
from core_backend.app.llm_call.entailment import detect_urgency
from core_backend.app.urgency_rules.models import (
    UrgencyRuleDB,
    get_cosine_distances_from_rules,
    get_urgency_rules_from_db,
    save_urgency_rule_to_db,
)
from core_backend.app.urgency_rules.schemas import UrgencyRuleCreate

PATH_TO_MESSAGES = Path(__file__).parents[3] / "data/mc_urgency_message_data.csv"
PATH_TO_RULES = Path(__file__).parents[3] / "data/mc_urgency_rules.csv"


async def load_urgency_rules(path_to_rules: Path) -> List[UrgencyRuleDB]:
    """
    Load urgency rules from a CSV file and save them to the database
    """

    rules_df = pd.read_csv(path_to_rules)

    tasks = []
    for _i, row in rules_df.iterrows():
        async for session in get_async_session():
            rule = UrgencyRuleCreate(urgency_rule_text=row.iloc[0])
            tasks.append(save_urgency_rule_to_db(1, rule, session))

    results = await asyncio.gather(*tasks)
    return results


async def get_cosine_results_for_message(
    session: AsyncSession, _i: Hashable, row: pd.Series
) -> dict:
    """
    Get cosine distances for a message
    """
    result = await get_cosine_distances_from_rules(1, row.loc["Question"], session)
    print(".", end="", sep="", flush=True)
    return {
        "idx": _i,
        "message": row.loc["Question"],
        "urgency_label": row.loc["Urgent_bool"],
        "results": result,
    }


# --- Cosine scoring ---
async def cosine_distance_scoring() -> List[Dict]:
    """
    Calculate cosine distances for all messages
    """
    messages_df = pd.read_csv(PATH_TO_MESSAGES)
    messages_df.loc[:, "Urgent_bool"] = messages_df.loc[:, "Urgent"].map(
        lambda x: True if x == "Yes" else False
    )

    tasks = []

    async for session in get_async_session():
        for _i, row in messages_df.iterrows():
            tasks.append(get_cosine_results_for_message(session, _i, row))
        cosine_distance_results = await asyncio.gather(*tasks)

    return cosine_distance_results


def process_cosine_results(message_results_dict: dict) -> None:
    """
    Process cosine distance results
    """
    processed_results = []
    for message_result in message_results_dict:
        min_distance = 100
        min_rule = ""
        for rule_result in message_result["results"].values():
            if min_distance > rule_result["distance"]:
                min_distance = rule_result["distance"]
                min_rule = rule_result["urgency_rule"]

        processed_results.append(
            {
                "message": message_result["message"],
                "urgency_label": message_result["urgency_label"],
                "min_distance": min_distance,
                "min_rule": min_rule,
            }
        )

    pd.DataFrame(processed_results).to_csv("processed_results.csv")


# --- LLM Scoring ---


async def llm_scoring_for_message(row: pd.Series, rules: List[UrgencyRuleDB]) -> Dict:
    """
    Calculate LLM scores for a message
    """
    tasks = []
    for rule in rules:
        tasks.append(
            detect_urgency(
                urgency_rule=rule.urgency_rule_text,
                message=row["Question"],
                metadata={},
            )
        )

    results = await asyncio.gather(*tasks)
    return {
        "message": row["Question"],
        "urgency_label": row["Urgent_bool"],
        "results": results,
    }


async def llm_scoring() -> List[Dict]:
    """
    Calculate LLM scores for all messages
    """
    messages_df = pd.read_csv(PATH_TO_MESSAGES)
    messages_df.loc[:, "Urgent_bool"] = messages_df.loc[:, "Urgent"].map(
        lambda x: True if x == "Yes" else False
    )

    tasks = []
    async for asession in get_async_session():
        rules = await get_urgency_rules_from_db(user_id=1, asession=asession)
        for _i, row in messages_df.iterrows():
            tasks.append(llm_scoring_for_message(row, rules))

    llm_results = await asyncio.gather(*tasks)
    return llm_results


def process_llm_results(llm_results: List[Dict]) -> None:
    """
    Process LLM results
    """
    processed_results = []
    for message_result in llm_results:
        max_probability = 0
        max_rule = ""
        for rule_result in message_result["results"]:
            if max_probability < rule_result["probability"]:
                max_probability = rule_result["probability"]
                max_rule = rule_result["statement"]

        processed_results.append(
            {
                "message": message_result["message"],
                "urgency_label": message_result["urgency_label"],
                "max_rule": max_rule,
                "max_probability": max_probability,
            }
        )

    pd.DataFrame(processed_results).to_csv("processed_results-llm.csv")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    rules = loop.run_until_complete(load_urgency_rules(PATH_TO_RULES))
    print(f"Loaded {len(rules)} rules")

    # print("Running cosine distance scoring")

    # cosine_distance_results = loop.run_until_complete(cosine_distance_scoring())
    # print(f"Calculated cosine distances for {len(cosine_distance_results)} messages")

    # process_cosine_results(cosine_distance_results)

    print("Running LLM scoring")
    llm_results = loop.run_until_complete(llm_scoring())
    print(f"Calculated LLM scores for {len(llm_results)} messages")
    process_llm_results(llm_results)
    loop.close()
