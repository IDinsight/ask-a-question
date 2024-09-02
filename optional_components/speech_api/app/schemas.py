from pydantic import BaseModel, ConfigDict


class TranscriptionRequest(BaseModel):
    """
    Pydantic model for the transcription request for STT.

    """

    stt_file_path: str

    model_config = ConfigDict(from_attributes=True)


class TranscriptionResponse(BaseModel):
    """
    Pydantic model for the transcription response for STT.

    """

    text: str
    language: str

    model_config = ConfigDict(from_attributes=True)


class SynthesisRequest(BaseModel):
    """
    Pydantic model for the synthesis request for TTS.

    """

    text: str

    model_config = ConfigDict(from_attributes=True)
