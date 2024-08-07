from pydantic import BaseModel

from ..question_answer.schemas import ErrorType


class AudioQueryError(BaseModel):
    """
    Pydantic model for audio query related errors
    """

    error_message: str
    error_type: ErrorType
    debug_info: dict = {}
