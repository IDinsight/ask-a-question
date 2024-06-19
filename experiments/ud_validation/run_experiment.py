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
BATCH_SIZE = 50


async def my_save_urgency_rule_to_db(
    user_id: int, rule: UrgencyRuleCreate, session: AsyncSession
) -> UrgencyRuleDB:
    """
    We create a wrapper since we are gathering the async tasks outside
    of the context manager. This avoids connections being left open.
    """
    result = await save_urgency_rule_to_db(user_id, rule, session)
    await session.close()

    return result


async def load_urgency_rules(path_to_rules: Path) -> List[UrgencyRuleDB]:
    """
    Load urgency rules from a CSV file and save them to the database
    """

    rules_df = pd.read_csv(path_to_rules)

    tasks = []
    for _i, row in rules_df.iterrows():
        async for session in get_async_session():
            rule = UrgencyRuleCreate(urgency_rule_text=row.iloc[0])
            tasks.append(my_save_urgency_rule_to_db(1, rule, session))

    results = await asyncio.gather(*tasks)

    return results


# --- Cosine scoring ---


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


def process_cosine_results(message_results_list: List[Dict]) -> None:
    """
    Process cosine distance results
    """
    processed_results = []
    for message_result in message_results_list:
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

    pd.DataFrame(processed_results).to_csv(
        Path(__file__).parent / "processed_results-cosine.csv"
    )


# --- LLM Scoring ---


async def llm_scoring_for_message(row: pd.Series, rules: List[str]) -> Dict:
    """
    Calculate LLM scores for a message
    """
    result = await detect_urgency(
        urgency_rules=rules,
        message=row["Question"],
        metadata={},
    )

    result.update(
        {
            "message": row["Question"],
            "urgency_label": row["Urgent_bool"],
        }
    )
    return result


async def llm_scoring() -> List[Dict]:
    """
    Calculate LLM scores for all messages
    """
    messages_df = pd.read_csv(PATH_TO_MESSAGES)
    messages_df.loc[:, "Urgent_bool"] = messages_df.loc[:, "Urgent"].map(
        lambda x: True if x == "Yes" else False
    )

    async for asession in get_async_session():
        rules = await get_urgency_rules_from_db(user_id=1, asession=asession)
        rules_list = [rule.urgency_rule_text for rule in rules]

        llm_results = []
        for start in range(0, len(messages_df), BATCH_SIZE):
            tasks = []
            print(".", end="", sep="", flush=True)
            end = min(start + BATCH_SIZE, len(messages_df))
            sub_df = messages_df.iloc[start:end, :]
            for _i, row in sub_df.iterrows():
                tasks.append(llm_scoring_for_message(row, rules_list))

            sub_llm_results = await asyncio.gather(*tasks)
            llm_results.extend(sub_llm_results)

    return llm_results


def process_llm_results(llm_results: List[Dict]) -> None:
    """
    Process LLM results
    """
    pd.DataFrame(llm_results).to_csv(
        Path(__file__).parent / "processed_results-cosine.csv"
    )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    rules = loop.run_until_complete(load_urgency_rules(PATH_TO_RULES))
    print(f"Loaded {len(rules)} rules")

    print("Running cosine distance scoring")
    cosine_distance_results = loop.run_until_complete(cosine_distance_scoring())
    print(f"Calculated cosine distances for {len(cosine_distance_results)} messages")
    process_cosine_results(cosine_distance_results)

    print("Running LLM scoring")
    llm_results = loop.run_until_complete(llm_scoring())
    print(f"Calculated LLM scores for {len(llm_results)} messages")
    process_llm_results(llm_results)

    loop.close()
