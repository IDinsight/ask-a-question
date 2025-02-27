"""This module contains tests for the speech API endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from ..app.schemas import IdentifiedLanguage


class TestTranscribeEndpoint:
    """Tests for the transcribe endpoint."""

    @pytest.mark.parametrize(
        "file_path, expected_keywords, expected_language, expected_status_code",
        [
            (
                "tests/data/test.mp3",
                ["STT", "test", "external"],
                "en",
                status.HTTP_200_OK,
            ),
        ],
    )
    def test_transcribe_audio_success(
        self,
        file_path: str,
        expected_keywords: str,
        expected_language: str,
        expected_status_code: int,
        client: TestClient,
    ) -> None:
        """Test the transcribe audio endpoint.

        Parameters
        ----------
        file_path
            The file path to the audio file.
        expected_keywords
            The expected keywords in the transcription.
        expected_language
            The expected language of the transcription.
        expected_status_code
            The expected status code of the response.
        client
            The test client.
        """

        response = client.post("/transcribe", json={"stt_file_path": file_path})
        assert response.status_code == expected_status_code
        assert response.json()["text"] != ""
        for keyword in expected_keywords:
            assert keyword in response.json()["text"]
        assert response.json()["language"] == expected_language

    @pytest.mark.parametrize(
        "file_path, expected_status_code, expected_detail",
        [
            (
                "tests/data/non_existent_audio.wav",
                status.HTTP_404_NOT_FOUND,
                "File not found.",
            ),
            (
                "tests/data/corrupted_file.mp3",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "An unexpected error occurred.",
            ),
        ],
    )
    def test_transcribe_audio_errors(
        self,
        file_path: str,
        expected_status_code: int,
        expected_detail: str,
        client: TestClient,
    ) -> None:
        """Test the transcribe audio endpoint errors.

        Parameters
        ----------
        file_path
            The file path to the audio file.
        expected_status_code
            The expected status code of the response.
        expected_detail
            The expected detail of the error.
        client
            The test client.
        """

        response = client.post("/transcribe", json={"stt_file_path": file_path})
        assert response.status_code == expected_status_code
        assert response.json()["error"] == expected_detail


class TestSynthesizeEndpoint:
    """Tests for the synthesize endpoint."""

    @pytest.mark.parametrize(
        "text, language, expected_status_code, expected_content_type",
        [
            (
                "Hello, this is a test.",
                IdentifiedLanguage.ENGLISH,
                status.HTTP_200_OK,
                "audio/wav",
            ),
        ],
    )
    def test_synthesize_speech_success(
        self,
        text: str,
        language: IdentifiedLanguage,
        expected_status_code: int,
        expected_content_type: str,
        client: TestClient,
    ) -> None:
        """Test the synthesize speech endpoint.

        Parameters
        ----------
        text
            The text to be synthesized.
        language
            The language of the text to be synthesized.
        expected_status_code
            The expected status code of the response.
        expected_content_type
            The expected content type of the response.
        client
            The test client.
        """

        response = client.post("/synthesize", json={"text": text, "language": language})
        assert response.status_code == expected_status_code
        assert response.headers["content-type"] == expected_content_type

    @pytest.mark.parametrize(
        "text, language, expected_status_code, expected_detail",
        [
            (
                "",
                IdentifiedLanguage.ENGLISH,
                status.HTTP_400_BAD_REQUEST,
                "Text input cannot be empty.",
            ),
            (
                "This is a test.",
                IdentifiedLanguage.UNSUPPORTED,
                status.HTTP_400_BAD_REQUEST,
                "An unexpected error occurred.",
            ),
        ],
    )
    def test_synthesize_speech_errors(
        self,
        text: str,
        language: IdentifiedLanguage,
        expected_status_code: int,
        expected_detail: str,
        client: TestClient,
    ) -> None:
        """Test the synthesize speech endpoint errors.

        Parameters
        ----------
        text
            The text to be synthesized.
        language
            The language of the text to be synthesized.
        expected_status_code
            The expected status code of the response.
        expected_detail
            The expected detail of the error.
        client
            The test client.
        """

        response = client.post("/synthesize", json={"text": text, "language": language})
        assert response.status_code == expected_status_code
        assert response.json()["error"] == expected_detail
