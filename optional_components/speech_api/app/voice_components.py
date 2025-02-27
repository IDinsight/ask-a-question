"""This module contains the voice components for the speech API."""

import os
import wave
from io import BytesIO

import whisper
from piper.voice import PiperVoice

from .config import (
    ENG_MODEL_NAME,
    PIPER_MODELS_DIR,
    PREFERRED_MODEL,
    SWAHILI_MODEL_NAME,
    WHISPER_MODEL_DIR,
)
from .schemas import IdentifiedLanguage, TranscriptionResponse
from .utils import setup_logger

logger = setup_logger(name="Whisper ASR")


async def synthesize_speech(*, language: IdentifiedLanguage, text: str) -> BytesIO:
    """Synthesize speech from text using the Piper TTS model and returns it as a
    `BytesIO` stream.

    Parameters
    ----------
    language
        The language of the text to be synthesized.
    text
        The text to be synthesized.

    Raises
    ------
    ValueError
        If an unsupported language is provided or if the synthesis process fails.
    """

    try:
        logger.info(f"Starting speech synthesis process for text: '{text}'")

        if language == IdentifiedLanguage.ENGLISH:
            model_path = os.path.join(PIPER_MODELS_DIR, ENG_MODEL_NAME)
        elif language == IdentifiedLanguage.SWAHILI:
            model_path = os.path.join(PIPER_MODELS_DIR, SWAHILI_MODEL_NAME)
        else:
            raise ValueError(f"Unsupported language: {language}")

        voice = PiperVoice.load(model_path)

        with wave.open("output.wav", "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(voice.config.sample_rate)

            voice.synthesize(text, wav_file)

        logger.info("Speech synthesis completed successfully.")

        with open("output.wav", "rb") as file:
            audio_data = file.read()

        os.remove("output.wav")

        return BytesIO(audio_data)
    except Exception as e:
        error_msg = f"Failed to synthesize speech for text '{text}': {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


async def transcribe_audio(*, file_path: str) -> TranscriptionResponse:
    """Transcribe audio from a file path using the specified Whisper model.

    Parameters
    ----------
    file_path
        The path to the audio file to be transcribed.

    Returns
    -------
    TranscriptionResponse
        The transcription response containing the transcribed text and identified
        language.

    Raises
    ------
    ValueError
        If the transcription process fails.
    """

    try:
        model = whisper.load_model(PREFERRED_MODEL, download_root=WHISPER_MODEL_DIR)

        logger.info(
            f"Starting transcription for {file_path} using {PREFERRED_MODEL} model."
        )

        result = model.transcribe(file_path)

        logger.info(f"Transcription completed successfully for {file_path}.")

        return TranscriptionResponse(language=result["language"], text=result["text"])
    except Exception as e:
        error_msg = f"Failed to transcribe audio file '{file_path}': {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e
