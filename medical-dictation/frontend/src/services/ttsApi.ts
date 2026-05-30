import { API_URL } from '@/lib/constants';
import { TTSApiErrorCode, TTSSynthesizeRequest } from '@/types';

interface BackendErrorDetail {
  code?: string;
  message?: string;
}

export class TTSApiError extends Error {
  constructor(
    public readonly code: TTSApiErrorCode,
    message: string
  ) {
    super(message);
    this.name = 'TTSApiError';
  }
}

export async function synthesizeSpeech(text: string): Promise<string> {
  const cleanText = text.trim();
  if (!cleanText) {
    throw new TTSApiError('REQUEST_FAILED', 'Assistant response is empty.');
  }

  const payload: TTSSynthesizeRequest = { text: cleanText };
  const response = await fetch(`${API_URL}/tts/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    const message = detail.message || 'Speech synthesis failed.';

    if (detail.code === 'TTS_CONFIG_ERROR' || detail.code === 'TTS_SYNTHESIS_ERROR') {
      throw new TTSApiError('TTS_UNAVAILABLE', message);
    }

    throw new TTSApiError('REQUEST_FAILED', message);
  }

  const blob = await response.blob();
  if (blob.size === 0) {
    throw new TTSApiError('TTS_UNAVAILABLE', 'TTS returned empty audio.');
  }

  return URL.createObjectURL(blob);
}

async function readErrorDetail(response: Response): Promise<BackendErrorDetail> {
  try {
    const body = await response.json();
    if (body && typeof body.detail === 'object') {
      return body.detail;
    }
  } catch {
    return {};
  }

  return {};
}
