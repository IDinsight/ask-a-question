from io import BytesIO

from gtts import gTTS

from ..config import GCS_SPEECH_BUCKET
from ..llm_call.llm_prompts import IdentifiedLanguage
from ..utils import generate_signed_url, setup_logger, upload_file_to_gcs

logger = setup_logger("Voice API")


async def generate_tts_on_gcs(
    text: str,
    language: IdentifiedLanguage,
    destination_blob_name: str = "response.mp3",
) -> str:
    """
    Converts the provided text to speech and saves it as an mp3 file on
    Google cloud storage. Returns a URL to the generated speech.
    """

    try:
        lang = get_gtts_lang_code(language)
        tts = gTTS(text=text, lang=lang)

        mp3_file = BytesIO()
        tts.write_to_fp(mp3_file)
        content_type = "audio/mpeg"

        await upload_file_to_gcs(
            GCS_SPEECH_BUCKET, mp3_file, destination_blob_name, content_type
        )

        signed_url = await generate_signed_url(GCS_SPEECH_BUCKET, destination_blob_name)

        logger.info(
            f"Speech generated successfully. Saved to {destination_blob_name} in GCS."
        )
        return signed_url

    except Exception as e:
        error_msg = f"Failed to generate speech: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


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
