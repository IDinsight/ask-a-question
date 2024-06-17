from gtts import gTTS
import os
from ..question_answer.schemas import QueryRefined, QueryResponse, QueryResponseError
from ..llm_call.process_input import identify_language__before
from ..utils import setup_logger
from .utils import get_gtts_lang_code

logger = setup_logger("TTS")


@identify_language__before
async def generate_speech(
    question: QueryRefined,
    response: QueryResponse | QueryResponseError,
    save_path: str = "response.mp3",
) -> QueryResponse | QueryResponseError:
    """
    Converts the provided text to speech and saves it as an mp3 file.
    """
    if isinstance(response, QueryResponseError):
        logger.error("Received QueryResponseError. Unable to generate speech.")
        return response

    if question.original_language is None:
        error_msg = "Language hasn't been identified. Identify language before calling this function."
        logger.error(error_msg)
        return QueryResponseError(error=error_msg)

    try:
        lang = get_gtts_lang_code(question.original_language)
        tts = gTTS(text=question.query_text, lang=lang)
        tts.save(save_path)
        response.debug_info["tts_file"] = save_path
        logger.info(f"Speech generated successfully. Saved to {save_path}")
        return response
    except Exception as e:
        error_msg = f"Failed to generate speech: {str(e)}"
        logger.error(error_msg)
        return QueryResponseError(error=error_msg)
