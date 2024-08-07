# from unittest.mock import MagicMock, patch

# import pytest
# from fastapi.testclient import TestClient


# @pytest.fixture
# def mock_whisper():
#     with patch("voice_api.app.voice_components.whisper") as mock_whisper:
#         mock_whisper.load_model = MagicMock(return_value="mocked_model")
#         yield mock_whisper


# def test_root_endpoint(whisper_client: TestClient, mock_whisper) -> None:
#     response = whisper_client.get("/")
#     assert response.status_code == 200
#     assert response.json() == {"message": "Welcome to the Whisper Service"}
