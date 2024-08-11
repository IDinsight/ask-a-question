import pytest

from core_backend.app.llm_call.llm_prompts import IdentifiedLanguage
from core_backend.app.voice_api.voice_components import generate_speech


class TestGenerateSpeech:
    @pytest.mark.parametrize(
        "language, text, blob_name",
        [
            (
                IdentifiedLanguage.ENGLISH,
                "Hello, this is a test.",
                "test-stt-voice-notes/voice_note1.mp3",
            ),
            (
                IdentifiedLanguage.SWAHILI,
                "Habari, hii ni jaribio.",
                "test-stt-voice-notes/voice_note2.mp3",
            ),
            (
                IdentifiedLanguage.HINDI,
                "नमस्ते, यह एक परीक्षण है।",
                "test-stt-voice-notes/voice_note3.mp3",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_generate_speech_success(
        self,
        language: IdentifiedLanguage,
        text: str,
        blob_name: str,
    ) -> None:
        dummy_url = "http://example.com/signed-url"

        signed_url = await generate_speech(text, language, blob_name)
        assert signed_url == dummy_url

    @pytest.mark.parametrize(
        "text, language, blob_name",
        [
            ("", IdentifiedLanguage.ENGLISH, "test-stt-voice-notes/voice_note1.mp3"),
            (
                "Hello",
                IdentifiedLanguage.UNSUPPORTED,
                "test-stt-voice-notes/voice_note2.mp3",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_generate_speech_failure(
        self,
        text: str,
        blob_name: str,
        language: IdentifiedLanguage,
    ) -> None:

        with pytest.raises(ValueError):
            await generate_speech(text, language, blob_name)
