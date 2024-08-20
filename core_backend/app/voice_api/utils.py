import os

from pydub import AudioSegment

from ..llm_call.llm_prompts import IdentifiedLanguage
from ..utils import setup_logger

logger = setup_logger("Voice utils")


def get_gtts_lang_code(identified_language: IdentifiedLanguage) -> str:
    """
    Maps IdentifiedLanguage values to google-cloud text to
    speech language codes.
    """
    # Please add the language codes according to
    # https://cloud.google.com/text-to-speech/docs/voices
    mapping = {
        IdentifiedLanguage.ENGLISH: "en-US",
        IdentifiedLanguage.SWAHILI: "sw-TZ",
        IdentifiedLanguage.HINDI: "hi-IN",
    }

    lang_code = mapping.get(identified_language)
    if lang_code is None:
        raise ValueError(f"Unsupported language: {identified_language}")

    return lang_code


def convert_audio_to_wav(input_filename: str) -> str:
    """
    Converts an MP3 or M4A file to a WAV file and ensures the WAV file has
    the required specifications.
    """
    file_extension = input_filename.lower().split(".")[-1]

    if file_extension in ["mp3", "m4a"]:
        audio = AudioSegment.from_file(input_filename, format=file_extension)

        wav_filename = os.path.splitext(input_filename)[0] + ".wav"
        audio.export(wav_filename, format="wav")
        logger.info(f"Conversion complete. Output file: {wav_filename}")
    else:
        wav_filename = input_filename
        logger.info(f"{wav_filename} is already in WAV format.")

    return set_wav_specifications(wav_filename)


def set_wav_specifications(wav_filename: str) -> str:
    """
    Ensures that the WAV file has a sample rate of 16 kHz, mono channel,
    and LINEAR16 encoding.
    """
    logger.info(f"Ensuring {wav_filename} meets the required WAV specifications.")

    audio = AudioSegment.from_wav(wav_filename)
    updated_wav_filename = os.path.splitext(wav_filename)[0] + "_updated.wav"
    audio.set_frame_rate(16000).set_channels(1).export(
        updated_wav_filename, format="wav", codec="pcm_s16le"
    )

    logger.info(f"Updated file created: {updated_wav_filename}")
    return updated_wav_filename
