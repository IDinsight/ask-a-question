import os
from io import BytesIO

import whisper
from piper.voice import PiperVoice

from .config import ENG_MODEL_NAME, PIPER_MODELS_DIR, PREFERRED_MODEL, WHISPER_MODEL_DIR
from .schemas import TranscriptionResponse
from .utils import setup_logger

logger = setup_logger("Whisper ASR")


async def transcribe_audio(file_path: str) -> TranscriptionResponse:
    """
    Transcribes audio from a file path using the specified Whisper model.
    """
    try:

        model = whisper.load_model(PREFERRED_MODEL, download_root=WHISPER_MODEL_DIR)

        logger.info(
            f"Starting transcription for {file_path} using {PREFERRED_MODEL} model."
        )

        result = model.transcribe(file_path)

        logger.info(f"Transcription completed successfully for {file_path}.")

        return TranscriptionResponse(text=result["text"], language=result["language"])

    except Exception as e:
        error_msg = f"Failed to transcribe audio file '{file_path}': {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


async def synthesize_speech(text: str) -> BytesIO:
    """
    Synthesizes speech from text using the specified Piper TTS model.
    """
    try:
        model_path = os.path.join(PIPER_MODELS_DIR, ENG_MODEL_NAME)
        logger.info(f"Loading Piper TTS model from {model_path}.")

        voice = PiperVoice.load(model_path)

        logger.info(f"Starting speech synthesis for text: '{text}'.")

        audio = voice.synthesize(text)

        audio_stream = BytesIO(audio)

        logger.info("Speech synthesis completed successfully.")

        return audio_stream

    except Exception as e:
        error_msg = f"Failed to synthesize speech for text '{text}': {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e
