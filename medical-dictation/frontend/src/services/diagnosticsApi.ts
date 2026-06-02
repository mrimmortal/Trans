import { API_URL } from '@/lib/constants';
import { DiagnosticsResponse } from '@/types';
import { createRequestId } from '@/services/requestId';

export class DiagnosticsApiError extends Error {
  constructor(message: string, public readonly requestId?: string) {
    super(message);
    this.name = 'DiagnosticsApiError';
  }
}

async function getDiagnosticsPath(path: string): Promise<DiagnosticsResponse> {
  const requestId = createRequestId('diagnostics');
  const response = await fetch(`${API_URL}${path}`, {
    headers: { 'x-request-id': requestId },
  });
  const responseRequestId = response.headers.get('x-request-id') || requestId;

  if (!response.ok) {
    throw new DiagnosticsApiError('Diagnostics request failed.', responseRequestId);
  }

  const body = (await response.json()) as DiagnosticsResponse;
  return { ...body, request_id: body.request_id || responseRequestId };
}

export function getDiagnostics(): Promise<DiagnosticsResponse> {
  return getDiagnosticsPath('/diagnostics');
}

export function getSttDiagnostics(): Promise<DiagnosticsResponse> {
  return getDiagnosticsPath('/diagnostics/stt');
}

export function getLlmDiagnostics(): Promise<DiagnosticsResponse> {
  return getDiagnosticsPath('/diagnostics/llm');
}

export function getTtsDiagnostics(): Promise<DiagnosticsResponse> {
  return getDiagnosticsPath('/diagnostics/tts');
}
