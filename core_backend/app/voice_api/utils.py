from enum import Enum
from gtts.lang import tts_langs

class IdentifiedGttsLanguage(str, Enum):
    """
    Identified language of the user's input.
    """
    
    ENGLISH = "en"
    SWAHILI = "sw"
    HINDI = "hi"
    BENGALI = "bn"
    UNINTELLIGIBLE = "UNINTELLIGIBLE"
    UNSUPPORTED = "UNSUPPORTED"

    @classmethod
    def get_supported_languages(cls) -> list[str]:
        return [
            lang
            for lang in cls._member_names_
            if lang not in ("UNINTELLIGIBLE", "UNSUPPORTED")
        ]

def get_gtts_lang_code(identified_lang: IdentifiedGttsLanguage) -> str:
    """
    Maps IdentifiedLanguage to gTTS language code.
    """
    gtts_langs = tts_langs()
    if identified_lang.value in gtts_langs:
        return identified_lang.value
    else:
        raise ValueError(f"Language {identified_lang.name} is not supported by gTTS")