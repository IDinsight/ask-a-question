import os
import urllib.request
import zipfile

from pydub import AudioSegment

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


def download_model(model_url: str, model_path: str) -> None:
    """
    Downloads and extracts the Vosk model if it does not exist.
    """
    try:
        if not os.path.exists(model_path):
            os.makedirs(model_path, exist_ok=True)
            logger.info(f"Downloading Vosk model from {model_url}...")
            model_archive_path = os.path.join(model_path, "model.zip")
            urllib.request.urlretrieve(model_url, model_archive_path)

            with zipfile.ZipFile(model_archive_path, "r") as zip_ref:
                zip_ref.extractall(model_path)
            os.remove(model_archive_path)
            logger.info(f"Vosk model downloaded and extracted to {model_path}.")
        else:
            logger.info(f"Vosk model already exists at {model_path}.")
    except Exception as e:
        error_msg = f"Failed to download and extract Vosk model: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


def convert_mp3_to_wav(file_path: str) -> str:
    """
    Converts an MP3 file to WAV format.
    """
    try:
        logger.info(f"Converting MP3 file {file_path} to WAV format.")
        audio = AudioSegment.from_mp3(file_path)
        wav_path = file_path.replace(".mp3", ".wav")
        audio.export(wav_path, format="wav")
        logger.info(f"Successfully converted {file_path} to {wav_path}.")
        return wav_path
    except Exception as e:
        error_msg = f"Failed to convert {file_path} to WAV format: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e
