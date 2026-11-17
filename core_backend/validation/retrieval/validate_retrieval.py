import asyncio
import os
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Union

import boto3
import pandas as pd
from dateutil import tz
from fastapi.testclient import TestClient

from app.core.config import LITELLM_MODEL_EMBEDDING, N_TOP_CONTENT
from app.core.observability import setup_logger
from app.question_answer.schemas import QueryBase

if TYPE_CHECKING:  # Fixture from validation/conftest.py; imported for typing only.
    from validation.conftest import ValidationWorkspace

logger = setup_logger()


def _storage_options(path: str, aws_profile: Union[str, None]) -> Union[dict, None]:
    """fsspec options for reading `path`: the AWS profile for remote paths (e.g.
    s3://...), none for local files (pandas rejects options for those)."""
    return dict(profile=aws_profile) if "://" in path else None


class TestRetrievalPerformance:
    def test_retrieval_performance(
        self,
        client: TestClient,
        validation_data_path: str,
        validation_data_question_col: str,
        validation_data_label_col: str,
        content_data_path: str,
        content_data_label_col: str,
        content_data_text_col: str,
        notification_topic: Union[str, None],
        aws_profile: Union[str, None],
        validation_workspace: "ValidationWorkspace",
    ) -> None:
        """Test retrieval performance of the system"""
        content_df = self.prepare_content_data(
            content_data_path=content_data_path,
            content_data_label_col=content_data_label_col,
            content_data_text_col=content_data_text_col,
            aws_profile=aws_profile,
        )
        self.load_content(
            client,
            access_token=validation_workspace.access_token,
            content_dataframe=content_df,
        )

        val_df = self.generate_retrieval_results(
            client,
            api_key=validation_workspace.api_key,
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
        df = pd.read_csv(
            content_data_path,
            storage_options=_storage_options(content_data_path, aws_profile),
            nrows=5,
        )
        df = df.rename(
            columns={
                content_data_label_col: "content_title",
                content_data_text_col: "content_text",
            }
        )
        return df

    def load_content(
        self,
        client: TestClient,
        access_token: str,
        content_dataframe: pd.DataFrame,
    ) -> None:
        """Load content into the validation workspace through POST /content/, which
        embeds each item the same way production does."""
        n_content = content_dataframe.shape[0]
        logger.info(f"Loading {n_content} content items...")

        for title, text in zip(
            content_dataframe["content_title"], content_dataframe["content_text"]
        ):
            response = client.post(
                "/content/",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"content_text": str(text), "content_title": str(title)},
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"Failed to load content '{title}' "
                    f"(HTTP {response.status_code}): {response.text}"
                )
        logger.info(f"Completed loading {n_content} content items.")

    def generate_retrieval_results(
        self,
        client: TestClient,
        api_key: str,
        validation_data_path: str,
        validation_data_question_col: str,
        validation_data_label_col: str,
        aws_profile: Union[str, None] = None,
    ) -> pd.DataFrame:
        """Generate retrieval results for all queries in validation data"""
        df = pd.read_csv(
            validation_data_path,
            storage_options=_storage_options(validation_data_path, aws_profile),
        )

        logger.info("Retrieving content for each validation query...")

        df = asyncio.run(
            self.retrieve_results(df, client, api_key, validation_data_question_col)
        )

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

    async def call_embeddings_search(
        self,
        query_text: str,
        client: TestClient,
        api_key: str,
    ) -> List[str]:
        """Single POST /search request"""
        request_json = QueryBase(
            query_text=query_text, generate_llm_response=False
        ).model_dump()
        headers = {"Authorization": f"Bearer {api_key}"}
        response = client.post("/search", json=request_json, headers=headers)

        if response.status_code != 200:
            logger.warning("Failed to retrieve content")
            content_titles = []
        else:
            retrieved = response.json()["search_results"]
            content_titles = [retrieved[str(i)]["title"] for i in range(len(retrieved))]
        return content_titles

    async def retrieve_results(
        self,
        df: pd.DataFrame,
        client: TestClient,
        api_key: str,
        validation_data_question_col: str,
    ) -> pd.DataFrame:
        """Asynchronously retrieve similar content for all queries in validation data"""
        tasks = [
            self.call_embeddings_search(query, client, api_key)
            for query in df[validation_data_question_col]
        ]
        df["retrieved_content_titles"] = await asyncio.gather(*tasks)
        return df

    @staticmethod
    def get_top_k_accuracies(
        df: pd.DataFrame,
    ) -> List[float]:
        """Get top K accuracy table for validation results"""
        accuracies = []
        for i in range(1, int(N_TOP_CONTENT) + 1):
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
