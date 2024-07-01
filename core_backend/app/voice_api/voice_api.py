import json
import wave

from config import (
    ENGLISH_MODEL_PATH,
    ENGLISH_MODEL_URL,
)
from gtts import gTTS  # type: ignore
from vosk import KaldiRecognizer, Model

from ..llm_call.llm_prompts import IdentifiedLanguage
from ..utils import setup_logger
from .utils import convert_mp3_to_wav, download_model, get_gtts_lang_code

logger = setup_logger("Voice API")


async def transcribe_audio(file_path: str) -> str:
    """
    Transcribes the audio file at the given file path using the appropriate Vosk model.
    """
    try:
        download_model(ENGLISH_MODEL_URL, ENGLISH_MODEL_PATH)
        # download_model(HINDI_MODEL_URL, HINDI_MODEL_PATH)

        wav_path = convert_mp3_to_wav(file_path)

        model = Model(ENGLISH_MODEL_PATH)

        with wave.open(wav_path, "rb") as wf:
            rec = KaldiRecognizer(model, wf.getframerate())
            rec.SetWords(True)
            transcription = ""

            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    transcription += result.get("text", "")

            final_result = json.loads(rec.FinalResult())
            transcription += final_result.get("text", "")

        return transcription

    except Exception as e:
        error_msg = f"Failed to transcribe audio file '{file_path}': {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


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
