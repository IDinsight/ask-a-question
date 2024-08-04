import whisper

from .config import PREFERRED_MODEL, WHISPER_MODEL_DIR
from .schemas import TranscriptionResponse
from .utils import setup_logger

logger = setup_logger("Whisper ASR")

model = whisper.load_model(PREFERRED_MODEL, download_root=WHISPER_MODEL_DIR)
logger.info(f"Whisper model '{PREFERRED_MODEL}' loaded successfully.")


async def transcribe_audio(file_path: str) -> TranscriptionResponse:
    """
    Transcribes audio from a file path using the specified Whisper model.
    """
    try:

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
