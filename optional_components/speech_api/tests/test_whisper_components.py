import pytest

from ..app.voice_components import transcribe_audio


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
