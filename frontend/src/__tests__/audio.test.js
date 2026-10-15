import { afterEach, describe, expect, it, vi } from 'vitest';
import { playAudio, stopAudio } from '../utils/audio.js';

/** Minimal HTMLAudioElement stand-in; tests drive `ended` and `error` by hand. */
function installFakeAudio({ playRejects = false } = {}) {
  const instances = [];
  class FakeAudio {
    constructor(url) {
      this.url = url;
      this.paused = true;
      instances.push(this);
    }

    play() {
      this.paused = false;
      if (playRejects) return Promise.reject(new Error('blocked'));
      this.onplaying?.();
      return Promise.resolve();
    }

    pause() {
      this.paused = true;
    }
  }
  vi.stubGlobal('Audio', FakeAudio);
  return instances;
}

afterEach(() => {
  stopAudio();
  vi.unstubAllGlobals();
});

describe('playAudio', () => {
  it('rejects without creating an element when there is no audio url', async () => {
    const instances = installFakeAudio();
    await expect(playAudio(null)).rejects.toThrow('No audio available');
    expect(instances).toHaveLength(0);
  });

  it('plays the given url and resolves when playback ends', async () => {
    const instances = installFakeAudio();
    const onPlaying = vi.fn();
    const done = playAudio('/api/audio/abc.mp3', { onPlaying });
    expect(instances[0].url).toBe('/api/audio/abc.mp3');
    instances[0].onended();
    await expect(done).resolves.toBeUndefined();
    expect(onPlaying).toHaveBeenCalledTimes(1);
  });

  it('rejects when the file fails to load, such as a 503 from the audio route', async () => {
    const instances = installFakeAudio();
    const done = playAudio('/api/audio/abc.mp3');
    instances[0].onerror();
    await expect(done).rejects.toThrow('Audio could not be loaded');
  });

  it('rejects when the browser blocks playback', async () => {
    installFakeAudio({ playRejects: true });
    await expect(playAudio('/api/audio/abc.mp3')).rejects.toThrow('blocked');
  });

  it('stops the previous clip when a new one starts', async () => {
    const instances = installFakeAudio();
    const first = playAudio('/api/audio/one.mp3');
    const second = playAudio('/api/audio/two.mp3');
    await expect(first).resolves.toBeUndefined();
    expect(instances[0].paused).toBe(true);
    instances[1].onended();
    await expect(second).resolves.toBeUndefined();
  });
});
