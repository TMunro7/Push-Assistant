"""
assistant/speech_to_text.py — local transcription via faster-whisper.

The model is loaded once at startup (~150 MB for tiny) and reused for
every recording.  CPU usage is ~0 % when idle; spikes only during the
brief transcription window after key release.
"""
import logging
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# Ignore clips shorter than 0.2 s — too short to contain a real command.
_MIN_SAMPLES = 3_200  # 0.2 s × 16 000 Hz


class SpeechToText:
    """
    Wraps faster-whisper for efficient CPU transcription.

    Model is loaded with int8 quantisation by default, which is ~2×
    faster than float32 on modern x86 CPUs with no meaningful accuracy
    loss for short commands.  Change compute_type to "float32" in
    config.yaml if you encounter issues on older hardware.
    """

    def __init__(self, config: dict) -> None:
        stt = config.get("speech_to_text", {})
        model_size: str = stt.get("model", "tiny")
        compute_type: str = stt.get("compute_type", "int8")
        language_raw: Optional[str] = stt.get("language", "en")
        # Convert empty / null to None so Whisper auto-detects language
        self._language: Optional[str] = language_raw if language_raw else None

        logger.info(
            "Loading Whisper '%s' model (%s) on CPU — "
            "this may download ~75 MB on first run…",
            model_size,
            compute_type,
        )
        self._model = WhisperModel(
            model_size, device="cpu", compute_type=compute_type
        )
        logger.info("Whisper model ready")

    def transcribe(self, audio: np.ndarray) -> str:
        """
        Convert a float32 16 kHz mono array to lowercase text.
        Returns "" if the clip is too short or completely silent.
        """
        if audio is None or len(audio) < _MIN_SAMPLES:
            return ""

        segments, _info = self._model.transcribe(
            audio,
            language=self._language,
            beam_size=1,       # fastest decoding
            vad_filter=True,   # skip silent sections via Silero VAD
            vad_parameters={"min_silence_duration_ms": 200},
        )

        text = " ".join(seg.text for seg in segments).strip()
        return text
