import { API_URL } from '@/lib/constants';
import { TTSApiErrorCode, TTSSynthesizeRequest, TTSSynthesizeResult } from '@/types';
import { createRequestId } from '@/services/requestId';

interface BackendErrorDetail {
  code?: string;
  message?: string;
  request_id?: string;
}

export class TTSApiError extends Error {
  constructor(
    public readonly code: TTSApiErrorCode,
    message: string,
    public readonly requestId?: string
  ) {
    super(message);
    this.name = 'TTSApiError';
  }
}

export async function synthesizeSpeech(text: string): Promise<TTSSynthesizeResult> {
  const cleanText = text.trim();
  if (!cleanText) {
    throw new TTSApiError('REQUEST_FAILED', 'Assistant response is empty.');
  }

  const payload: TTSSynthesizeRequest = { text: cleanText };
  const requestId = createRequestId('tts');
  const response = await fetch(`${API_URL}/tts/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-request-id': requestId },
    body: JSON.stringify(payload),
  });
  const responseRequestId = response.headers.get('x-request-id') || requestId;

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    const message = detail.message || 'Speech synthesis failed.';
    const errorRequestId = detail.request_id || responseRequestId;

    if (detail.code === 'TTS_CONFIG_ERROR' || detail.code === 'TTS_SYNTHESIS_ERROR') {
      throw new TTSApiError('TTS_UNAVAILABLE', message, errorRequestId);
    }

    throw new TTSApiError('REQUEST_FAILED', message, errorRequestId);
  }

  const blob = await response.blob();
  if (blob.size === 0) {
    throw new TTSApiError('TTS_UNAVAILABLE', 'TTS returned empty audio.', responseRequestId);
  }

  return { audioUrl: URL.createObjectURL(blob), request_id: responseRequestId };
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
