import io
from io import BytesIO

from google.cloud import speech, texttospeech

from ...config import GCS_SPEECH_BUCKET
from ...llm_call.llm_prompts import IdentifiedLanguage
from ...utils import (
    generate_public_url,
    generate_random_filename,
    get_file_extension_from_mime_type,
    setup_logger,
    upload_file_to_gcs,
)
from .utils import convert_audio_to_wav, get_gtts_lang_code_and_model

logger = setup_logger("Voice API")


async def transcribe_audio(audio_file: io.BytesIO) -> str:
    """
    Converts the provided audio byte stream to text using Google's Speech-to-Text API.

    The function ensures that the audio stream is converted to the correct WAV format
    (16-bit PCM, mono, 16kHz) if needed, and then sends it to Google's Speech-to-Text
    API for transcription. It returns the transcribed text if successful.
    """
    logger.info("Starting transcription from byte stream.")

    try:
        wav_file = convert_audio_to_wav(audio_file)
        client = speech.SpeechClient()

        audio_content = wav_file.read()
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",  # Checkout language codes here:
            # https://cloud.google.com/speech-to-text/docs/languages
        )

        response = client.recognize(config=config, audio=audio)

        transcript = ""
        for result in response.results:
            transcript += result.alternatives[0].transcript

        logger.info("Transcription completed successfully from byte stream.")
        return transcript

    except Exception as e:
        error_msg = f"Failed to transcribe audio stream: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


async def generate_tts_on_gcs(
    text: str,
    language: IdentifiedLanguage | None,
) -> str:
    """
    Converts the provided text to speech using the specified voice model
    and saves it as an mp3 file on Google Cloud Storage using Google Text-to-Speech.
    """
    if language is None:
        error_msg = "Language must be provided to generate speech."
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        client = texttospeech.TextToSpeechClient()

        lang, voice_model = get_gtts_lang_code_and_model(language)

        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code=lang,
            name=f"{lang}-{voice_model}",
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        mp3_file = BytesIO(response.audio_content)
        content_type = "audio/mpeg"

        file_extension = get_file_extension_from_mime_type(content_type)
        unique_filename = generate_random_filename(file_extension)

        destination_blob_name = f"tts-voice-notes/{unique_filename}"

        await upload_file_to_gcs(
            GCS_SPEECH_BUCKET, mp3_file, destination_blob_name, content_type
        )

        public_url = await generate_public_url(GCS_SPEECH_BUCKET, destination_blob_name)

        logger.info(
            f"Speech generated successfully. Saved to {destination_blob_name} in GCS."
        )
        return public_url

    except Exception as e:
        error_msg = f"Failed to generate speech: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e
