'use client';

import { useRef, useEffect, useState, useCallback } from 'react';
import { Header } from '@/components/Header/Header';
import { Toolbar } from '@/components/Editor/Toolbar';
import { DictationEditor, DictationEditorHandle } from '@/components/Editor/DictationEditor';
import { RecordButton } from '@/components/Recorder/RecordButton';
import { AudioVisualizer } from '@/components/Recorder/AudioVisualizer';
import { Sidebar } from '@/components/Sidebar/Sidebar';
import { SettingsModal } from '@/components/Settings/SettingsModal';
import { Session } from '@/components/Sidebar/SessionHistory';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAudioRecorder } from '@/hooks/useAudioRecorder';
import { useVoiceCommands } from '@/hooks/useVoiceCommands';
import { useSettings } from '@/hooks/useSettings';
import { useToast } from '@/components/ui/Toast';
import { WS_URL } from '@/lib/constants';
import { DEFAULT_MACROS } from '@/lib/defaultMacros';
import { Macro } from '@/types';
import { X, AlertTriangle, RefreshCw, Keyboard } from 'lucide-react';

// Keyboard shortcut definitions for help modal
const KEYBOARD_SHORTCUTS = [
  { keys: ['Ctrl/⌘', 'Shift', 'R'], description: 'Toggle recording on/off' },
  { keys: ['Ctrl/⌘', 'Shift', 'P'], description: 'Pause/Resume recording' },
  { keys: ['Ctrl/⌘', 'S'], description: 'Save session' },
  { keys: ['Ctrl/⌘', 'Shift', 'C'], description: 'Copy all text' },
  { keys: ['Escape'], description: 'Stop recording' },
  { keys: ['?'], description: 'Show/hide this help' },
];

