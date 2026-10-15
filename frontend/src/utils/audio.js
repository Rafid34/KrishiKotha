// Plays the Bangla MP3 served by GET /api/audio/{filename} (F2.4).
// Only one clip plays at a time. A failed load (for example HTTP 503 when gTTS is
// offline) rejects, so callers can fall back to showing the text only.

let active = null;

/** Stop the clip that is currently playing, if any. */
export function stopAudio() {
  if (active) active.stop();
}

/**
 * Play an audio URL and resolve when it ends (or is stopped).
 * Rejects when the URL is missing, the file cannot be loaded, or playback is blocked.
 * @param {string|null|undefined} url
 * @param {{ onPlaying?: () => void }} [options]
 * @returns {Promise<void>}
 */
export function playAudio(url, { onPlaying } = {}) {
  if (!url) return Promise.reject(new Error('No audio available'));
  stopAudio();

  return new Promise((resolve, reject) => {
    const audio = new Audio(url);
    const handle = {
      stop() {
        audio.pause();
        finish(resolve);
      },
    };

    function finish(settle, arg) {
      audio.onended = null;
      audio.onerror = null;
      audio.onplaying = null;
      if (active === handle) active = null;
      settle(arg);
    }

    active = handle;
    audio.onplaying = () => onPlaying?.();
    audio.onended = () => finish(resolve);
    audio.onerror = () => finish(reject, new Error('Audio could not be loaded'));
    Promise.resolve(audio.play()).catch((err) => finish(reject, err));
  });
}
