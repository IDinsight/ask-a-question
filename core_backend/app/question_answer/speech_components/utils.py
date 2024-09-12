from io import BytesIO

from pydub import AudioSegment

from ...llm_call.llm_prompts import IdentifiedLanguage
from ...utils import setup_logger

logger = setup_logger("Voice utils")

# Add language codes and voice models according to
# https://cloud.google.com/text-to-speech/docs/voices

lang_code_mapping = {
    IdentifiedLanguage.ENGLISH: ("en-US", "Neural2-D"),
    # IdentifiedLanguage.SWAHILI: ("sw-TZ", "Neural2-D"), # no support for swahili
    IdentifiedLanguage.HINDI: ("hi-IN", "Neural2-D"),
    # Add more languages and models as needed
}


def get_gtts_lang_code_and_model(
    identified_language: IdentifiedLanguage,
) -> tuple[str, str]:
    """
    Maps IdentifiedLanguage values to Google Cloud Text-to-Speech language codes
    and voice model names.
    """

    result = lang_code_mapping.get(identified_language)
    if result is None:
        raise ValueError(f"Unsupported language: {identified_language}")

    return result


def convert_audio_to_wav(audio_file: BytesIO) -> BytesIO:
    """
    Converts an audio file to WAV format with a 16kHz sample rate,
    mono channel, and 16-bit sample width.
    """

    audio_file.seek(0)
    audio = AudioSegment.from_file(audio_file)

    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

    wav_io = BytesIO()
    audio.export(wav_io, format="wav")
    wav_io.seek(0)
    return wav_io
