import os

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


def convert_mp3_to_wav(input_filename: str) -> str:
    """
    Converts an MP3 file to a WAV file with the required specifications.

    The WAV file will have a sample rate of 16 kHz, mono channel, and
    LINEAR16 encoding. If the input file is already a WAV file,
    it will return the original filename.
    """

    if input_filename.lower().endswith(".mp3"):
        logger.info(f"Converting {input_filename} from MP3 to WAV format.")

        audio = AudioSegment.from_mp3(input_filename)
        wav_filename = os.path.splitext(input_filename)[0] + ".wav"
        audio.set_frame_rate(16000).set_channels(1).export(
            wav_filename, format="wav", codec="pcm_s16le"
        )

        logger.info(f"Conversion complete. Output file: {wav_filename}")
        return wav_filename
    else:
        logger.info(f"{input_filename} is already in WAV format.")
        return input_filename
