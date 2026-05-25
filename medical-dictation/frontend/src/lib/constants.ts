const normalizeUrl = (value: string) => value.replace(/\/+$/, '');

const normalizeLoopbackBackendUrl = (value: string) => {
  try {
    const url = new URL(value);
    if (url.hostname === 'localhost') {
      url.hostname = '127.0.0.1';
    }
    return normalizeUrl(url.toString());
  } catch {
    return normalizeUrl(value);
  }
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://127.0.0.1:8000/ws/audio';

export const API_URL = normalizeLoopbackBackendUrl(apiUrl);
export const WS_URL = (() => {
  const normalized = normalizeLoopbackBackendUrl(wsUrl);
  return normalized.endsWith('/ws/audio')
    ? normalized
    : `${normalized}/ws/audio`;
})();

export const AUDIO_SAMPLE_RATE = 16000;
export const AUDIO_CHUNK_INTERVAL = 250;
export const BROWSER_SAMPLE_RATE = 44100;
export const AUTO_SAVE_INTERVAL = 30000;
export const MAX_SESSIONS = 50;
export const TOAST_DURATION = 3000;
