from io import BytesIO

import pytest

from ..app.schemas import IdentifiedLanguage
from ..app.voice_components import synthesize_speech, transcribe_audio


@pytest.mark.asyncio
class TestTranscribeAudio:

    @pytest.mark.parametrize(
        "file_path, expected_keywords, expected_language, expected_exception",
        [
            ("tests/data/harvard.wav", ["stale", "smell", "old beer"], "en", None),
            ("tests/data/swahili_test.mp3", ["Nairobi", "juhadi milima"], "sw", None),
            # base model does not properly transcribe this, have to use small model
            # ("tests/data/hindi_test.wav", ["बंगाल", "खाड़ी", "कोलकाता"], "hi", None),
            ("tests/data/non_existent_audio.wav", [], None, ValueError),
        ],
    )
    async def test_transcribe_audio(
        self,
        file_path: str,
        expected_keywords: list[str],
        expected_language: str | None,
        expected_exception: type[Exception] | None,
    ) -> None:
        if expected_exception:
            with pytest.raises(expected_exception):
                await transcribe_audio(file_path)
        else:
            response = await transcribe_audio(file_path)
            assert response.text != ""
            for keyword in expected_keywords:
                assert keyword in response.text
            assert response.language == expected_language


@pytest.mark.asyncio
class TestSynthesizeSpeech:

    @pytest.mark.parametrize(
        "text, language, expected_exception",
        [
            ("This is a test.", IdentifiedLanguage.ENGLISH, None),
            ("Hii ni jaribio.", IdentifiedLanguage.SWAHILI, None),
            ("ఇది ఒక పరీక్ష", IdentifiedLanguage.UNSUPPORTED, ValueError),
        ],
    )
    async def test_synthesize_speech(
        self,
        text: str,
        language: IdentifiedLanguage,
        expected_exception: type[Exception] | None,
    ) -> None:
        if expected_exception:
            with pytest.raises(expected_exception):
                await synthesize_speech(text, language)
        else:
            result = await synthesize_speech(text, language)
            assert isinstance(result, BytesIO)
            assert len(result.getvalue()) > 0
