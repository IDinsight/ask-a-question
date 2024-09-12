import os
from io import BytesIO

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from .schemas import TranscriptionResponse
from .utils import convert_audio_to_wav, setup_logger
from .voice_components import transcribe_audio

router = APIRouter()
logger = setup_logger("Transcribe Endpoint")


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio_endpoint(
    file: Request,
) -> TranscriptionResponse | JSONResponse:
    """
    Transcribes audio from the provided file using the appropriate ASR model.
    """
    try:

        file_stream = BytesIO(await file.body())

        wav_io = convert_audio_to_wav(file_stream)

        file_path = "temp/audio.wav"
        with open(file_path, "wb") as f:
            f.write(wav_io.getvalue())

        logger.info(f"Received request to transcribe file at: {file_path}")

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "File not found."},
            )

        result = await transcribe_audio(file_path)

        return result

    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "An unexpected error occurred."},
        )
