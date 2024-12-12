from enum import Enum

from pydantic import BaseModel, ConfigDict


class IdentifiedLanguage(str, Enum):
    """
    Identified language of the user's input.
    """

    ENGLISH = "ENGLISH"
    SWAHILI = "SWAHILI"
    # XHOSA = "XHOSA"
    # ZULU = "ZULU"
    # AFRIKAANS = "AFRIKAANS"
    HINDI = "HINDI"
    UNINTELLIGIBLE = "UNINTELLIGIBLE"
    UNSUPPORTED = "UNSUPPORTED"


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
    language: IdentifiedLanguage

    model_config = ConfigDict(from_attributes=True)


class SynthesisResponse(BaseModel):
    """
    Pydantic model for the synthesis response for TTS.

    """

    audio: bytes

    model_config = ConfigDict(from_attributes=True)
