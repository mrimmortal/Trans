'use client';

import { useState } from 'react';
import { DiagnosticsResponse } from '@/types';

interface DeveloperDiagnosticsPanelProps {
  diagnostics: DiagnosticsResponse | null;
  websocketStatus: string;
  assistantStatus: string;
  assistantRequestId: string | null;
  assistantError: string | null;
  isChecking: boolean;
  lastError: string | null;
  lastRequestId: string | null;
  onCheckBackend: () => void;
  onCheckLlm: () => void;
  onCheckTts: () => void;
  onCopyDebugInfo: () => void;
}

export function DeveloperDiagnosticsPanel({
  diagnostics,
  websocketStatus,
  assistantStatus,
  assistantRequestId,
  assistantError,
  isChecking,
  lastError,
  lastRequestId,
  onCheckBackend,
  onCheckLlm,
  onCheckTts,
  onCopyDebugInfo,
}: DeveloperDiagnosticsPanelProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <section className="mx-4 sm:mx-6 mt-3 border border-gray-200 rounded-lg bg-white">
      <button
        type="button"
        onClick={() => setIsOpen((value) => !value)}
        className="w-full px-4 py-2 text-left text-xs font-semibold text-gray-700"
      >
        Developer Diagnostics {isOpen ? 'Hide' : 'Show'}
      </button>

      {isOpen && (
        <div className="border-t border-gray-200 px-4 py-3 space-y-3 text-xs text-gray-700">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <Status label="Backend" value={diagnostics?.status || 'unknown'} />
            <Status label="WebSocket" value={websocketStatus} />
            <Status label="LLM" value={diagnostics?.llm?.status || 'unknown'} />
            <Status label="TTS" value={diagnostics?.tts?.status || 'unknown'} />
          </div>

          <div className="grid gap-1 sm:grid-cols-2">
            <div>Assistant: {assistantStatus}</div>
            <div>Last request: {assistantRequestId || lastRequestId || 'none'}</div>
            <div>STT: {diagnostics?.stt?.status || 'unknown'}</div>
            <div>Error: {assistantError || lastError || 'none'}</div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={onCheckBackend} disabled={isChecking} className="px-2 py-1 rounded border border-gray-300 disabled:opacity-50">
              Check Backend
            </button>
            <button type="button" onClick={onCheckLlm} disabled={isChecking} className="px-2 py-1 rounded border border-gray-300 disabled:opacity-50">
              Check LLM
            </button>
            <button type="button" onClick={onCheckTts} disabled={isChecking} className="px-2 py-1 rounded border border-gray-300 disabled:opacity-50">
              Check TTS
            </button>
            <button type="button" onClick={onCopyDebugInfo} className="px-2 py-1 rounded border border-gray-300">
              Copy Debug Info
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function Status({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2 rounded border border-gray-100 px-2 py-1">
      <span>{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
