from pydantic import BaseModel, ConfigDict


class TranscriptionRequest(BaseModel):
    """
    Pydantic model for the transcription request.

    """

    file_path: str


class TranscriptionResponse(BaseModel):
    """
    Pydantic model for the transcription response.

    """

    text: str
    language: str

    model_config = ConfigDict(from_attributes=True)
