from fastapi import File, UploadFile
from pydantic import BaseModel, ConfigDict

from ..question_answer.schemas import ErrorType


class AudioQuery(BaseModel):
    """
    Pydantic model for audio query
    """

    file: UploadFile = File(...)
    audio_metadata: dict = {}

    model_config = ConfigDict(from_attributes=True)


class AudioQueryError(BaseModel):
    """
    Pydantic model for audio query related errors
    """

    error_message: str
    error_type: ErrorType
    debug_info: dict = {}

    model_config = ConfigDict(from_attributes=True)
