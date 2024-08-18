import io
from io import BytesIO

from google.cloud import speech
from gtts import gTTS

from ..config import BUCKET_NAME
from ..llm_call.llm_prompts import IdentifiedLanguage
from ..utils import generate_signed_url, setup_logger, upload_file_to_gcs
from .utils import get_gtts_lang_code

logger = setup_logger("Voice API")


async def speech_to_text(audio_filename: str, language_code: str = "en-US") -> str:
    """
    Converts the provided audio file to text using Google's Speech-to-Text API.
    """
    logger.info(
        f"""Starting transcription for {audio_filename}
        with language code {language_code}."""
    )

    try:
        client = speech.SpeechClient()

        with io.open(audio_filename, "rb") as audio_file:
            content = audio_file.read()

        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=language_code,
        )

        response = client.recognize(config=config, audio=audio)

        transcript = ""
        for result in response.results:
            transcript += result.alternatives[0].transcript

        logger.info(f"Transcription completed successfully for {audio_filename}.")
        return transcript

    except Exception as e:
        error_msg = f"Failed to transcribe {audio_filename}: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


async def generate_speech(
    text: str,
    language: IdentifiedLanguage | None,
    destination_blob_name: str = "response.mp3",
) -> str:
    """
    Converts the provided text to speech and saves it as an mp3 file on
    Google cloud storage
    """
    if language is None:
        error_msg = "Language must be provided to generate speech."
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        lang = get_gtts_lang_code(language)
        tts = gTTS(text=text, lang=lang)

        mp3_file = BytesIO()
        tts.write_to_fp(mp3_file)
        content_type = "audio/mpeg"

        await upload_file_to_gcs(
            BUCKET_NAME, mp3_file, destination_blob_name, content_type
        )

        signed_url = await generate_signed_url(BUCKET_NAME, destination_blob_name)

        logger.info(
            f"Speech generated successfully. Saved to {destination_blob_name} in GCS."
        )
        return signed_url

    except Exception as e:
        error_msg = f"Failed to generate speech: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e
