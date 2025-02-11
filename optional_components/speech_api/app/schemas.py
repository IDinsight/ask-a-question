"""This module contains Pydantic models for the speech API."""

from enum import Enum

from pydantic import BaseModel, ConfigDict


class IdentifiedLanguage(str, Enum):
    """Enumeration for the identified language of the user's input."""

    # AFRIKAANS = "AFRIKAANS"
    ENGLISH = "ENGLISH"
    HINDI = "HINDI"
    SWAHILI = "SWAHILI"
    UNINTELLIGIBLE = "UNINTELLIGIBLE"
    UNSUPPORTED = "UNSUPPORTED"
    # XHOSA = "XHOSA"
    # ZULU = "ZULU"


class SynthesisRequest(BaseModel):
    """Pydantic model for the synthesis request for TTS."""

    language: IdentifiedLanguage
    text: str

    model_config = ConfigDict(from_attributes=True)


class SynthesisResponse(BaseModel):
    """Pydantic model for the synthesis response for TTS."""

    audio: bytes

    model_config = ConfigDict(from_attributes=True)


class TranscriptionRequest(BaseModel):
    """Pydantic model for the transcription request for STT."""

    stt_file_path: str

    model_config = ConfigDict(from_attributes=True)


class TranscriptionResponse(BaseModel):
    """Pydantic model for the transcription response for STT."""

    language: str
    text: str

    model_config = ConfigDict(from_attributes=True)
