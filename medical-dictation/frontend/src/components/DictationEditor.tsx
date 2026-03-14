// components/DictationEditor.tsx
'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import { useCommandHandler } from '../hooks/useCommandHandler';
import { VoiceCommand } from '../types';

// ══════════════════════════════════════════════════════════════════
// ICONS (inline SVG to avoid dependencies)
// ══════════════════════════════════════════════════════════════════

const MicrophoneIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
  </svg>
);

const StopIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24">
    <rect x="6" y="6" width="12" height="12" rx="2" />
  </svg>
);

const SaveIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
  </svg>
);

const TrashIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
  </svg>
);

const CopyIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
  </svg>
);

const CommandIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
  </svg>
);

// ══════════════════════════════════════════════════════════════════
// COMPONENT PROPS
// ══════════════════════════════════════════════════════════════════

interface DictationEditorProps {
  wsUrl?: string;
  placeholder?: string;
  initialText?: string;
  onTextChange?: (text: string) => void;
  onSave?: (text: string) => void;
  className?: string;
}

// ══════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════════════════════════════════

export function DictationEditor({
  wsUrl = 'ws://localhost:8000/ws/audio',
  placeholder = 'Start dictating... Try saying "period", "new paragraph", "insert vitals template"',
  initialText = '',
  onTextChange,
  onSave,
  className = '',
}: DictationEditorProps) {
  // ══════════════════════════════════════════════════════════
  // STATE
  // ══════════════════════════════════════════════════════════
  
  const [text, setText] = useState(initialText);
  const [commandNotification, setCommandNotification] = useState<string | null>(null);
  const [showCommands, setShowCommands] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const textHistoryRef = useRef<string[]>([initialText]);
  const historyIndexRef = useRef(0);

  // ══════════════════════════════════════════════════════════
  // WEBSOCKET CONNECTION
  // ══════════════════════════════════════════════════════════
  
  const {
    isConnected,
    isConnecting,
    error: wsError,
    lastTranscription,
    lastCommands,
    availableCommands,
    commandsEnabled,
    connect,
    disconnect,
    sendBinary,
    reset,
    flush,
    enableCommands,
    disableCommands,
    registerCustomCommand,
  } = useWebSocket(wsUrl);

  // ══════════════════════════════════════════════════════════
  // AUDIO RECORDER
  // ══════════════════════════════════════════════════════════
  
  const {
    isRecording,
    audioLevel,
    error: audioError,
    startRecording,
    stopRecording,
  } = useAudioRecorder({
    sampleRate: 16000,
    channelCount: 1,
    chunkIntervalMs: 100,
    onAudioData: (data) => {
      if (isConnected) {
        sendBinary(data);
      }
    },
    onError: (error) => {
      console.error('[DictationEditor] Audio error:', error);
    },
  });

  // ══════════════════════════════════════════════════════════
  // TEXT MANAGEMENT
  // ══════════════════════════════════════════════════════════
  
  const updateText = useCallback((newText: string) => {
    setText(newText);
    onTextChange?.(newText);
    
    // Add to history for undo/redo
    const history = textHistoryRef.current;
    const currentIndex = historyIndexRef.current;
    
    // Remove any "future" history if we're not at the end
    if (currentIndex < history.length - 1) {
      textHistoryRef.current = history.slice(0, currentIndex + 1);
    }
    
    // Add new state
    textHistoryRef.current.push(newText);
    historyIndexRef.current = textHistoryRef.current.length - 1;
    
    // Limit history size
    if (textHistoryRef.current.length > 100) {
      textHistoryRef.current.shift();
      historyIndexRef.current--;
    }
  }, [onTextChange]);

  const handleUndo = useCallback(() => {
    const history = textHistoryRef.current;
    const currentIndex = historyIndexRef.current;
    
    if (currentIndex > 0) {
      historyIndexRef.current--;
      const previousText = history[historyIndexRef.current];
      setText(previousText);
      onTextChange?.(previousText);
    }
  }, [onTextChange]);

  const handleRedo = useCallback(() => {
    const history = textHistoryRef.current;
    const currentIndex = historyIndexRef.current;
    
    if (currentIndex < history.length - 1) {
      historyIndexRef.current++;
      const nextText = history[historyIndexRef.current];
      setText(nextText);
      onTextChange?.(nextText);
    }
  }, [onTextChange]);

  const handleDeleteLastWord = useCallback(() => {
    updateText(text.replace(/\s*\S+\s*$/, ''));
  }, [text, updateText]);

  const handleDeleteLastSentence = useCallback(() => {
    // Remove last sentence (ending with . ! or ?)
    const newText = text.replace(/[^.!?]*[.!?]\s*$/, '').trim();
    updateText(newText);
  }, [text, updateText]);

  const handleDeleteLastParagraph = useCallback(() => {
    // Remove last paragraph
    const paragraphs = text.split(/\n\n+/);
    paragraphs.pop();
    updateText(paragraphs.join('\n\n'));
  }, [text, updateText]);

  const handleClearAll = useCallback(() => {
    if (confirm('Are you sure you want to clear all text?')) {
      updateText('');
    }
  }, [updateText]);

  const handleGoToStart = useCallback(() => {
    if (textareaRef.current) {
      textareaRef.current.setSelectionRange(0, 0);
      textareaRef.current.scrollTop = 0;
      textareaRef.current.focus();
    }
  }, []);

  const handleGoToEnd = useCallback(() => {
    if (textareaRef.current) {
      const len = textareaRef.current.value.length;
      textareaRef.current.setSelectionRange(len, len);
      textareaRef.current.scrollTop = textareaRef.current.scrollHeight;
      textareaRef.current.focus();
    }
  }, []);

  const handleSave = useCallback(() => {
    if (onSave) {
      onSave(text);
    } else {
      // Default: save to localStorage
      localStorage.setItem('dictation_draft', text);
      localStorage.setItem('dictation_draft_time', new Date().toISOString());
    }
    setCommandNotification('Document saved!');
    setTimeout(() => setCommandNotification(null), 2000);
  }, [text, onSave]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [text]);

  // ══════════════════════════════════════════════════════════
  // COMMAND HANDLER
  // ══════════════════════════════════════════════════════════
  
  useCommandHandler(lastCommands, {
    onUndo: handleUndo,
    onRedo: handleRedo,
    onDeleteLastWord: handleDeleteLastWord,
    onDeleteLastSentence: handleDeleteLastSentence,
    onDeleteLastParagraph: handleDeleteLastParagraph,
    onClearAll: handleClearAll,
    onGoToStart: handleGoToStart,
    onGoToEnd: handleGoToEnd,
    onSave: handleSave,
    onPause: stopRecording,
    onResume: startRecording,
    onScrollUp: () => {
      if (textareaRef.current) {
        textareaRef.current.scrollTop -= 100;
      }
    },
    onScrollDown: () => {
      if (textareaRef.current) {
        textareaRef.current.scrollTop += 100;
      }
    },
    onAnyCommand: (cmd) => {
      // Show notification for commands
      if (cmd.action !== 'punctuation') {
        setCommandNotification(`Command: ${cmd.action.replace(/_/g, ' ')}`);
        setTimeout(() => setCommandNotification(null), 1500);
      }
    },
  });

  // ══════════════════════════════════════════════════════════
  // EFFECTS
  // ══════════════════════════════════════════════════════════
  
  // Connect on mount
  useEffect(() => {
    connect();
    
    // Load draft from localStorage
    const savedDraft = localStorage.getItem('dictation_draft');
    if (savedDraft && !initialText) {
      setText(savedDraft);
      textHistoryRef.current = [savedDraft];
    }
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect, initialText]);

  // Register custom commands when connected
  useEffect(() => {
    if (isConnected) {
      // Register custom signature
      registerCustomCommand({
        pattern: 'my signature',
        replacement: '\n\n— Dictated using Medical Dictation AI\n',
      });
    }
  }, [isConnected, registerCustomCommand]);

  // Handle transcription updates
  useEffect(() => {
    if (lastTranscription) {
      updateText((prevText) => {
        // Smart appending
        const needsSpace = prevText.length > 0 && 
                          !prevText.endsWith('\n') && 
                          !prevText.endsWith(' ') &&
                          !lastTranscription.startsWith('\n');
        return prevText + (needsSpace ? ' ' : '') + lastTranscription;
      });
      
      // Scroll to bottom
      if (textareaRef.current) {
        textareaRef.current.scrollTop = textareaRef.current.scrollHeight;
      }
    }
  }, [lastTranscription, updateText]);

  // ══════════════════════════════════════════════════════════
  // RENDER HELPERS
  // ══════════════════════════════════════════════════════════
  
  const getStatusColor = () => {
    if (!isConnected) return 'bg-red-500';
    if (isRecording) return 'bg-green-500 animate-pulse';
    return 'bg-green-500';
  };

  const getStatusText = () => {
    if (isConnecting) return 'Connecting...';
    if (!isConnected) return 'Disconnected';
    if (isRecording) return 'Recording...';
    return 'Ready';
  };

  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;
  const charCount = text.length;

  // ══════════════════════════════════════════════════════════
  // RENDER
  // ══════════════════════════════════════════════════════════
  
  return (
    <div className={`flex flex-col h-full bg-white rounded-lg shadow-lg overflow-hidden ${className}`}>
      {/* ════════════════════════════════════════════════════════ */}
      {/* HEADER */}
      {/* ════════════════════════════════════════════════════════ */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b">
        {/* Status */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className={`w-2.5 h-2.5 rounded-full ${getStatusColor()}`} />
            <span className="text-sm font-medium text-gray-600">{getStatusText()}</span>
          </div>
          
          {/* Audio level indicator */}
          {isRecording && (
            <div className="flex items-center gap-1">
              {[...Array(5)].map((_, i) => (
                <div
                  key={i}
                  className={`w-1 rounded-full transition-all duration-75 ${
                    audioLevel > i * 0.2 ? 'bg-green-500' : 'bg-gray-300'
                  }`}
                  style={{ height: `${8 + i * 3}px` }}
                />
              ))}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {/* Commands toggle */}
          <button
            onClick={() => commandsEnabled ? disableCommands() : enableCommands()}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
              commandsEnabled 
                ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' 
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}
            title={commandsEnabled ? 'Disable voice commands' : 'Enable voice commands'}
          >
            <CommandIcon className="w-4 h-4" />
            <span className="hidden sm:inline">Commands</span>
          </button>

          {/* Show commands help */}
          <button
            onClick={() => setShowCommands(!showCommands)}
            className="px-3 py-1.5 text-sm text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
          >
            {showCommands ? 'Hide Help' : 'Show Help'}
          </button>

          {/* Copy button */}
          <button
            onClick={handleCopy}
            className={`p-2 rounded-md transition-colors ${
              copySuccess ? 'bg-green-100 text-green-600' : 'text-gray-500 hover:bg-gray-100'
            }`}
            title="Copy all text"
          >
            <CopyIcon className="w-5 h-5" />
          </button>

          {/* Save button */}
          <button
            onClick={handleSave}
            className="p-2 text-gray-500 hover:bg-gray-100 rounded-md transition-colors"
            title="Save document"
          >
            <SaveIcon className="w-5 h-5" />
          </button>

          {/* Clear button */}
          <button
            onClick={handleClearAll}
            className="p-2 text-gray-500 hover:bg-red-100 hover:text-red-600 rounded-md transition-colors"
            title="Clear all text"
          >
            <TrashIcon className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* ════════════════════════════════════════════════════════ */}
      {/* ERROR DISPLAY */}
      {/* ════════════════════════════════════════════════════════ */}
      {(wsError || audioError) && (
        <div className="px-4 py-2 bg-red-50 border-b border-red-100 text-red-700 text-sm">
          {wsError || audioError}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════ */}
      {/* COMMAND NOTIFICATION */}
      {/* ════════════════════════════════════════════════════════ */}
      {commandNotification && (
        <div className="px-4 py-2 bg-blue-50 border-b border-blue-100 text-blue-700 text-sm flex items-center gap-2">
          <CommandIcon className="w-4 h-4" />
          {commandNotification}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════ */}
      {/* AVAILABLE COMMANDS PANEL */}
      {/* ════════════════════════════════════════════════════════ */}
      {showCommands && availableCommands && (
        <div className="px-4 py-3 bg-gray-50 border-b max-h-60 overflow-y-auto">
          <h3 className="font-semibold text-gray-700 mb-2">Available Voice Commands</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 text-sm">
            {Object.entries(availableCommands).map(([category, commands]) => (
              <div key={category}>
                <h4 className="font-medium text-gray-600 capitalize mb-1">{category}</h4>
                <ul className="space-y-0.5 text-gray-500">
                  {commands.slice(0, 6).map((cmd, i) => (
                    <li key={i} className="truncate">"{cmd}"</li>
                  ))}
                  {commands.length > 6 && (
                    <li className="text-gray-400">+{commands.length - 6} more</li>
                  )}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════ */}
      {/* TEXT EDITOR */}
      {/* ════════════════════════════════════════════════════════ */}
      <div className="flex-1 relative">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => updateText(e.target.value)}
          placeholder={placeholder}
          className="w-full h-full p-4 resize-none focus:outline-none text-gray-800 placeholder-gray-400"
          style={{ minHeight: '300px' }}
        />
      </div>

      {/* ════════════════════════════════════════════════════════ */}
      {/* FOOTER */}
      {/* ════════════════════════════════════════════════════════ */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-t">
        {/* Word count */}
        <div className="text-sm text-gray-500">
          {wordCount} words · {charCount} characters
        </div>

        {/* Record button */}
        <button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={!isConnected}
          className={`flex items-center gap-2 px-6 py-2.5 rounded-full font-medium transition-all ${
            isRecording
              ? 'bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-200'
              : isConnected
                ? 'bg-blue-500 hover:bg-blue-600 text-white shadow-lg shadow-blue-200'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}
        >
          {isRecording ? (
            <>
              <StopIcon className="w-5 h-5" />
              Stop Recording
            </>
          ) : (
            <>
              <MicrophoneIcon className="w-5 h-5" />
              Start Recording
            </>
          )}
        </button>

        {/* Flush button */}
        <button
          onClick={flush}
          disabled={!isConnected}
          className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded-md transition-colors disabled:opacity-50"
        >
          Flush Buffer
        </button>
      </div>
    </div>
  );
}

export default DictationEditor;