"""
Uses Locust to load test the AAQ API for a given URL
"""

import json
import os

import urllib3
from locust import HttpUser, between, task

urllib3.disable_warnings()  # Disable SSL warnings for local testing


class AAQUser(HttpUser):
    """
    Class must be a subclass of HttpUser to use Locust. Each @task
    decorator represents a task that a user will perform.
    """

    # Users will make requests with a wait time between 5 and 15 seconds
    wait_time = between(5, 15)

    @task
    def check_endpoint(
        self,
        endpoint: str = "search",
        question: str = "Is this great content?",
        local: bool = False,
    ) -> (
        None
    ):  # If testing locally, set local to True to ignore SSL verification
        """Sends a question to the API.

        This task sends the same question repeatedly.

        The endpoint is the API endpoint to send the question to.
        Default is "llm-response" but this can be channged to
        "embeddings-search" to test the embeddings search endpoint.
        """
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('AAQ_API_KEY')}",
        }
        data = {
            "query_text": question,
            "generate_llm_response": "true",
            "query_metadata": {},
        }
        self.client.post(
            endpoint, data=json.dumps(data), headers=headers, verify=not local
        )
