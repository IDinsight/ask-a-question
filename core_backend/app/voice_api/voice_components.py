from gtts import gTTS

from ..llm_call.llm_prompts import IdentifiedLanguage
from ..utils import setup_logger
from .utils import get_gtts_lang_code

logger = setup_logger("Voice API")


async def generate_speech(
    text: str,
    language: IdentifiedLanguage,
    save_path: str = "response.mp3",
) -> str:
    """
    Converts the provided text to speech and saves it as an mp3 file.
    """

    try:
        lang = get_gtts_lang_code(language)
        tts = gTTS(text=text, lang=lang)
        tts.save(save_path)
        logger.info(f"Speech generated successfully. Saved to {save_path}")
        return save_path

    except Exception as e:
        error_msg = f"Failed to generate speech: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e
