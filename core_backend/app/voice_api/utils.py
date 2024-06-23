from ..llm_call.llm_prompts import IdentifiedLanguage


def get_gtts_lang_code(identified_language: IdentifiedLanguage) -> str:
    """
    Maps IdentifiedLanguage values to gTTS language codes.
    """

    mapping = {
        IdentifiedLanguage.ENGLISH: "en",
        IdentifiedLanguage.SWAHILI: "sw",
        IdentifiedLanguage.HINDI: "hi",
    }

    return mapping.get(identified_language, "en")
