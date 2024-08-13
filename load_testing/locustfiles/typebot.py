"""
Allows easy testing of TypeBot loads
"""

import json
import logging
import os
import time

from locust import HttpUser, between, task


class TypeBotUser(HttpUser):
    """Class must be a subclass of HttpUser to use Locust. Each @task
    decorator represents a task that a user will perform."""

    # Synthetic users will complete the set of tasks below (starting
    # a conversation and sending a message) every 1-5 seconds
    wait_time = between(1, 5)

    def on_start(self) -> None:
        """Initialize a session token on start."""
        self.start_conversation()

    @task
    def start_conversation(self) -> None:
        """
        Requests a session token from a given TypeBot.
        List of TypeBot IDs can be found in the TypeBot dashboard here:
        https://typebot.idinsight.io/typebots.
        Then navigate to the TypeBot you want to use, go to "Share" and copy
        the ID from the API option.
        """
        typebot_id: str = os.getenv("TYPEBOT_BOT_ID", "")
        typbot_init_endpoint: str = (
            f"viewer/api/v1/typebots/{typebot_id}/startChat"
        )
        response = self.client.post(
            typbot_init_endpoint,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.getenv('TYPEBOT_API_KEY')}",
            },
        )
        self.session_token = response.json()["sessionId"]

    @task
    def send_messages(self) -> None:
        """
        Sends two messages to the TypeBot.
        This requires a session token from the previous step.
        The first message will be empty and the second is a follow-up.
        """
        if not self.session_token:
            # Start a conversation if session token is not available
            self.start_conversation()

        typebot_chat_endpoint: str = (
            f"viewer/api/v1/sessions/{self.session_token}/continueChat"
        )
        messages: list[str] = ["Testing", "Is your content good?", "Good"]

        for message in messages:
            logging.info(f"Sending message: {message}")

            response = self.client.post(
                typebot_chat_endpoint,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {os.getenv('TYPEBOT_API_KEY')}",
                },
                data=json.dumps({"message": message}),
            )
            logging.info(f"Response message {response.json()}")
            time.sleep(3)  # Wait for 3 seconds before sending the next message

        self.session_token = ""  # Reset session token after conversation ends
