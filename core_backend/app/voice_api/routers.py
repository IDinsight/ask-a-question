import os

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import authenticate_key
from ..database import get_async_session
from ..question_answer.config import N_TOP_CONTENT_FOR_RAG
from ..question_answer.models import (
    save_query_response_error_to_db,
    save_query_response_to_db,
)
from ..question_answer.routers import get_llm_answer, get_user_query_and_response
from ..question_answer.schemas import (
    ErrorType,
    QueryBase,
    QueryResponse,
    QueryResponseError,
)
from ..users.models import UserDB
from ..utils import setup_logger
from .schemas import AudioQuery, AudioQueryError
from .voice_api import transcribe_audio

logger = setup_logger()

router = APIRouter(dependencies=[Depends(authenticate_key)], tags=["Voice API"])


@router.post(
    "/stt-llm-response",
    response_model=QueryResponse,
    responses={
        400: {"model": QueryResponseError, "description": "Bad Request"},
        500: {"model": AudioQueryError, "description": "Internal Server Error"},
    },
)
async def stt_llm_response(
    audio_file: AudioQuery,
    asession: AsyncSession = Depends(get_async_session),
    user_db: UserDB = Depends(authenticate_key),
) -> QueryResponse | JSONResponse:
    """
    Transcribes the provided MP3 file to text using Vosk ASR,
    then generates a custom response using LLM and returns it.
    """
    file_path = f"temp/{audio_file.file.filename}"
    try:

        with open(file_path, "wb") as f:
            f.write(await audio_file.file.read())

        transcription = await transcribe_audio(file_path)

        user_query = QueryBase(
            query_text=transcription, query_metadata=audio_file.audio_metadata
        )
        user_query_db, user_query_refined, response = await get_user_query_and_response(
            user_id=user_db.user_id, user_query=user_query, asession=asession
        )

        response = await get_llm_answer(
            question=user_query_refined,
            response=response,
            user_id=user_db.user_id,
            n_similar=int(N_TOP_CONTENT_FOR_RAG),
            asession=asession,
        )

        if isinstance(response, QueryResponseError):
            await save_query_response_error_to_db(user_query_db, response, asession)
            return JSONResponse(status_code=400, content=response.model_dump())
        else:
            await save_query_response_to_db(user_query_db, response, asession)
            return response

    except Exception as e:
        error_msg = f"Failed to process request: {str(e)}"
        logger.error(error_msg)
        error_response = AudioQueryError(
            error_message=error_msg,
            error_type=ErrorType.STT_ERROR,
            debug_info={},
        )
        return JSONResponse(status_code=500, content=error_response.model_dump())

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
