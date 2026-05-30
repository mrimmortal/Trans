import { API_URL } from '@/lib/constants';
import { AssistantApiErrorCode, LLMRespondRequest, LLMRespondResponse } from '@/types';

interface BackendErrorDetail {
  code?: string;
  message?: string;
}

export class AssistantApiError extends Error {
  constructor(
    public readonly code: AssistantApiErrorCode,
    message: string
  ) {
    super(message);
    this.name = 'AssistantApiError';
  }
}

export async function requestAssistantResponse(text: string): Promise<LLMRespondResponse> {
  const cleanText = text.trim();
  if (!cleanText) {
    throw new AssistantApiError('REQUEST_FAILED', 'Transcript is empty.');
  }

  const payload: LLMRespondRequest = { text: cleanText };
  const response = await fetch(`${API_URL}/llm/respond`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    const message = detail.message || 'LM Studio request failed.';

    if (detail.code === 'LM_STUDIO_CONFIG_ERROR' || detail.code === 'LM_STUDIO_UNAVAILABLE') {
      throw new AssistantApiError('LM_STUDIO_UNAVAILABLE', message);
    }

    throw new AssistantApiError('REQUEST_FAILED', message);
  }

  return response.json() as Promise<LLMRespondResponse>;
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
