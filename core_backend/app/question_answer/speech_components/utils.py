import os
from io import BytesIO

from faster_whisper import WhisperModel  # type: ignore
from pydub import AudioSegment

from ...llm_call.llm_prompts import IdentifiedLanguage
from ...utils import get_file_extension_from_mime_type, get_http_client, setup_logger

logger = setup_logger("Voice utils")

# Add language codes and voice models according to
# https://cloud.google.com/text-to-speech/docs/voices

lang_code_mapping_tts = {
    IdentifiedLanguage.ENGLISH: ("en-US", "Neural2-D"),
    # IdentifiedLanguage.SWAHILI: ("sw-TZ", "Neural2-D"), # no support for swahili
    IdentifiedLanguage.HINDI: ("hi-IN", "Neural2-D"),
    # Add more languages and models as needed
}

language_code_mapping_stt = {
    "en": "en-IN",  # English (India)
    "hi": "hi-IN",  # Hindi (India)
    # Add more language mappings as needed
}


def detect_language(file_path: str) -> str:
    """
    Uses Faster Whisper's tiny model to detect the language of the audio file.
    """
    model = WhisperModel("tiny", download_root="/whisper_models")

    logger.info(f"Detecting language for {file_path} using Faster Whisper tiny model.")

    segments, info = model.transcribe(file_path)

    detected_language = info.language
    logger.info(f"Detected language: {detected_language}")

    google_language_code = language_code_mapping_stt.get(detected_language, "en-US")

    return google_language_code


def get_gtts_lang_code_and_model(
    identified_language: IdentifiedLanguage,
) -> tuple[str, str]:
    """
    Maps IdentifiedLanguage values to Google Cloud Text-to-Speech language codes
    and voice model names.
    """

    result = lang_code_mapping_tts.get(identified_language)
    if result is None:
        raise ValueError(f"Unsupported language: {identified_language}")

    return result


def convert_audio_to_wav(input_filename: str) -> str:
    """
    Converts an audio file (MP3, M4A, OGG, FLAC, AAC, WebM, etc.) to a WAV file
    and ensures the WAV file has the required specifications. Returns an error
    if the file format is unsupported.
    """

    file_extension = input_filename.lower().split(".")[-1]

    supported_formats = ["mp3", "m4a", "wav", "ogg", "flac", "aac", "aiff", "webm"]

    if file_extension in supported_formats:
        if file_extension != "wav":
            audio = AudioSegment.from_file(input_filename, format=file_extension)
            wav_filename = os.path.splitext(input_filename)[0] + ".wav"
            audio.export(wav_filename, format="wav")
            logger.info(f"Conversion complete. Output file: {wav_filename}")
        else:
            wav_filename = input_filename
            logger.info(f"{wav_filename} is already in WAV format.")

        return set_wav_specifications(wav_filename)
    else:
        logger.error(f"""Unsupported file format: {file_extension}.""")
        raise ValueError(f"""Unsupported file format: {file_extension}.""")


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


async def post_to_internal_tts(
    text: str, endpoint_url: str, language: IdentifiedLanguage
) -> BytesIO:
    """
    Post request to synthesize speech using the internal TTS model.
    """
    async with get_http_client() as client:
        payload = {"text": text, "language": language}
        async with client.post(endpoint_url, json=payload) as response:
            if response.status != 200:
                error_content = await response.json()
                logger.error(f"Error from CUSTOM_TTS_ENDPOINT: {error_content}")
                raise ValueError(f"Error from CUSTOM_TTS_ENDPOINT: {error_content}")

            audio_content = await response.read()

            return BytesIO(audio_content)


async def download_file_from_url(file_url: str) -> tuple[BytesIO, str, str]:
    """
    Asynchronously download a file from a given URL using the
    global aiohttp ClientSession and return its content as a BytesIO object,
    along with its content type and file extension.
    """
    async with get_http_client() as client:
        try:
            async with client.get(file_url) as response:
                if response.status != 200:
                    error_content = await response.text()
                    logger.error(f"Failed to download file: {error_content}")
                    raise ValueError(f"Failed to download file: {error_content}")

                content_type = response.headers.get("Content-Type")
                if not content_type:
                    logger.error("Content-Type header missing in response")
                    raise ValueError("Unable to determine file content type")

                file_stream = BytesIO(await response.read())
                file_extension = get_file_extension_from_mime_type(content_type)

        except Exception as e:
            logger.error(f"Error during file download: {str(e)}")
            raise ValueError(f"Unable to fetch file: {str(e)}") from None

    return file_stream, content_type, file_extension


async def post_to_speech_stt(file_path: str, endpoint_url: str) -> dict:
    """
    Post request the file to the speech endpoint to get the transcription
    """
    async with get_http_client() as client:
        async with client.post(
            endpoint_url, json={"stt_file_path": file_path}
        ) as response:
            if response.status != 200:
                error_content = await response.json()
                logger.error(f"Error from CUSTOM_STT_ENDPOINT: {error_content}")
                raise ValueError(f"Error from CUSTOM_STT_ENDPOINT: {error_content}")
            return await response.json()
