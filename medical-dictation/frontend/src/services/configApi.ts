import { API_URL } from '@/lib/constants';
import { BackendConfigResponse } from '@/types';

export class ConfigApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConfigApiError';
  }
}

export async function getBackendConfig(): Promise<BackendConfigResponse> {
  const response = await fetch(`${API_URL}/config`);

  if (!response.ok) {
    throw new ConfigApiError('Backend config request failed.');
  }

  return (await response.json()) as BackendConfigResponse;
}
