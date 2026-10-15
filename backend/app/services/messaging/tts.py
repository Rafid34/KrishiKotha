"""gTTS wrapper with a hash-based audio cache (F2.4, Section 9 Phase 11).

Audio files are named `<sha256(text)>.mp3` inside `AUDIO_DIR`. A tiny `<sha256>.txt`
sidecar stores the source text so the audio route can synthesize lazily: registering
text is cheap and offline, and gTTS (which needs network) is only called the first
time an MP3 is actually requested. The same text never triggers a second TTS call.
"""
from __future__ import annotations

import hashlib
import io
import os
import re
import threading
from pathlib import Path

from ...config import get_settings

TTS_LANGUAGE = "bn"
AUDIO_URL_PREFIX = "/api/audio/"
_FILENAME_RE = re.compile(r"^[0-9a-f]{64}\.mp3$")
_SYNTH_LOCK = threading.Lock()


class AudioNotFoundError(LookupError):
    """The filename is malformed or no text was ever registered for it."""


class TtsUnavailableError(RuntimeError):
    """Text to speech is disabled or gTTS failed (for example when offline)."""


def audio_filename(text: str) -> str:
    """Return the cache filename for `text`: SHA-256 hex of the UTF-8 text plus `.mp3`."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest() + ".mp3"


def audio_url(filename: str) -> str:
    """Return the API path that serves `filename`."""
    return AUDIO_URL_PREFIX + filename


def is_valid_filename(filename: str) -> bool:
    """True only for names this module could have generated (blocks path traversal)."""
    return bool(_FILENAME_RE.fullmatch(filename))


def _audio_dir() -> Path:
    path = get_settings().audio_path
    path.mkdir(parents=True, exist_ok=True)
    return path


def register_text(text: str) -> str:
    """Remember `text` for lazy synthesis and return its audio filename. No network."""
    filename = audio_filename(text)
    sidecar = _audio_dir() / (filename[:-4] + ".txt")
    if not sidecar.exists():
        sidecar.write_text(text, encoding="utf-8")
    return filename


def synthesize(text: str) -> bytes:
    """Call gTTS (language `bn`) and return MP3 bytes. gTTS is imported only here."""
    from gtts import gTTS

    buffer = io.BytesIO()
    gTTS(text=text, lang=TTS_LANGUAGE).write_to_fp(buffer)
    return buffer.getvalue()


def ensure_audio(filename: str) -> Path:
    """Return the cached MP3 path, generating it once from the registered text.

    Raises:
        AudioNotFoundError: malformed filename, or text was never registered.
        TtsUnavailableError: TTS disabled or gTTS failed.
    """
    if not is_valid_filename(filename):
        raise AudioNotFoundError(filename)
    directory = _audio_dir()
    mp3 = directory / filename
    if mp3.exists() and mp3.stat().st_size > 0:
        return mp3
    sidecar = directory / (filename[:-4] + ".txt")
    if not sidecar.exists():
        raise AudioNotFoundError(filename)
    if not get_settings().tts_enabled:
        raise TtsUnavailableError("Text to speech is disabled (TTS_ENABLED=false).")
    text = sidecar.read_text(encoding="utf-8")
    with _SYNTH_LOCK:
        if mp3.exists() and mp3.stat().st_size > 0:  # another request finished first
            return mp3
        try:
            data = synthesize(text)
        except Exception as exc:  # gTTS raises gTTSError, requests and OS errors when offline
            raise TtsUnavailableError(f"Text to speech failed: {exc}") from exc
        if not data:
            raise TtsUnavailableError("Text to speech returned no audio.")
        tmp = mp3.with_suffix(".mp3.tmp")
        tmp.write_bytes(data)
        os.replace(tmp, mp3)
    return mp3


def prepare_audio(text: str) -> str:
    """Register `text`, generate its MP3 now, and return the filename (voice webhook)."""
    filename = register_text(text)
    ensure_audio(filename)
    return filename
