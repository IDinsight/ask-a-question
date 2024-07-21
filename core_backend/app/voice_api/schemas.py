from pydantic import BaseModel

from ..question_answer.schemas import ErrorType


class AudioQuery(BaseModel):
    """
    Pydantic model for audio query
    """

    audio_metadata: dict = {}
    generate_tts: bool = False


class AudioQueryError(BaseModel):
    """
    Pydantic model for audio query related errors
    """

    error_message: str
    error_type: ErrorType
    debug_info: dict = {}
