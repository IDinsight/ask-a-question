import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .schemas import TranscriptionRequest, TranscriptionResponse
from .utils import setup_logger
from .voice_components import transcribe_audio

router = APIRouter()
logger = setup_logger("Transcribe Endpoint")


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio_endpoint(
    request: TranscriptionRequest,
) -> TranscriptionResponse | JSONResponse:
    """
    Transcribes audio from the specified file path using the specified Whisper model.
    """
    try:
        logger.info(f"Received request to transcribe file at: {request.file_path}")

        if not os.path.exists(request.file_path):
            logger.error(f"File not found: {request.file_path}")
            return JSONResponse(status_code=404, content={"error": "File not found."})

        result = await transcribe_audio(request.file_path)
        return result

    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        return JSONResponse(
            status_code=500, content={"error": "An unexpected error occurred."}
        )
