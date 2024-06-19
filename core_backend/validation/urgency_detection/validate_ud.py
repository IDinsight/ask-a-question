import asyncio
import json
import os
from datetime import datetime
from typing import AsyncGenerator, Dict, Union

import boto3
import pandas as pd
import pytest
from dateutil import tz
from httpx import AsyncClient

from core_backend.app.config import (
    LITELLM_MODEL_EMBEDDING,
)
from core_backend.app.utils import setup_logger

logger = setup_logger("UDValidation")


class TestUDPerformance:

    @pytest.fixture(scope="class", autouse=True)
    async def setup(
        self,
        client: AsyncClient,
        fullaccess_token: str,
        ud_rules_path: str,
        ud_rules_col: str,
        aws_profile: Union[str, None],
    ) -> AsyncGenerator[None, None]:
        """Setup UD rules table"""
        ud_rules_df = pd.read_csv(
            ud_rules_path,
        )
        ud_rules = ud_rules_df.loc[:, ud_rules_col].to_list()

        urgency_rule_ids = []
        for rule in ud_rules:
            response = await client.post(
                "/urgency-rules/",
                headers={"Authorization": f"Bearer {fullaccess_token}"},
                json={
                    "urgency_rule_text": rule,
                },
            )
            urgency_rule_ids.append(response.json()["urgency_rule_id"])
        yield
        for rule_id in urgency_rule_ids:
            await client.delete(
                f"/urgency-rules/{rule_id}",
                headers={"Authorization": f"Bearer {fullaccess_token}"},
            )

    @pytest.fixture(scope="class", autouse=True)
    def validation_data(
        self,
        validation_data_path: str,
        validation_data_question_col: str,
        validation_data_label_col: str,
        aws_profile: Union[str, None],
    ) -> pd.DataFrame:
        val_df = pd.read_csv(
            validation_data_path,
            usecols=[validation_data_question_col, validation_data_label_col],
        )
        val_df[validation_data_label_col] = val_df[validation_data_label_col].map(
            lambda x: 1 if x == "Yes" else 0
        )
        val_df = val_df.rename(
            columns={
                validation_data_question_col: "question",
                validation_data_label_col: "label",
            }
        )
        return val_df

    async def test_ud_performance(
        self,
        client: AsyncClient,
        validation_data: pd.DataFrame,
        api_key: str,
        notification_topic: Union[str, None],
        aws_profile: Union[str, None],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test UD performance of the system"""
        tasks = [
            self._test_single_query(
                client,
                row,
                api_key,
            )
            for row_idx, row in validation_data.iterrows()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                print("E", end="")
            else:
                print(".", end="")

        print()

        validation_data["predicted"] = results
        metrics = self._calculate_metrics(validation_data)

        print(json.dumps(metrics, indent=2))
        if notification_topic is not None and aws_profile is not None:
            self._notify_results(metrics, notification_topic, aws_profile)

    @staticmethod
    def _calculate_metrics(validation_data: pd.DataFrame) -> Dict[str, float | int]:
        """Calculate metrics for UD performance"""

        total_positives = int(validation_data["label"].sum())
        total_negatives = len(validation_data) - total_positives

        true_positives = int(
            validation_data.loc[validation_data["label"] == 1, "predicted"].sum()
        )
        false_positives = int(
            validation_data.loc[validation_data["label"] == 0, "predicted"].sum()
        )
        true_negatives = total_negatives - false_positives
        false_negatives = total_positives - true_positives

        logger.info(
            (
                f"True positives: {true_positives}\n"
                f"False negatives: {false_negatives}\n"
                f"True negatives: {true_negatives}\n"
                f"False positives: {false_positives}\n"
            )
        )

        predicted_positives = true_positives + false_positives

        precision = (
            true_positives / predicted_positives if predicted_positives > 0 else 0
        )
        recall = true_positives / total_positives if total_positives > 0 else 0

        logger.info(f"Precision: {precision:.1%}\nRecall: {recall:.1%}\n")

        return {
            "true_positives": true_positives,
            "false_negatives": false_negatives,
            "true_negatives": true_negatives,
            "false_positives": false_positives,
            "precision": precision,
            "recall": recall,
        }

    @staticmethod
    async def _test_single_query(
        client: AsyncClient,
        row: pd.Series,
        token: str,
    ) -> int:
        """Test a single query for UD performance"""
        response = await client.post(
            "/urgency-detect",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "message_text": row["question"],
            },
        )
        return response.json()["is_urgent"]

    @staticmethod
    def _make_markdown_table(metrics: Dict[str, float | int]) -> str:
        """Generate markdown table for UD performance"""
        true_positives = metrics["true_positives"]
        false_negatives = metrics["false_negatives"]
        true_negatives = metrics["true_negatives"]
        false_positives = metrics["false_positives"]

        fpr = false_positives / (false_positives + true_negatives)
        fnr = false_negatives / (false_negatives + true_positives)

        table = (
            "|                  | Predicted Positive | Predicted Negative |\n"
            "|------------------|--------------------|--------------------|\n"
            f"| Actual Positive  | {true_positives} | {false_negatives} ({fnr:.1%}) |\n"
            f"| Actual Negative  | {false_positives} ({fpr:.1%})| {true_negatives} |\n"
        )
        return table

    def _notify_results(
        self, metrics: Dict[str, float | int], notification_topic: str, aws_profile: str
    ) -> None:

        ist = tz.gettz("Asia/Kolkata")
        timestamp = datetime.now(tz=ist).strftime("%Y-%m-%d %H:%M:%S IST")

        markdown_table = self._make_markdown_table(metrics)
        metadata = self.get_results_metadata()
        message = markdown_table + "\n\n" + metadata

        message_dict = {
            "Subject": f"UD validation results ({timestamp})",
            "Message": message,
        }

        if notification_topic is not None:
            self.send_notification(
                message_dict, topic=notification_topic, aws_profile=aws_profile
            )

    def get_results_metadata(self) -> str:

        ist = tz.gettz("Asia/Kolkata")
        timestamp = datetime.now(tz=ist).strftime("%Y-%m-%d %H:%M:%S IST")

        message = (
            f"Urgency Detection validation details\n"
            f"--------------------------------------------\n"
            f"\n"
            f"• Timestamp: {timestamp}\n"
            f"• Embedding model: {LITELLM_MODEL_EMBEDDING}\n"
        )

        env_vars = [
            env_var for env_var in os.environ.keys() if env_var.startswith("URGENCY_")
        ]
        for var in env_vars:
            message += f"• {var}: {os.environ.get(var)}\n"

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
        else:
            message += "\n\nThis test was run outside of Github Actions."

        return message

    @staticmethod
    def send_notification(
        message_dict: Dict[str, str],
        topic: str,
        aws_profile: Union[str, None] = None,
    ) -> None:
        """
        Function to send notification
        """
        boto3.setup_default_session(profile_name=aws_profile)
        sns = boto3.client("sns")

        sns.publish(
            TopicArn=topic,
            **message_dict,
        )
        print("Successfully sent message to SNS topic")
