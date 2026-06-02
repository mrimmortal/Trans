import { API_URL } from '@/lib/constants';
import { AssistantApiErrorCode, LLMRespondRequest, LLMRespondResponse } from '@/types';
import { createRequestId } from '@/services/requestId';

interface BackendErrorDetail {
  code?: string;
  message?: string;
  request_id?: string;
}

export class AssistantApiError extends Error {
  constructor(
    public readonly code: AssistantApiErrorCode,
    message: string,
    public readonly requestId?: string
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
  const requestId = createRequestId('llm');
  const response = await fetch(`${API_URL}/llm/respond`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-request-id': requestId },
    body: JSON.stringify(payload),
  });
  const responseRequestId = response.headers.get('x-request-id') || requestId;

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    const message = detail.message || 'LM Studio request failed.';
    const errorRequestId = detail.request_id || responseRequestId;

    if (detail.code === 'LM_STUDIO_CONFIG_ERROR' || detail.code === 'LM_STUDIO_UNAVAILABLE') {
      throw new AssistantApiError('LM_STUDIO_UNAVAILABLE', message, errorRequestId);
    }

    throw new AssistantApiError('REQUEST_FAILED', message, errorRequestId);
  }

  const body = (await response.json()) as LLMRespondResponse;
  return { ...body, request_id: responseRequestId };
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
