import io
from io import BytesIO

from google.cloud import speech, texttospeech

from ..config import BUCKET_NAME
from ..llm_call.llm_prompts import IdentifiedLanguage
from ..utils import generate_signed_url, setup_logger, upload_file_to_gcs
from .utils import convert_mp3_to_wav, get_gtts_lang_code

logger = setup_logger("Voice API")


async def transcribe_audio(audio_filename: str, language_code: str = "en-US") -> str:
    """
    Converts the provided audio file to text using Google's Speech-to-Text API.
    Ensures the audio file meets the required specifications.
    """
    logger.info(f"Starting transcription for {audio_filename}")

    try:
        wav_filename = convert_mp3_to_wav(audio_filename)

        client = speech.SpeechClient()

        with io.open(wav_filename, "rb") as audio_file:
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
    destination_blob_name: str,
) -> str:
    """
    Converts the provided text to speech and saves it as an mp3 file on
    Google Cloud Storage using Google Text-to-Speech.
    """
    if language is None:
        error_msg = "Language must be provided to generate speech."
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:

        client = texttospeech.TextToSpeechClient()

        lang = get_gtts_lang_code(language)

        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code=lang,
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        mp3_file = BytesIO(response.audio_content)
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
