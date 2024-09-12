from pydantic import BaseModel, ConfigDict


class TranscriptionResponse(BaseModel):
    """
    Pydantic model for the transcription response.

    """

    text: str
    language: str

    model_config = ConfigDict(from_attributes=True)
