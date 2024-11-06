import pytest
from fastapi.testclient import TestClient

from ..app.schemas import IdentifiedLanguage


class TestTranscribeEndpoint:

    @pytest.mark.parametrize(
        "file_path, expected_keywords, expected_language, expected_status_code",
        [
            (
                "tests/data/test.mp3",
                ["STT", "test", "external"],
                "en",
                200,
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
                404,
                "File not found.",
            ),
            (
                "tests/data/corrupted_file.mp3",
                500,
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

        response = client.post("/transcribe", json={"stt_file_path": file_path})
        assert response.status_code == expected_status_code
        assert response.json()["error"] == expected_detail


class TestSynthesizeEndpoint:

    @pytest.mark.parametrize(
        "text, language, expected_status_code, expected_content_type",
        [
            (
                "Hello, this is a test.",
                IdentifiedLanguage.ENGLISH,
                200,
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

        response = client.post("/synthesize", json={"text": text, "language": language})
        assert response.status_code == expected_status_code
        assert response.headers["content-type"] == expected_content_type

    @pytest.mark.parametrize(
        "text, language, expected_status_code, expected_detail",
        [
            (
                "",
                IdentifiedLanguage.ENGLISH,
                400,
                "Text input cannot be empty.",
            ),
            (
                "This is a test.",
                IdentifiedLanguage.UNSUPPORTED,
                400,
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

        response = client.post("/synthesize", json={"text": text, "language": language})
        assert response.status_code == expected_status_code
        assert response.json()["error"] == expected_detail
