"""Fast barge-in: notice the caller talking over the assistant locally."""

from __future__ import annotations

from ..rtp.g711 import Codec

# RMS on the 16-bit scale; telephone speech is typically 2000-8000, line noise
# a few hundred. The threshold adapts to noisy lines.
MIN_SPEECH_RMS = 1200.0
NOISE_FACTOR = 4.0
SPEECH_MS = 240  # continuous speech needed to count as an interruption
GAP_MS = 60  # short dips between syllables that do not reset the count
REARM_MS = 300  # quiet needed before the next interruption is detected


class SpeechDetector:
    """Energy based voice activity detection on G.711 frames.

    The remote phone cancels the assistant's echo, so loud audio on the line
    while the assistant speaks means the caller is talking. Detection happens
    here instead of waiting for the model's own turn detection, which reacts
    noticeably later on phone lines.
    """

    def __init__(self, codec: Codec) -> None:
        """Initialize the detector."""
        self._codec = codec
        self._noise = 300.0
        self._loud_ms = 0
        self._quiet_ms = 0
        self._armed = True

    def feed(self, frame: bytes) -> bool:
        """Process a frame; return True when the caller starts talking."""
        duration = len(frame) // 8
        level = self._codec.rms(frame)
        if level >= max(MIN_SPEECH_RMS, self._noise * NOISE_FACTOR):
            self._loud_ms += duration
            self._quiet_ms = 0
        else:
            self._noise += (level - self._noise) * 0.05
            self._quiet_ms += duration
            if self._quiet_ms > GAP_MS:
                self._loud_ms = 0
            if self._quiet_ms >= REARM_MS:
                self._armed = True
        if self._armed and self._loud_ms >= SPEECH_MS:
            self._armed = False
            return True
        return False
