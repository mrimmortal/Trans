'use client';

import { useCallback, useState } from 'react';
import {
  DiagnosticsApiError,
  getDiagnostics,
  getLlmDiagnostics,
  getTtsDiagnostics,
} from '@/services/diagnosticsApi';
import { DiagnosticsResponse } from '@/types';

interface DiagnosticsContext {
  websocketStatus: string;
  assistantStatus: string;
  assistantRequestId: string | null;
  assistantError: string | null;
}

export function useDiagnostics(context: DiagnosticsContext) {
  const [diagnostics, setDiagnostics] = useState<DiagnosticsResponse | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);
  const [lastRequestId, setLastRequestId] = useState<string | null>(null);

  const runCheck = useCallback(async (check: () => Promise<DiagnosticsResponse>) => {
    setIsChecking(true);
    setLastError(null);
    try {
      const result = await check();
      setDiagnostics((prev) => ({ ...(prev || {}), ...result }));
      setLastRequestId(result.request_id);
    } catch (error) {
      const requestId = error instanceof DiagnosticsApiError ? error.requestId || null : null;
      setLastRequestId(requestId);
      setLastError('Diagnostics request failed.');
    } finally {
      setIsChecking(false);
    }
  }, []);

  const checkBackend = useCallback(() => runCheck(getDiagnostics), [runCheck]);
  const checkLlm = useCallback(() => runCheck(getLlmDiagnostics), [runCheck]);
  const checkTts = useCallback(() => runCheck(getTtsDiagnostics), [runCheck]);

  const copyDebugInfo = useCallback(async () => {
    const debugInfo = {
      diagnostics,
      websocket_status: context.websocketStatus,
      assistant_status: context.assistantStatus,
      assistant_request_id: context.assistantRequestId,
      assistant_error: context.assistantError,
      diagnostics_request_id: lastRequestId,
    };

    await navigator.clipboard.writeText(JSON.stringify(debugInfo, null, 2));
  }, [context.assistantError, context.assistantRequestId, context.assistantStatus, context.websocketStatus, diagnostics, lastRequestId]);

  return {
    diagnostics,
    isChecking,
    lastError,
    lastRequestId,
    checkBackend,
    checkLlm,
    checkTts,
    copyDebugInfo,
  };
}
