import os

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse, StreamingResponse

from .schemas import (
    SynthesisRequest,
    SynthesisResponse,
    TranscriptionRequest,
    TranscriptionResponse,
)
from .utils import setup_logger
from .voice_components import synthesize_speech, transcribe_audio

router = APIRouter()
logger = setup_logger("Speech Endpoints")


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio_endpoint(
    request: TranscriptionRequest,
) -> TranscriptionResponse | JSONResponse:
    """
    Transcribes audio from the specified file path using the Appropriate ASR model.
    """
    try:
        logger.info(f"Received request to transcribe file at: {request.stt_file_path}")

        if not os.path.exists(request.stt_file_path):
            logger.error(f"File not found: {request.stt_file_path}")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "File not found."},
            )

        result = await transcribe_audio(request.stt_file_path)
        return result

    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "An unexpected error occurred."},
        )


@router.post("/synthesize", response_model=SynthesisResponse)
async def synthesize_speech_endpoint(
    request: SynthesisRequest,
) -> StreamingResponse | JSONResponse:
    """
    Synthesizes speech from the specified text input using the Appropriate TTS model.
    """
    try:
        logger.info(f"Received request to synthesize text: {request.text}")
        logger.info(f"Language: {request.language}")

        if not request.text.strip():
            logger.error("The text input is empty.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Text input cannot be empty."},
            )

        result = await synthesize_speech(request.text, request.language)
        return StreamingResponse(result, media_type="audio/wav")

    except Exception as e:
        logger.error(f"Unexpected error during speech synthesis: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "An unexpected error occurred."},
        )
