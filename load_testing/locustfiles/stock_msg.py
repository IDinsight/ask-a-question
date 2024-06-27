import os
import json

from locust import HttpUser, task

class APIUser(HttpUser):
    @task
    def ask_a_question(
        self,
        endpoint="llm-response",
        question="Is this great content?",
        local=False,
    ):  # If testing locally, set to True to ignore SSL verification
        """Sends a question to the API.

        This task sends the same question repeatedly.

        The endpoint is the API endpoint to send the question to. 
        Default is "llm-response".
        """
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('AAQ_API_KEY')}",
        }
        data = {"query_text": question, "query_metadata": {}}
        self.client.post(
            endpoint, data=json.dumps(data), headers=headers, verify=not local
        )
