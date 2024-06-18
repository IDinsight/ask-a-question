import asyncio
import os
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Union

import boto3
import pandas as pd
import pytest
from dateutil import tz
from httpx import AsyncClient

from core_backend.app.config import (
    LITELLM_MODEL_EMBEDDING,
)
from core_backend.app.question_answer.config import N_TOP_CONTENT_FOR_SEARCH
from core_backend.app.question_answer.schemas import QueryBase
from core_backend.app.utils import setup_logger

logger = setup_logger()


class TestRetrievalPerformance:
    @pytest.fixture(scope="class", autouse=True)
    async def setup(
        self,
        client: AsyncClient,
        fullaccess_token: str,
        content_data_path: str,
        content_data_label_col: str,
        content_data_text_col: str,
        aws_profile: Union[str, None],
    ) -> AsyncGenerator[None, None]:
        """Setup UD rules table"""
        content_df = self.prepare_content_data(
            content_data_path=content_data_path,
            content_data_label_col=content_data_label_col,
            content_data_text_col=content_data_text_col,
            aws_profile=aws_profile,
        )

        n_content = content_df.shape[0]
        logger.info(f"Loading {n_content} content item to vector table...")

        content_ids = []
        for content_title, content_text in zip(
            content_df["content_title"],
            content_df["content_text"],
        ):
            response = await client.post(
                "/content/",
                headers={"Authorization": f"Bearer {fullaccess_token}"},
                json={
                    "content_title": content_title,
                    "content_text": content_text,
                },
            )
            content_ids.append(response.json()["content_id"])
        logger.info(f"Completed loading {n_content} items to content table.")
        yield
        for content_id in content_ids:
            await client.delete(
                f"/content/{content_id}",
                headers={"Authorization": f"Bearer {fullaccess_token}"},
            )

    async def test_retrieval_performance(
        self,
        client: AsyncClient,
        api_key: str,
        validation_data_path: str,
        validation_data_question_col: str,
        validation_data_label_col: str,
        content_data_path: str,
        content_data_label_col: str,
        content_data_text_col: str,
        notification_topic: Union[str, None],
        aws_profile: Union[str, None],
    ) -> None:
        """Test retrieval performance of the system"""
        val_df = await self.generate_retrieval_results(
            client=client,
            api_key=api_key,
            validation_data_path=validation_data_path,
            validation_data_question_col=validation_data_question_col,
            validation_data_label_col=validation_data_label_col,
            aws_profile=aws_profile,
        )

        accuracies = self.get_top_k_accuracies(val_df)
        retrieval_failure_rate = val_df["rank"].isna().mean()

        logger.info(f"\nRetrieval failed on {retrieval_failure_rate:.1%} of queries.")
        logger.info("\n" + self.format_accuracies(accuracies))

        if notification_topic is not None:
            message_dict = self._generate_message(
                accuracies,
                retrieval_failure_rate,
                validation_data_path=validation_data_path,
                validation_data_label_col=validation_data_label_col,
                validation_data_question_col=validation_data_question_col,
                content_data_path=content_data_path,
                content_data_label_col=content_data_label_col,
                content_data_text_col=content_data_text_col,
            )
            self.send_notification(
                message_dict, topic=notification_topic, aws_profile=aws_profile
            )

    def prepare_content_data(
        self,
        content_data_path: str,
        content_data_label_col: str,
        content_data_text_col: str,
        aws_profile: Union[str, None] = None,
    ) -> pd.DataFrame:
        """Prepare content data for loading to content table"""
        if content_data_path.startswith("s3://"):
            storage_options = dict(profile=aws_profile)
        else:
            storage_options = None

        df = pd.read_csv(
            content_data_path,
            storage_options=storage_options,
            nrows=5,
        )
        df["content_id"] = list(range(len(df)))
        df = df.rename(
            columns={
                content_data_label_col: "content_title",
                content_data_text_col: "content_text",
            }
        )
        return df

    async def generate_retrieval_results(
        self,
        client: AsyncClient,
        api_key: str,
        validation_data_path: str,
        validation_data_question_col: str,
        validation_data_label_col: str,
        aws_profile: Union[str, None] = None,
    ) -> pd.DataFrame:
        """Generate retrieval results for all queries in validation data"""
        if validation_data_path.startswith("s3://"):
            storage_options = dict(profile=aws_profile)
        else:
            storage_options = None

        df = pd.read_csv(
            validation_data_path,
            storage_options=storage_options,
        )

        logger.info("Retrieving content for each validation query...")

        tasks = [
            self._call_embeddings_search(
                query_text=query, client=client, api_key=api_key
            )
            for query in df[validation_data_question_col]
        ]
        df["retrieved_content_titles"] = await asyncio.gather(*tasks)

        logger.info("Completed retrieving content for each validation query.")

        def get_rank(row: pd.Series) -> Union[int, None]:
            """Get the rank of label in the retrieved content IDs"""
            label = row[validation_data_label_col]
            ranked_list = row["retrieved_content_titles"]
            try:
                return ranked_list.index(label) + 1
            except ValueError:
                return None

        df["rank"] = df.apply(get_rank, axis=1)
        return df

    async def _call_embeddings_search(
        self,
        query_text: str,
        client: AsyncClient,
        api_key: str,
    ) -> List[str]:
        """Single POST /embeddings-search request"""
        request_json = QueryBase(query_text=query_text).model_dump()
        headers = {"Authorization": f"Bearer {api_key}"}
        response = await client.post(
            "/embeddings-search", json=request_json, headers=headers
        )

        if response.status_code != 200:
            logger.warning("Failed to retrieve content")
            content_titles = []
        else:
            retrieved = response.json()["content_response"]
            content_titles = [
                retrieved[str(i)]["retrieved_title"] for i in range(len(retrieved))
            ]
        return content_titles

    @staticmethod
    def get_top_k_accuracies(
        df: pd.DataFrame,
    ) -> List[float]:
        """Get top K accuracy table for validation results"""
        accuracies = []
        for i in range(1, int(N_TOP_CONTENT_FOR_SEARCH) + 1):
            acc = (df["rank"] <= i).mean()
            accuracies.append(acc)
        return accuracies

    @staticmethod
    def format_accuracies(accuracies: List[float]) -> str:
        """Format list of accuracies into readable string"""
        accuracy_message = "\n".join(
            [
                f"   • Top-{i + 1} accuracy: {acc:.1%}"
                for i, acc in enumerate(accuracies)
            ]
        )
        return accuracy_message

    def _generate_message(
        self,
        accuracies: List[float],
        retrieval_failure_rate: float,
        validation_data_path: str,
        validation_data_question_col: str,
        validation_data_label_col: str,
        content_data_path: str,
        content_data_label_col: str,
        content_data_text_col: str,
    ) -> Dict[str, str]:
        """Generate messages for validation results"""
        ist = tz.gettz("Asia/Kolkata")
        timestamp = datetime.now(tz=ist).strftime("%Y-%m-%d %H:%M:%S IST")

        message = (
            f"Content retrieval validation results\n"
            f"--------------------------------------------\n"
            f"\n"
            f"• Timestamp: {timestamp}\n"
            f"• Dataset:\n"
            f"   • Validation data: {validation_data_path}\n"
            f"      • Question column: {validation_data_question_col}\n"
            f"      • Label column: {validation_data_label_col}\n"
            f"   • Content data: {content_data_path}\n"
            f"      • Text column: {content_data_text_col}\n"
            f"      • Label column: {content_data_label_col}\n"
            f"• Embedding model: {LITELLM_MODEL_EMBEDDING}\n"
            f"• Retrieval failure rate: {retrieval_failure_rate:.1%}\n"
            f"• Top N accuracies:\n" + self.format_accuracies(accuracies)
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
        else:
            message += "\n\nThis test was run outside of Github Actions."

        return {
            "Subject": f"Retrieval validation results ({timestamp})",
            "Message": message,
        }

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
