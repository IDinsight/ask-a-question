from unittest.mock import MagicMock, patch

import pytest

from core_backend.app.llm_call.llm_prompts import IdentifiedLanguage
from core_backend.app.voice_api.voice_components import generate_speech


class TestGenerateSpeech:
    @pytest.mark.parametrize(
        "language, text",
        [
            (IdentifiedLanguage.ENGLISH, "Hello, this is a test."),
            (IdentifiedLanguage.SWAHILI, "Habari, hii ni jaribio."),
            (IdentifiedLanguage.HINDI, "नमस्ते, यह एक परीक्षण है।"),
        ],
    )
    @pytest.mark.asyncio
    async def test_generate_speech_success(
        self, language: IdentifiedLanguage, text: str, mock_gtts: MagicMock
    ) -> None:
        save_path = "test_audio.mp3"

        with patch("core_backend.app.voice_api.voice_components.gTTS", mock_gtts):
            tts_file_path = await generate_speech(text, language, save_path)
            assert tts_file_path == save_path

    @pytest.mark.parametrize(
        "text, language",
        [
            ("", IdentifiedLanguage.ENGLISH),
            ("Hello", IdentifiedLanguage.UNSUPPORTED),
        ],
    )
    @pytest.mark.asyncio
    async def test_generate_speech_failure(
        self,
        text: str,
        language: IdentifiedLanguage,
    ) -> None:
        save_path = "test_audio.mp3"

        with pytest.raises(ValueError):
            await generate_speech(text, language, save_path)
