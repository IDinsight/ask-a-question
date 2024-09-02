import os
from io import BytesIO

import numpy as np
import sounddevice as sd
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
    Synthesizes speech from text using the specified Piper TTS model
    and return it as a BytesIO stream.
    """
    try:

        model_path = os.path.join(PIPER_MODELS_DIR, ENG_MODEL_NAME)
        voice = PiperVoice.load(model_path)

        audio_stream = BytesIO()

        stream = sd.OutputStream(
            samplerate=voice.config.sample_rate, channels=1, dtype="int16"
        )
        stream.start()

        for audio_bytes in voice.synthesize_stream_raw(text):
            int_data = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_stream.write(int_data.tobytes())

        stream.stop()
        stream.close()

        audio_stream.seek(0)

        return audio_stream

    except Exception as e:
        error_msg = f"Failed to synthesize speech for text '{text}': {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e
