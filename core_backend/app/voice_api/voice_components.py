from io import BytesIO

from gtts import gTTS

from ..config import BUCKET_NAME
from ..llm_call.llm_prompts import IdentifiedLanguage
from ..utils import generate_signed_url, setup_logger, upload_file_to_gcs
from .utils import get_gtts_lang_code

logger = setup_logger("Voice API")


async def generate_speech(
    text: str,
    language: IdentifiedLanguage,
    destination_blob_name: str = "response.mp3",
) -> str:
    """
    Converts the provided text to speech and saves it as an mp3 file on
    Google cloud storage
    """

    try:
        lang = get_gtts_lang_code(language)
        tts = gTTS(text=text, lang=lang)

        mp3_file = BytesIO()
        tts.write_to_fp(mp3_file)
        content_type = "audio/mpeg"

        await upload_file_to_gcs(
            BUCKET_NAME, mp3_file, destination_blob_name, content_type
        )

        signed_url = await generate_signed_url(BUCKET_NAME, destination_blob_name)

        logger.info(
            f"Speech generated successfully. Saved to {destination_blob_name} in GCS."
        )
        return signed_url

    except Exception as e:
        error_msg = f"Failed to generate speech: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e
