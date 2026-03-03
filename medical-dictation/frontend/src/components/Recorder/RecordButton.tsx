'use client';

import { Mic, Square, Pause, Play } from 'lucide-react';

interface RecordButtonProps {
  isRecording: boolean;
  isPaused: boolean;
  duration: number;
  onStartRecording: () => void;
  onStopRecording: () => void;
  onPauseRecording: () => void;
  onResumeRecording: () => void;
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

export function RecordButton({
  isRecording,
  isPaused,
  duration,
  onStartRecording,
  onStopRecording,
  onPauseRecording,
  onResumeRecording,
}: RecordButtonProps) {
  return (
    <div className="flex flex-col items-center gap-4">
      <div className="flex items-end gap-3">
        {/* Main record button */}
        <div className="relative">
          {isRecording && (
            <div className="absolute inset-0 w-20 h-20 rounded-full bg-red-400 opacity-75 animate-ping" />
          )}
          <button
            onClick={isRecording ? onStopRecording : onStartRecording}
            className={`relative w-20 h-20 rounded-full flex items-center justify-center text-white font-semibold transition-all transform ${isRecording
                ? 'bg-red-500 hover:bg-red-600 hover:scale-105'
                : 'bg-blue-500 hover:bg-blue-600 hover:scale-105'
              }`}
            aria-label={isRecording ? 'Stop recording' : 'Start recording'}
          >
            {isRecording ? (
              <Square className="w-10 h-10 fill-current" />
            ) : (
              <Mic className="w-10 h-10" />
            )}
          </button>
        </div>

        {/* Pause/Resume button when recording */}
        {isRecording && (
          <button
            onClick={isPaused ? onResumeRecording : onPauseRecording}
            className="w-10 h-10 rounded-full bg-gray-500 hover:bg-gray-600 text-white flex items-center justify-center transition-all transform hover:scale-105"
            aria-label={isPaused ? 'Resume recording' : 'Pause recording'}
          >
            {isPaused ? (
              <Play className="w-5 h-5" />
            ) : (
              <Pause className="w-5 h-5" />
            )}
          </button>
        )}
      </div>

      {/* Duration display */}
      <div className="text-center">
        <div className="text-lg font-mono font-bold text-gray-900">
          {formatDuration(duration)}
        </div>
        <div className="text-sm text-gray-600 mt-1">
          {!isRecording && 'Click to start'}
          {isRecording && !isPaused && 'Recording...'}
          {isRecording && isPaused && 'Paused'}
        </div>
      </div>
    </div>
  );
}