export default function Page() {
  // Hooks
  const { isConnected, isConnecting, lastMessage, error: wsError, connect, disconnect, sendBinary } = useWebSocket(WS_URL);
  const { isRecording, isPaused, duration, audioLevel, error: recorderError, startRecording, stopRecording, pauseRecording, resumeRecording } = useAudioRecorder();
  const { processText } = useVoiceCommands();
  const { settings, updateSettings } = useSettings();
  const { showToast } = useToast();

  // State
  const [processedText, setProcessedText] = useState<string | null>(null);
  const [wordCount, setWordCount] = useState(0);
  const [charCount, setCharCount] = useState(0);
  const [dismissedErrors, setDismissedErrors] = useState<Set<string>>(new Set());
  const [macros, setMacros] = useState<Macro[]>(DEFAULT_MACROS);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [autoSaveTimestamp, setAutoSaveTimestamp] = useState<string | null>(null);
  const [showAutoSaveRestore, setShowAutoSaveRestore] = useState(false);
  const [restoredAutoSave, setRestoredAutoSave] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [isAppLoading, setIsAppLoading] = useState(true);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [microphoneError, setMicrophoneError] = useState<string | null>(null);
  const [browserSupported, setBrowserSupported] = useState(true);
  const [retryCount, setRetryCount] = useState(0);
  const [isInitializingMicrophone, setIsInitializingMicrophone] = useState(false);
  const [recordingStatusAnnouncement, setRecordingStatusAnnouncement] = useState('');

  const editorRef = useRef<DictationEditorHandle>(null);
  const connectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load macros, sessions, and auto-save from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const savedMacros = localStorage.getItem('medDictateMacros');
      if (savedMacros) {
        try {
          setMacros(JSON.parse(savedMacros));
        } catch (e) {
          console.warn('Failed to load macros from localStorage:', e);
          setMacros(DEFAULT_MACROS);
        }
      }

      const savedSessions = localStorage.getItem('medDictateSessions');
      if (savedSessions) {
        try {
          setSessions(JSON.parse(savedSessions));
        } catch (e) {
          console.warn('Failed to load sessions from localStorage:', e);
          setSessions([]);
        }
      }

      // Check for auto-save and restore if < 24 hours old
      const autoSaveData = localStorage.getItem('medDictateAutoSave');
      if (autoSaveData && !restoredAutoSave) {
        try {
          const { content: _content, timestamp } = JSON.parse(autoSaveData);
          const savedTime = new Date(timestamp).getTime();
          const now = new Date().getTime();
          const hoursOld = (now - savedTime) / (1000 * 60 * 60);

          if (hoursOld < 24) {
            setShowAutoSaveRestore(true);
          } else {
            localStorage.removeItem('medDictateAutoSave');
          }
        } catch (e) {
          console.warn('Failed to parse auto-save:', e);
          localStorage.removeItem('medDictateAutoSave');
        }
      }
    }
  }, [restoredAutoSave]);

  // Browser support check and app loading state
  useEffect(() => {
    const hasMediaRecorder = typeof window !== 'undefined' && typeof window.MediaRecorder !== 'undefined';
    const hasAudioContext = typeof window !== 'undefined' && (window.AudioContext || (window as any).webkitAudioContext);

    if (!hasMediaRecorder || !hasAudioContext) {
      setBrowserSupported(false);
    }

    const timer = setTimeout(() => {
      setIsAppLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  // Get current date
  const currentDate = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  // Handler: Start recording
  const handleStartRecording = useCallback(async () => {
    setProcessedText(null);
    setIsInitializingMicrophone(true);
    setMicrophoneError(null);

    try {
      connect();

      if (connectTimeoutRef.current) clearTimeout(connectTimeoutRef.current);
      connectTimeoutRef.current = setTimeout(() => {
        startRecording((chunk) => {
          sendBinary(chunk);
        });
        setIsInitializingMicrophone(false);
        setRecordingStatusAnnouncement('Recording started');
      }, 500);
    } catch (err: any) {
      setIsInitializingMicrophone(false);
      if (err.name === 'NotAllowedError') {
        setMicrophoneError('Microphone access denied. Please allow microphone access in your browser settings.');
        showToast('Microphone access denied', 'error');
      } else if (err.name === 'NotFoundError') {
        setMicrophoneError('No microphone found. Please connect a microphone and try again.');
        showToast('No microphone found', 'error');
      } else {
        setMicrophoneError(`Error accessing microphone: ${err.message}`);
        showToast(`Microphone error: ${err.message}`, 'error');
      }
    }
  }, [connect, startRecording, sendBinary, showToast]);

  // Handler: Stop recording and auto-save session if content > 10 chars
  const handleStopRecording = useCallback(() => {
    stopRecording();
    disconnect();
    setProcessedText(null);
    if (connectTimeoutRef.current) clearTimeout(connectTimeoutRef.current);
    setRecordingStatusAnnouncement('Recording stopped');

    // Auto-save session if content is substantial
    const plainText = editorRef.current?.editor?.getText() || '';
    const html = editorRef.current?.editor?.getHTML() || '';

    if (plainText.length > 10) {
      const title = plainText.substring(0, 50);
      const newSession: Session = {
        id: crypto.randomUUID(),
        title: title.length > 50 ? title.substring(0, 47) + '...' : title,
        content: html,
        plainText,
        wordCount,
        duration,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      setSessions((prev: Session[]) => {
        const updated = [newSession, ...prev];
        const truncated = updated.slice(0, 50);
        localStorage.setItem('medDictateSessions', JSON.stringify(truncated));
        return truncated;
      });

      showToast('Session saved', 'success');
    }

    // Focus management: return focus to editor after stopping
    setTimeout(() => {
      editorRef.current?.editor?.commands.focus();
    }, 100);
  }, [stopRecording, disconnect, wordCount, duration, showToast]);

  // Keyboard shortcuts listener (must be after handler functions are defined)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isMac = /Mac|iPhone|iPad|iPod/.test(navigator.platform);
      const modifier = isMac ? e.metaKey : e.ctrlKey;

      // Don't fire shortcuts when typing in an input/textarea (unless it's the editor)
      const target = e.target as HTMLElement;
      const isInputField = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT';

      // Ctrl/Cmd + Shift + R: Toggle recording
      if (modifier && e.shiftKey && e.key === 'R') {
        e.preventDefault();
        if (isRecording) {
          handleStopRecording();
        } else {
          handleStartRecording();
        }
        return;
      }

      // Ctrl/Cmd + Shift + P: Pause/Resume
      if (modifier && e.shiftKey && e.key === 'P') {
        e.preventDefault();
        if (isRecording) {
          if (isPaused) {
            resumeRecording();
          } else {
            pauseRecording();
          }
        }
        return;
      }

      // Ctrl/Cmd + S: Save session (prevent browser save)
      if (modifier && e.key === 's') {
        e.preventDefault();
        if (editorRef.current?.editor) {
          const content = editorRef.current.editor.getHTML();
          const plainText = editorRef.current.editor.getText();
          const session: Session = {
            id: `session-${Date.now()}`,
            title: `Session - ${new Date().toLocaleString()}`,
            content,
            plainText,
            wordCount: plainText.split(/\s+/).filter(Boolean).length,
            createdAt: new Date().toISOString(),
          };
          setSessions((prev: Session[]) => {
            const updated = [session, ...prev];
            const truncated = updated.slice(0, 50);
            localStorage.setItem('medDictateSessions', JSON.stringify(truncated));
            return truncated;
          });
          showToast('Session saved', 'success');
        }
        return;
      }

      // Ctrl/Cmd + Shift + C: Copy all text
      if (modifier && e.shiftKey && e.key === 'C') {
        e.preventDefault();
        if (editorRef.current?.editor) {
          const text = editorRef.current.editor.getText();
          navigator.clipboard.writeText(text);
          showToast('Copied to clipboard', 'success');
        }
        return;
      }

      // Escape: Stop recording
      if (e.key === 'Escape' && isRecording) {
        handleStopRecording();
        return;
      }

      // ?: Show help (only when not in an input field)
      if (e.key === '?' && !e.ctrlKey && !e.metaKey && !isInputField) {
        e.preventDefault();
        setShowHelpModal((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isRecording, isPaused, pauseRecording, resumeRecording, showToast, handleStartRecording, handleStopRecording]);

  // Handler: Insert macro
  const handleInsertMacro = (macroText: string) => {
    editorRef.current?.editor?.chain().focus().insertContent(macroText + ' ').run();
    showToast('Macro inserted', 'command');
  };

  // Handler: Load session
  const handleLoadSession = (session: Session) => {
    editorRef.current?.editor?.chain().focus().clearContent().insertContent(session.content).run();
    setWordCount(session.wordCount);
    setCharCount(session.plainText.length);
  };

  // Handler: Delete session
  const handleDeleteSession = (id: string) => {
    setSessions((prev: Session[]) => {
      const updated = prev.filter((s: Session) => s.id !== id);
      localStorage.setItem('medDictateSessions', JSON.stringify(updated));
      return updated;
    });
    showToast('Session deleted', 'success');
  };

  // Handler: Update session
  const handleUpdateSession = (session: Session) => {
    setSessions((prev: Session[]) => {
      const updated = prev.map((s: Session) => (s.id === session.id ? session : s));
      localStorage.setItem('medDictateSessions', JSON.stringify(updated));
      return updated;
    });
  };

  // Handler: Export session as .txt
  const handleExportSession = (session: Session) => {
    const element = document.createElement('a');
    const file = new Blob([session.plainText], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `${session.title}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
    showToast('Session exported', 'success');
  };

  // Handler: Content change
  const handleContentChange = (_html: string, text: string) => {
    const words = text.split(/\s+/).filter(Boolean).length;
    const chars = text.length;
    setWordCount(words);
    setCharCount(chars);
  };

  // Watch lastMessage and process it
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'transcription' && lastMessage.text) {
      const result = processText(lastMessage.text);

      if (result.wasCommand) {
        const action = result.commands[0]?.action;
        if (action === 'stopRecording') {
          handleStopRecording();
        } else if (action === 'pauseRecording') {
          pauseRecording();
        } else if (action === 'undo') {
          editorRef.current?.editor?.chain().focus().undo().run();
        } else if (action === 'clearAll') {
          if (window.confirm('Clear all content?')) {
            editorRef.current?.editor?.chain().focus().clearContent().run();
          }
        } else if (action === 'deleteLast') {
          editorRef.current?.editor?.chain().focus().deleteSelection().run();
        } else if (action === 'newline') {
          editorRef.current?.editor?.chain().focus().insertContent('\n').run();
        } else if (action === 'newParagraph') {
          editorRef.current?.editor?.chain().focus().insertContent('<p></p>').run();
        }

        showToast(`Command: ${action}`, 'command');
      } else if (result.isMacro) {
        setProcessedText(result.text);
        showToast('Macro inserted', 'command');
      } else if (result.text) {
        setProcessedText(result.text);
      }
    }
  }, [lastMessage, processText, pauseRecording, handleStopRecording]);

  // Error state
  const errorKey = (recorderError || wsError) ? `${recorderError || wsError}` : null;

  const handleDismissError = () => {
    if (errorKey) {
      setDismissedErrors((prev: Set<string>) => new Set([...prev, errorKey]));
    }
  };

  // Handler: Show toast message
  const handleToast = (message: string) => {
    showToast(message, 'info');
  };

  // Handler: Retry WebSocket connection
  const handleRetryConnection = () => {
    if (retryCount < 3) {
      setRetryCount((prev) => prev + 1);
      setDismissedErrors(new Set());
      connect();
      showToast(`Retrying connection (${retryCount + 1}/3)...`, 'info');
    }
  };

  // Auto-save to localStorage every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      if (editorRef.current?.editor) {
        const content = editorRef.current.editor.getHTML();
        const timestamp = new Date().toISOString();
        localStorage.setItem('medDictateAutoSave', JSON.stringify({ content, timestamp }));
        setAutoSaveTimestamp(timestamp);
      }
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  // Handler: Restore auto-save
  const handleRestoreAutoSave = () => {
    const autoSaveData = localStorage.getItem('medDictateAutoSave');
    if (autoSaveData) {
      try {
        const { content } = JSON.parse(autoSaveData);
        editorRef.current?.editor?.chain().focus().clearContent().insertContent(content).run();
        setRestoredAutoSave(true);
        setShowAutoSaveRestore(false);
        handleToast('Auto-save restored ✓');
      } catch (e) {
        console.error('Failed to restore auto-save:', e);
      }
    }
  };

  // Handler: Discard auto-save
  const handleDiscardAutoSave = () => {
    localStorage.removeItem('medDictateAutoSave');
    setRestoredAutoSave(true);
    setShowAutoSaveRestore(false);
  };

  // ================================================
  // SKELETON LOADING SCREEN
  // ================================================
  if (isAppLoading) {
    return (
      <div className="h-screen flex flex-col bg-white" aria-busy="true" aria-label="Loading application">
        {/* Skeleton Header */}
        <div className="sticky top-0 z-40 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="skeleton w-6 h-6 rounded-full" />
            <div className="skeleton w-32 h-6 rounded" />
          </div>
          <div className="flex items-center gap-4">
            <div className="skeleton w-16 h-5 rounded" />
            <div className="skeleton w-8 h-8 rounded-lg" />
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Skeleton Sidebar */}
          <div className="hidden lg:block w-72 border-r border-gray-200 p-4 space-y-4">
            <div className="skeleton w-full h-10 rounded-lg" />
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="space-y-2">
                  <div className="skeleton w-24 h-4 rounded" />
                  <div className="skeleton w-full h-16 rounded-lg" />
                </div>
              ))}
            </div>
          </div>

          {/* Skeleton Editor */}
          <div className="flex-1 flex flex-col">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="skeleton w-64 h-7 rounded" />
            </div>
            <div className="p-2 bg-gray-50 border-b flex gap-2">
              {[1, 2, 3, 4, 5, 6, 7].map((i) => (
                <div key={i} className="skeleton w-8 h-8 rounded" />
              ))}
            </div>
            <div className="flex-1 p-6 space-y-3">
              <div className="skeleton w-full h-4 rounded" />
              <div className="skeleton w-3/4 h-4 rounded" />
              <div className="skeleton w-5/6 h-4 rounded" />
              <div className="skeleton w-2/3 h-4 rounded" />
              <div className="skeleton w-full h-4 rounded" />
              <div className="skeleton w-4/5 h-4 rounded" />
            </div>
            <div className="border-t border-gray-200 px-6 py-4 flex items-center justify-between">
              <div className="skeleton w-32 h-5 rounded" />
              <div className="skeleton w-20 h-20 rounded-full" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ================================================
  // BROWSER NOT SUPPORTED
  // ================================================
  if (!browserSupported) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8 text-center">
          <AlertTriangle className="w-16 h-16 text-yellow-500 mx-auto mb-4" aria-hidden="true" />
          <h1 className="text-xl font-bold text-gray-900 mb-2">Browser Not Supported</h1>
          <p className="text-gray-600 mb-6">
            MedDictate requires <strong>MediaRecorder</strong> and <strong>AudioContext</strong> APIs
            which are not available in your current browser.
          </p>
          <p className="text-sm text-gray-500">
            Please use <strong>Chrome</strong>, <strong>Firefox</strong>, or <strong>Edge</strong> for the best experience.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-white">
      {/* Screen reader live region for recording status */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {recordingStatusAnnouncement}
      </div>

      {/* Header */}
      <Header
        isConnected={isConnected}
        isConnecting={isConnecting}
        onSettingsClick={() => setShowSettingsModal(true)}
        onHelpClick={() => setShowHelpModal(true)}
      />

      {/* Microphone denied banner */}
      {microphoneError && (
        <div className="mx-4 mt-3 px-4 py-3 bg-yellow-50 border border-yellow-300 text-yellow-800 rounded-lg flex items-start gap-3" role="alert">
          <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div className="flex-1">
            <p className="font-semibold text-sm">{microphoneError}</p>
            <p className="text-xs text-yellow-700 mt-1">
              <strong>How to fix:</strong> Click the lock/camera icon in your browser&apos;s address bar → Allow microphone access → Reload the page.
            </p>
          </div>
          <button
            onClick={() => setMicrophoneError(null)}
            className="text-yellow-600 hover:text-yellow-800 flex-shrink-0"
            aria-label="Dismiss microphone error"
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
      )}

      {/* WebSocket error banner with retry */}
      {wsError && !dismissedErrors.has(wsError) && (
        <div className="mx-4 mt-3 px-4 py-3 bg-red-50 border border-red-300 text-red-800 rounded-lg flex items-center gap-3" role="alert">
          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0" aria-hidden="true" />
          <div className="flex-1">
            <p className="font-semibold text-sm">Connection Failed</p>
            <p className="text-xs text-red-700 mt-0.5">{wsError}</p>
          </div>
          {retryCount < 3 && (
            <button
              onClick={handleRetryConnection}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-red-100 hover:bg-red-200 text-red-800 text-xs font-medium rounded-lg transition-colors"
              aria-label={`Retry connection (${retryCount}/3 attempts)`}
            >
              <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
              Retry ({retryCount}/3)
            </button>
          )}
          <button
            onClick={() => setDismissedErrors((prev) => new Set([...prev, wsError]))}
            className="text-red-600 hover:text-red-800 flex-shrink-0"
            aria-label="Dismiss connection error"
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
      )}

      {/* Recorder error banner (non-WS) */}
      {recorderError && !wsError && !dismissedErrors.has(recorderError) && (
        <div className="mx-4 mt-3 px-4 py-3 bg-red-500 text-white rounded-lg flex items-center justify-between" role="alert">
          <span>{recorderError}</span>
          <button
            onClick={handleDismissError}
            className="text-white hover:text-gray-100 font-semibold"
            aria-label="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}

      {/* Initializing microphone indicator */}
      {isInitializingMicrophone && (
        <div className="mx-4 mt-3 px-4 py-2 bg-blue-50 border border-blue-200 text-blue-700 rounded-lg flex items-center gap-2" role="status">
          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" aria-hidden="true" />
          <span className="text-sm font-medium">Initializing microphone...</span>
        </div>
      )}

      {/* Auto-save Restore Modal */}
      {showAutoSaveRestore && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-label="Restore auto-save">
          <div className="bg-white rounded-lg shadow-xl max-w-sm w-full mx-4 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">
              Restore Previous Dictation?
            </h2>
            <p className="text-sm text-gray-600 mb-6">
              You have an auto-saved dictation from earlier. Would you like to restore it?
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleRestoreAutoSave}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
                aria-label="Restore auto-saved content"
              >
                Restore
              </button>
              <button
                onClick={handleDiscardAutoSave}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 transition-colors"
                aria-label="Discard auto-saved content"
              >
                Discard
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Help Modal */}
      {showHelpModal && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={() => setShowHelpModal(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Keyboard shortcuts"
        >
          <div
            className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Keyboard className="w-5 h-5 text-blue-600" aria-hidden="true" />
                <h2 className="text-lg font-bold text-gray-900">Keyboard Shortcuts</h2>
              </div>
              <button
                onClick={() => setShowHelpModal(false)}
                className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="Close help modal"
              >
                <X className="w-5 h-5 text-gray-500" aria-hidden="true" />
              </button>
            </div>

            <div className="space-y-3">
              {KEYBOARD_SHORTCUTS.map((shortcut, idx) => (
                <div key={idx} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <span className="text-sm text-gray-700">{shortcut.description}</span>
                  <div className="flex items-center gap-1">
                    {shortcut.keys.map((key, kidx) => (
                      <span key={kidx}>
                        <kbd className="px-2 py-1 bg-gray-100 border border-gray-300 text-xs font-mono font-semibold text-gray-700 rounded shadow-sm">
                          {key}
                        </kbd>
                        {kidx < shortcut.keys.length - 1 && (
                          <span className="text-gray-400 mx-0.5">+</span>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <p className="text-xs text-gray-500 mt-4 text-center">
              Press <kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-300 text-xs font-mono rounded">?</kbd> to toggle this panel
            </p>
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <Sidebar
          macros={macros}
          sessions={sessions}
          onInsertMacro={handleInsertMacro}
          onLoadSession={handleLoadSession}
          onDeleteSession={handleDeleteSession}
          onUpdateSession={handleUpdateSession}
          onExportSession={handleExportSession}
          isMobileOpen={isMobileOpen}
          onToggleMobile={() => setIsMobileOpen(!isMobileOpen)}
        />

        {/* Center content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Title */}
          <div className="px-6 py-4 border-b border-gray-200 bg-white hidden sm:block">
            <h1 className="text-2xl font-bold text-gray-900">
              New Dictation — {currentDate}
            </h1>
          </div>

          {/* Mobile title */}
          <div className="px-4 py-3 border-b border-gray-200 bg-white sm:hidden">
            <h1 className="text-lg font-bold text-gray-900">
              New Dictation
            </h1>
            <p className="text-xs text-gray-500">{currentDate}</p>
          </div>

          {/* Toolbar */}
          <Toolbar editor={editorRef.current?.editor || null} macros={macros} onToast={handleToast} />

          {/* Editor */}
          <div
            className="flex-1 overflow-auto px-4 sm:px-6 py-4"
            style={{
              fontSize: `${settings.editor.fontSize}px`,
              fontFamily: settings.editor.fontFamily,
            }}
          >
            <DictationEditor
              ref={editorRef}
              incomingText={processedText}
              onContentChange={handleContentChange}
            />
          </div>

          {/* Bottom bar — Desktop */}
          <div className="sticky bottom-0 border-t border-gray-200 bg-white px-4 sm:px-6 py-4 record-button">
            <div className="flex items-center justify-between gap-4">
              {/* Word/char count and auto-save status */}
              <div className="flex items-center gap-4">
                <div className="text-sm text-gray-700" aria-label={`${wordCount} words, ${charCount} characters`}>
                  {wordCount} words · {charCount} characters
                </div>
                {autoSaveTimestamp && (
                  <div className="text-xs text-gray-500 hidden sm:block">
                    Auto-saved {new Date(autoSaveTimestamp).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
                  </div>
                )}
              </div>

              {/* Visualizer and record button */}
              <div className="flex items-center gap-4 sm:gap-6">
                <AudioVisualizer isActive={isRecording} audioLevel={audioLevel} />

                <RecordButton
                  isRecording={isRecording}
                  isPaused={isPaused}
                  duration={duration}
                  onStartRecording={handleStartRecording}
                  onStopRecording={handleStopRecording}
                  onPauseRecording={pauseRecording}
                  onResumeRecording={resumeRecording}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={showSettingsModal}
        onClose={() => setShowSettingsModal(false)}
        settings={settings}
        onUpdateSettings={updateSettings}
      />
    </div>
  );
}
