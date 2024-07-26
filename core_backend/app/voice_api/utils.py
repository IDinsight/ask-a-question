from ..llm_call.llm_prompts import IdentifiedLanguage
from ..utils import setup_logger

logger = setup_logger("Voice utils")


def get_gtts_lang_code(identified_language: IdentifiedLanguage) -> str:
    """
    Maps IdentifiedLanguage values to gTTS language codes.
    """
    mapping = {
        IdentifiedLanguage.ENGLISH: "en",
        IdentifiedLanguage.SWAHILI: "sw",
        IdentifiedLanguage.HINDI: "hi",
    }

    lang_code = mapping.get(identified_language)
    if lang_code is None:
        raise ValueError(f"Unsupported language: {identified_language}")

    return lang_code
