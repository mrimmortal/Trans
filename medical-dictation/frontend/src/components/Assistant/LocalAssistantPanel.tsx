'use client';

import { Bot, Loader2, Play, Volume2, X } from 'lucide-react';

interface LocalAssistantPanelProps {
  responseText: string;
  error: string | null;
  isGeneratingResponse: boolean;
  isGeneratingSpeech: boolean;
  isBusy: boolean;
  hasAudio: boolean;
  onRun: () => void;
  onReplay: () => void;
  onClear: () => void;
}

export function LocalAssistantPanel({
  responseText,
  error,
  isGeneratingResponse,
  isGeneratingSpeech,
  isBusy,
  hasAudio,
  onRun,
  onReplay,
  onClear,
}: LocalAssistantPanelProps) {
  const statusText = isGeneratingResponse
    ? 'Generating response...'
    : isGeneratingSpeech
      ? 'Generating speech...'
      : null;

  return (
    <section className="mx-4 sm:mx-6 mt-4 border border-gray-200 rounded-lg bg-gray-50">
      <div className="px-4 py-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-blue-600" />
          <h2 className="text-sm font-semibold text-gray-900">Local Assistant</h2>
          {statusText && (
            <span className="inline-flex items-center gap-1.5 text-xs text-blue-700">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              {statusText}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {hasAudio && (
            <button
              type="button"
              onClick={onReplay}
              disabled={isBusy}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-gray-300 text-gray-700 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="w-3.5 h-3.5" />
              Replay
            </button>
          )}
          {(responseText || error) && (
            <button
              type="button"
              onClick={onClear}
              disabled={isBusy}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-gray-300 text-gray-700 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <X className="w-3.5 h-3.5" />
              Clear
            </button>
          )}
          <button
            type="button"
            onClick={onRun}
            disabled={isBusy}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Volume2 className="w-3.5 h-3.5" />
            Ask Assistant
          </button>
        </div>
      </div>

      {(responseText || error) && (
        <div className="border-t border-gray-200 px-4 py-3">
          {error ? (
            <p className="text-sm font-medium text-red-700" role="alert">
              {error}
            </p>
          ) : (
            <p className="max-h-40 overflow-y-auto whitespace-pre-wrap text-sm text-gray-800">
              {responseText}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
