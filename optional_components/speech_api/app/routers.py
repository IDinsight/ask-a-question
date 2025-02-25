"""This module contains FastAPI endpoints for the speech API."""

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
logger = setup_logger(name="Speech Endpoints")


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio_endpoint(
    request: TranscriptionRequest,
) -> TranscriptionResponse | JSONResponse:
    """Transcribes audio from the specified file path using the Appropriate ASR model.

    Parameters
    ----------
    request
        The request object containing the file path to the audio file.

    Returns
    -------
    TranscriptionResponse
        The transcription response containing the transcribed text and identified
        language.
    """

    logger.info(f"Received request to transcribe file at: {request.stt_file_path}")

    if not os.path.exists(request.stt_file_path):
        logger.error(f"File not found: {request.stt_file_path}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "File not found."},
        )

    try:
        return await transcribe_audio(file_path=request.stt_file_path)
    except Exception as e:  # pylint: disable=W0718
        logger.error(f"Error during transcription: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "An unexpected error occurred."},
        )


@router.post("/synthesize", response_model=SynthesisResponse)
async def synthesize_speech_endpoint(
    request: SynthesisRequest,
) -> StreamingResponse | JSONResponse:
    """Synthesize speech from the specified text input using the Appropriate TTS model.

    Parameters
    ----------
    request
        The request object containing the text to be synthesized and the language.

    Returns
    -------
    StreamingResponse
        The synthesized speech as a streaming response.
    """

    logger.info(f"Received request to synthesize text: {request.text}")
    logger.info(f"Language: {request.language}")

    if not request.text.strip():
        logger.error("The text input is empty.")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Text input cannot be empty."},
        )

    try:
        result = await synthesize_speech(language=request.language, text=request.text)
        return StreamingResponse(result, media_type="audio/wav")
    except Exception as e:  # pylint: disable=W0718
        logger.error(f"Unexpected error during speech synthesis: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "An unexpected error occurred."},
        )
