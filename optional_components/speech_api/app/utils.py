import logging
from io import BytesIO
from logging import Logger

from pydub import AudioSegment

from .config import LOG_LEVEL


def get_log_level_from_str(log_level_str: str = LOG_LEVEL) -> int:
    """
    Get log level from string
    """
    log_level_dict = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }
    return log_level_dict.get(log_level_str.upper(), logging.INFO)


def setup_logger(
    name: str = __name__, log_level: int = get_log_level_from_str()
) -> Logger:
    """
    Setup logger for the application
    """
    logger = logging.getLogger(name)

    # If the logger already has handlers,
    # assume it was already configured and return it.
    if logger.handlers:
        return logger

    logger.setLevel(log_level)

    formatter = logging.Formatter(
        "%(asctime)s %(filename)20s%(lineno)4s : %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
    )

    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger


def convert_audio_to_wav(audio_file: BytesIO) -> BytesIO:
    """
    Converts an audio file to WAV format with a 16kHz sample rate, mono channel,
    and 16-bit PCM encoding.
    """

    audio_file.seek(0)
    audio = AudioSegment.from_file(audio_file)

    audio = audio.set_frame_rate(16000)
    audio = audio.set_channels(1)
    audio = audio.set_sample_width(2)

    wav_io = BytesIO()
    audio.export(wav_io, format="wav", codec="pcm_s16le")
    wav_io.seek(0)
    return wav_io
