"""
assistant/audio_recorder.py — microphone capture via sounddevice.

CPU usage is zero when not recording; sounddevice only opens the
PortAudio stream while start() is active.
"""
import logging
from typing import Optional

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


class AudioRecorder:
    """
    Buffers microphone input as float32 samples while start() is active.
    Call stop() to close the stream and retrieve the recorded numpy array.
    """

    def __init__(self, config: dict) -> None:
        self._sample_rate: int = config["audio"]["sample_rate"]
        self._channels: int = config["audio"]["channels"]
        self._frames: list[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Open the mic stream and begin buffering."""
        self._frames = []
        try:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="float32",
                callback=self._callback,
            )
            self._stream.start()
        except Exception:
            logger.exception("Failed to open audio stream — check microphone access")
            self._stream = None

    def stop(self) -> np.ndarray:
        """
        Stop the stream and return all buffered audio as a 1-D float32
        array at the configured sample rate.  Returns an empty array if
        nothing was recorded.
        """
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                logger.exception("Error closing audio stream")
            self._stream = None

        if not self._frames:
            return np.array([], dtype="float32")

        audio = np.concatenate(self._frames, axis=0).flatten()
        self._frames = []
        return audio

    # ── sounddevice callback (called from PortAudio thread) ────────────────────

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,  # noqa: ARG002
        time,         # noqa: ARG002
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            logger.debug("Audio callback status: %s", status)
        self._frames.append(indata.copy())
