// app/page.tsx
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
import { 
  WS_URL, 
  API_URL, 
  AUDIO_SAMPLE_RATE, 
  AUDIO_CHUNK_INTERVAL,
  AUTO_SAVE_INTERVAL,
  MAX_SESSIONS,
  TOAST_DURATION 
} from '@/lib/constants';
import { DEFAULT_MACROS } from '@/lib/defaultMacros';
import { Macro, VoiceCommand } from '@/types';
import { X, AlertTriangle, RefreshCw, Keyboard, Wifi, WifiOff, Mic, MicOff } from 'lucide-react';

// ══════════════════════════════════════════════════════════════════
// KEYBOARD SHORTCUTS HELP
// ══════════════════════════════════════════════════════════════════

const KEYBOARD_SHORTCUTS = [
  { keys: ['Ctrl/⌘', 'Shift', 'R'], description: 'Toggle recording on/off' },
  { keys: ['Ctrl/⌘', 'Shift', 'P'], description: 'Pause/Resume recording' },
  { keys: ['Ctrl/⌘', 'S'], description: 'Save session' },
  { keys: ['Ctrl/⌘', 'Shift', 'C'], description: 'Copy all text' },
  { keys: ['Escape'], description: 'Stop recording' },
  { keys: ['?'], description: 'Show/hide this help' },
];

// ══════════════════════════════════════════════════════════════════
// HELPER: Migrate old localStorage macros (expansion → text)
// ══════════════════════════════════════════════════════════════════

function migrateMacros(raw: any[]): Macro[] {
  return raw.map((m) => ({
    id: m.id || `migrated-${Date.now()}-${Math.random()}`,
    name: m.name,
    trigger: m.trigger || '',
    text: m.text || m.expansion || '',
    category: m.category,
  }));
}

// ══════════════════════════════════════════════════════════════════
// MAIN PAGE COMPONENT
// ══════════════════════════════════════════════════════════════════

export default function Page() {
  // ─────────────────────────────────────────────────────────────────
  // HOOKS
  // ─────────────────────────────────────────────────────────────────
  
  const {
    isConnected,
    isConnecting,
    lastMessage,
    lastTranscription,
    lastCommands,
    availableCommands,
    commandsEnabled,
    error: wsError,
    connect,
    disconnect,
    sendBinary,
    sendControl,
    flush,
    reset,
    enableCommands,
    disableCommands,
    registerCustomCommand,
  } = useWebSocket(WS_URL);

  const {
    isRecording,
    isPaused,
    duration,
    audioLevel,
    error: recorderError,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
  } = useAudioRecorder({
    sampleRate: AUDIO_SAMPLE_RATE,
    chunkIntervalMs: AUDIO_CHUNK_INTERVAL,
    onAudioData: (data) => {
      if (isConnected) {
        sendBinary(data);
      }
    },
  });

  const { processText } = useVoiceCommands();
  const { settings, updateSettings } = useSettings();
  const { showToast } = useToast();

  // ─────────────────────────────────────────────────────────────────
  // STATE
  // ─────────────────────────────────────────────────────────────────
  
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
  const [showCommandsPanel, setShowCommandsPanel] = useState(false);
  const [microphoneError, setMicrophoneError] = useState<string | null>(null);
  const [browserSupported, setBrowserSupported] = useState(true);
  const [retryCount, setRetryCount] = useState(0);
  const [isInitializingMicrophone, setIsInitializingMicrophone] = useState(false);
  const [recordingStatusAnnouncement, setRecordingStatusAnnouncement] = useState('');
  const [pendingRecordStart, setPendingRecordStart] = useState(false);
  const [commandNotification, setCommandNotification] = useState<string | null>(null);

  const editorRef = useRef<DictationEditorHandle>(null);
  const connectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ─────────────────────────────────────────────────────────────────
  // LOAD DATA FROM LOCALSTORAGE
  // ─────────────────────────────────────────────────────────────────
  
  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Load and migrate macros
    const savedMacros = localStorage.getItem('medDictateMacros');
    if (savedMacros) {
      try {
        const parsed = JSON.parse(savedMacros);
        const migrated = migrateMacros(parsed);
        setMacros(migrated);
        localStorage.setItem('medDictateMacros', JSON.stringify(migrated));
      } catch {
        setMacros(DEFAULT_MACROS);
        localStorage.setItem('medDictateMacros', JSON.stringify(DEFAULT_MACROS));
      }
    } else {
      setMacros(DEFAULT_MACROS);
      localStorage.setItem('medDictateMacros', JSON.stringify(DEFAULT_MACROS));
    }

    // Load sessions
    const savedSessions = localStorage.getItem('medDictateSessions');
    if (savedSessions) {
      try {
        setSessions(JSON.parse(savedSessions));
      } catch {
        setSessions([]);
      }
    }

    // Check for auto-save < 24h old
    const autoSaveData = localStorage.getItem('medDictateAutoSave');
    if (autoSaveData && !restoredAutoSave) {
      try {
        const { timestamp } = JSON.parse(autoSaveData);
        const hoursOld = (Date.now() - new Date(timestamp).getTime()) / 3_600_000;
        if (hoursOld < 24) {
          setShowAutoSaveRestore(true);
        } else {
          localStorage.removeItem('medDictateAutoSave');
        }
      } catch {
        localStorage.removeItem('medDictateAutoSave');
      }
    }
  }, [restoredAutoSave]);

  // ─────────────────────────────────────────────────────────────────
  // BROWSER SUPPORT CHECK
  // ─────────────────────────────────────────────────────────────────
  
  useEffect(() => {
    const hasMediaRecorder =
      typeof window !== 'undefined' && typeof window.MediaRecorder !== 'undefined';
    const hasAudioContext =
      typeof window !== 'undefined' &&
      (window.AudioContext || (window as any).webkitAudioContext);

    if (!hasMediaRecorder || !hasAudioContext) {
      setBrowserSupported(false);
    }

    const timer = setTimeout(() => setIsAppLoading(false), 1000);
    return () => clearTimeout(timer);
  }, []);

  // ─────────────────────────────────────────────────────────────────
  // RECORDING STATE EFFECTS
  // ─────────────────────────────────────────────────────────────────
  
  useEffect(() => {
    if (isRecording || recorderError) {
      setIsInitializingMicrophone(false);
    }
  }, [isRecording, recorderError]);

  useEffect(() => {
    if (isRecording && !isPaused) {
      setRecordingStatusAnnouncement('Recording started');
    } else if (isRecording && isPaused) {
      setRecordingStatusAnnouncement('Recording paused');
    } else {
      setRecordingStatusAnnouncement('');
    }
  }, [isRecording, isPaused]);

  useEffect(() => {
    if (recorderError) {
      setMicrophoneError(recorderError);
      setPendingRecordStart(false);
    }
  }, [recorderError]);

  // ─────────────────────────────────────────────────────────────────
  // REGISTER CUSTOM COMMANDS ON CONNECT
  // ─────────────────────────────────────────────────────────────────
  
  useEffect(() => {
    if (isConnected) {
      // Register macros as custom commands
      macros.forEach((macro) => {
        if (macro.trigger) {
          registerCustomCommand({
            pattern: macro.trigger,
            replacement: macro.text,
            action: `macro_${macro.name}`,
          });
        }
      });

      // Register signature command
      registerCustomCommand({
        pattern: 'my signature',
        replacement: '\n\n— Dictated using MedDictate AI\n',
      });
    }
  }, [isConnected, macros, registerCustomCommand]);

  // ─────────────────────────────────────────────────────────────────
  // CURRENT DATE
  // ─────────────────────────────────────────────────────────────────
  
  const currentDate = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  // ─────────────────────────────────────────────────────────────────
  // START RECORDING
  // ─────────────────────────────────────────────────────────────────
  
  const handleStartRecording = useCallback(() => {
    setProcessedText(null);
    setIsInitializingMicrophone(true);
    setMicrophoneError(null);
    setDismissedErrors(new Set());
    setRetryCount(0);

    // Connect WebSocket
    connect();
    setPendingRecordStart(true);

    // Fallback: start recording anyway after 3s if WS not connected
    if (connectTimeoutRef.current) clearTimeout(connectTimeoutRef.current);
    connectTimeoutRef.current = setTimeout(() => {
      setPendingRecordStart((prev) => {
        if (prev) {
          console.warn('[Page] WS not connected after 3s — starting recording anyway');
          startRecording();
        }
        return false;
      });
    }, 3000);
  }, [connect, startRecording]);

  // Effect: start recording once WS is connected
  useEffect(() => {
    if (pendingRecordStart && isConnected && !isRecording) {
      setPendingRecordStart(false);
      if (connectTimeoutRef.current) {
        clearTimeout(connectTimeoutRef.current);
        connectTimeoutRef.current = null;
      }
      startRecording();
    }
  }, [pendingRecordStart, isConnected, isRecording, startRecording]);

  // ─────────────────────────────────────────────────────────────────
  // STOP RECORDING
  // ─────────────────────────────────────────────────────────────────
  
  const handleStopRecording = useCallback(() => {
    setPendingRecordStart(false);
    if (connectTimeoutRef.current) {
      clearTimeout(connectTimeoutRef.current);
      connectTimeoutRef.current = null;
    }

    stopRecording();
    flush();
    
    setTimeout(() => disconnect(), 600);

    setProcessedText(null);
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
        const updated = [newSession, ...prev].slice(0, MAX_SESSIONS);
        localStorage.setItem('medDictateSessions', JSON.stringify(updated));
        return updated;
      });

      showToast('Session saved', 'success');
    }

    setTimeout(() => editorRef.current?.editor?.commands.focus(), 100);
  }, [stopRecording, flush, disconnect, wordCount, duration, showToast]);

  // ─────────────────────────────────────────────────────────────────
  // PROCESS INCOMING TRANSCRIPTIONS
  // ─────────────────────────────────────────────────────────────────
  
  useEffect(() => {
    if (!lastTranscription) return;

    // Process with voice commands (local processing for non-server commands)
    const result = processText(lastTranscription, macros);

    if (result.wasCommand) {
      const action = result.commands[0]?.action;
      
      switch (action) {
        case 'stopRecording':
          handleStopRecording();
          break;
        case 'pauseRecording':
          pauseRecording();
          break;
        case 'undo':
          editorRef.current?.editor?.chain().focus().undo().run();
          break;
        case 'clearAll':
          if (window.confirm('Clear all content?')) {
            editorRef.current?.editor?.chain().focus().clearContent().run();
          }
          break;
        case 'deleteLast':
          editorRef.current?.editor?.chain().focus().deleteSelection().run();
          break;
        case 'newline':
          editorRef.current?.editor?.chain().focus().insertContent('\n').run();
          break;
        case 'newParagraph':
          editorRef.current?.editor?.chain().focus().insertContent('<p></p>').run();
          break;
      }
      
      showToast(`Command: ${action}`, 'command');
    } else if (result.isMacro) {
      setProcessedText(result.text);
      showToast('Macro inserted', 'command');
    } else if (result.text) {
      setProcessedText(result.text);
    }
  }, [lastTranscription, processText, macros, pauseRecording, handleStopRecording, showToast]);

  // ─────────────────────────────────────────────────────────────────
  // HANDLE SERVER-SIDE COMMANDS
  // ─────────────────────────────────────────────────────────────────
  
  useEffect(() => {
    if (!lastCommands || lastCommands.length === 0) return;

    lastCommands.forEach((cmd: VoiceCommand) => {
      // Show notification for non-punctuation commands
      if (cmd.type !== 'punctuation') {
        setCommandNotification(`Command: ${cmd.action.replace(/_/g, ' ')}`);
        setTimeout(() => setCommandNotification(null), TOAST_DURATION / 2);
      }

      // Handle specific commands that need frontend action
      switch (cmd.action) {
        case 'undo':
          editorRef.current?.editor?.chain().focus().undo().run();
          break;
        case 'redo':
          editorRef.current?.editor?.chain().focus().redo().run();
          break;
        case 'delete_last_word':
          // Delete last word
          const text = editorRef.current?.editor?.getText() || '';
          const newText = text.replace(/\s*\S+\s*$/, '');
          editorRef.current?.editor?.chain().focus().setContent(newText).run();
          break;
        case 'clear_all':
          if (window.confirm('Clear all content?')) {
            editorRef.current?.editor?.chain().focus().clearContent().run();
          }
          break;
        case 'select_all':
          editorRef.current?.editor?.chain().focus().selectAll().run();
          break;
        case 'save':
          handleSaveSession();
          break;
        case 'pause':
          pauseRecording();
          break;
        case 'resume':
          resumeRecording();
          break;
        case 'go_to_start':
          editorRef.current?.editor?.chain().focus().setTextSelection(0).run();
          break;
        case 'go_to_end':
          const endPos = editorRef.current?.editor?.state.doc.content.size || 0;
          editorRef.current?.editor?.chain().focus().setTextSelection(endPos).run();
          break;
      }
    });
  }, [lastCommands, pauseRecording, resumeRecording]);

  // ─────────────────────────────────────────────────────────────────
  // KEYBOARD SHORTCUTS
  // ─────────────────────────────────────────────────────────────────
  
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isMac = /Mac|iPhone|iPad|iPod/.test(navigator.platform);
      const modifier = isMac ? e.metaKey : e.ctrlKey;
      const target = e.target as HTMLElement;
      const isInputField =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT';

      // Ctrl/Cmd + Shift + R → toggle recording
      if (modifier && e.shiftKey && e.key === 'R') {
        e.preventDefault();
        isRecording ? handleStopRecording() : handleStartRecording();
        return;
      }

      // Ctrl/Cmd + Shift + P → pause/resume
      if (modifier && e.shiftKey && e.key === 'P') {
        e.preventDefault();
        if (isRecording) {
          isPaused ? resumeRecording() : pauseRecording();
        }
        return;
      }

      // Ctrl/Cmd + S → save session
      if (modifier && e.key === 's') {
        e.preventDefault();
        handleSaveSession();
        return;
      }

      // Ctrl/Cmd + Shift + C → copy all text
      if (modifier && e.shiftKey && e.key === 'C') {
        e.preventDefault();
        if (editorRef.current?.editor) {
          const text = editorRef.current.editor.getText();
          navigator.clipboard.writeText(text);
          showToast('Copied to clipboard', 'success');
        }
        return;
      }

      // Escape → stop recording
      if (e.key === 'Escape' && isRecording) {
        handleStopRecording();
        return;
      }

      // ? → help modal (outside input fields)
      if (e.key === '?' && !e.ctrlKey && !e.metaKey && !isInputField) {
        e.preventDefault();
        setShowHelpModal((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    isRecording,
    isPaused,
    pauseRecording,
    resumeRecording,
    showToast,
    handleStartRecording,
    handleStopRecording,
  ]);

  // ─────────────────────────────────────────────────────────────────
  // SAVE SESSION
  // ─────────────────────────────────────────────────────────────────
  
  const handleSaveSession = useCallback(() => {
    if (!editorRef.current?.editor) return;

    const content = editorRef.current.editor.getHTML();
    const plainText = editorRef.current.editor.getText();

    if (plainText.trim().length === 0) {
      showToast('Nothing to save', 'info');
      return;
    }

    const session: Session = {
      id: `session-${Date.now()}`,
      title: `Session - ${new Date().toLocaleString()}`,
      content,
      plainText,
      wordCount: plainText.split(/\s+/).filter(Boolean).length,
      createdAt: new Date().toISOString(),
    };

    setSessions((prev: Session[]) => {
      const updated = [session, ...prev].slice(0, MAX_SESSIONS);
      localStorage.setItem('medDictateSessions', JSON.stringify(updated));
      return updated;
    });

    showToast('Session saved', 'success');
  }, [showToast]);

  // ─────────────────────────────────────────────────────────────────
  // MACRO HANDLERS
  // ─────────────────────────────────────────────────────────────────
  
  const handleInsertMacro = useCallback((macroText: string) => {
    editorRef.current?.editor?.chain().focus().insertContent(macroText + ' ').run();
    showToast('Macro inserted', 'command');
  }, [showToast]);

  // ─────────────────────────────────────────────────────────────────
  // SESSION HANDLERS
  // ─────────────────────────────────────────────────────────────────
  
  const handleLoadSession = useCallback((session: Session) => {
    editorRef.current?.editor?.chain().focus().clearContent().insertContent(session.content).run();
    setWordCount(session.wordCount);
    setCharCount(session.plainText.length);
  }, []);

  const handleDeleteSession = useCallback((id: string) => {
    setSessions((prev: Session[]) => {
      const updated = prev.filter((s: Session) => s.id !== id);
      localStorage.setItem('medDictateSessions', JSON.stringify(updated));
      return updated;
    });
    showToast('Session deleted', 'success');
  }, [showToast]);

  const handleUpdateSession = useCallback((session: Session) => {
    setSessions((prev: Session[]) => {
      const updated = prev.map((s: Session) => (s.id === session.id ? session : s));
      localStorage.setItem('medDictateSessions', JSON.stringify(updated));
      return updated;
    });
  }, []);

  const handleExportSession = useCallback((session: Session) => {
    const element = document.createElement('a');
    const file = new Blob([session.plainText], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `${session.title}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
    showToast('Session exported', 'success');
  }, [showToast]);

  // ─────────────────────────────────────────────────────────────────
  // EDITOR CONTENT CHANGE
  // ─────────────────────────────────────────────────────────────────
  
  const handleContentChange = useCallback((_html: string, text: string) => {
    const words = text.split(/\s+/).filter(Boolean).length;
    setWordCount(words);
    setCharCount(text.length);
  }, []);

  // ─────────────────────────────────────────────────────────────────
  // AUTO-SAVE INTERVAL
  // ─────────────────────────────────────────────────────────────────
  
  useEffect(() => {
    const interval = setInterval(() => {
      if (editorRef.current?.editor) {
        const content = editorRef.current.editor.getHTML();
        const plainText = editorRef.current.editor.getText();
        
        if (plainText.trim().length > 0) {
          const timestamp = new Date().toISOString();
          localStorage.setItem('medDictateAutoSave', JSON.stringify({ content, timestamp }));
          setAutoSaveTimestamp(timestamp);
        }
      }
    }, AUTO_SAVE_INTERVAL);

    return () => clearInterval(interval);
  }, []);

  // ─────────────────────────────────────────────────────────────────
  // AUTO-SAVE RESTORE/DISCARD
  // ─────────────────────────────────────────────────────────────────
  
  const handleRestoreAutoSave = useCallback(() => {
    const autoSaveData = localStorage.getItem('medDictateAutoSave');
    if (autoSaveData) {
      try {
        const { content } = JSON.parse(autoSaveData);
        editorRef.current?.editor?.chain().focus().clearContent().insertContent(content).run();
        setRestoredAutoSave(true);
        setShowAutoSaveRestore(false);
        showToast('Auto-save restored ✓', 'info');
      } catch (e) {
        console.error('Failed to restore auto-save:', e);
      }
    }
  }, [showToast]);

  const handleDiscardAutoSave = useCallback(() => {
    localStorage.removeItem('medDictateAutoSave');
    setRestoredAutoSave(true);
    setShowAutoSaveRestore(false);
  }, []);

  // ─────────────────────────────────────────────────────────────────
  // ERROR HANDLERS
  // ─────────────────────────────────────────────────────────────────
  
  const errorKey = recorderError || wsError || null;

  const handleDismissError = useCallback(() => {
    if (errorKey) {
      setDismissedErrors((prev) => new Set([...prev, errorKey]));
    }
  }, [errorKey]);

  const handleRetryConnection = useCallback(() => {
    if (retryCount < 3) {
      setRetryCount((prev) => prev + 1);
      setDismissedErrors(new Set());
      connect();
      showToast(`Retrying connection (${retryCount + 1}/3)...`, 'info');
    }
  }, [retryCount, connect, showToast]);

  const handleToast = useCallback((message: string) => {
    showToast(message, 'info');
  }, [showToast]);

  // ════════════════════════════════════════════════════════════════
  // LOADING STATE
  // ════════════════════════════════════════════════════════════════
  
  if (isAppLoading) {
    return (
      <div className="h-screen flex flex-col bg-white" aria-busy="true" aria-label="Loading application">
        <div className="sticky top-0 z-40 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="skeleton w-6 h-6 rounded-full animate-pulse bg-gray-200" />
            <div className="skeleton w-32 h-6 rounded animate-pulse bg-gray-200" />
          </div>
          <div className="flex items-center gap-4">
            <div className="skeleton w-16 h-5 rounded animate-pulse bg-gray-200" />
            <div className="skeleton w-8 h-8 rounded-lg animate-pulse bg-gray-200" />
          </div>
        </div>
        <div className="flex flex-1 overflow-hidden">
          <div className="hidden lg:block w-72 border-r border-gray-200 p-4 space-y-4">
            <div className="skeleton w-full h-10 rounded-lg animate-pulse bg-gray-200" />
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="space-y-2">
                  <div className="skeleton w-24 h-4 rounded animate-pulse bg-gray-200" />
                  <div className="skeleton w-full h-16 rounded-lg animate-pulse bg-gray-200" />
                </div>
              ))}
            </div>
          </div>
          <div className="flex-1 flex flex-col">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="skeleton w-64 h-7 rounded animate-pulse bg-gray-200" />
            </div>
            <div className="p-2 bg-gray-50 border-b flex gap-2">
              {[1, 2, 3, 4, 5, 6, 7].map((i) => (
                <div key={i} className="skeleton w-8 h-8 rounded animate-pulse bg-gray-200" />
              ))}
            </div>
            <div className="flex-1 p-6 space-y-3">
              <div className="skeleton w-full h-4 rounded animate-pulse bg-gray-200" />
              <div className="skeleton w-3/4 h-4 rounded animate-pulse bg-gray-200" />
              <div className="skeleton w-5/6 h-4 rounded animate-pulse bg-gray-200" />
              <div className="skeleton w-2/3 h-4 rounded animate-pulse bg-gray-200" />
            </div>
            <div className="border-t border-gray-200 px-6 py-4 flex items-center justify-between">
              <div className="skeleton w-32 h-5 rounded animate-pulse bg-gray-200" />
              <div className="skeleton w-20 h-20 rounded-full animate-pulse bg-gray-200" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ════════════════════════════════════════════════════════════════
  // BROWSER NOT SUPPORTED
  // ════════════════════════════════════════════════════════════════
  
  if (!browserSupported) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8 text-center">
          <AlertTriangle className="w-16 h-16 text-yellow-500 mx-auto mb-4" aria-hidden="true" />
          <h1 className="text-xl font-bold text-gray-900 mb-2">Browser Not Supported</h1>
          <p className="text-gray-600 mb-6">
            MedDictate requires <strong>MediaRecorder</strong> and{' '}
            <strong>AudioContext</strong> APIs which are not available in your current browser.
          </p>
          <p className="text-sm text-gray-500">
            Please use <strong>Chrome</strong>, <strong>Firefox</strong>, or{' '}
            <strong>Edge</strong> for the best experience.
          </p>
        </div>
      </div>
    );
  }

  // ════════════════════════════════════════════════════════════════
  // MAIN RENDER
  // ════════════════════════════════════════════════════════════════
  
  return (
    <div className="h-screen flex flex-col bg-white">
      {/* Screen reader live region */}
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

      {/* ════════════════════════════════════════════════════════ */}
      {/* STATUS BANNERS */}
      {/* ════════════════════════════════════════════════════════ */}

      {/* Command notification */}
      {commandNotification && (
        <div className="mx-4 mt-3 px-4 py-2 bg-blue-50 border border-blue-200 text-blue-700 rounded-lg flex items-center gap-2">
          <Keyboard className="w-4 h-4" aria-hidden="true" />
          <span className="text-sm font-medium">{commandNotification}</span>
        </div>
      )}

      {/* Microphone error banner */}
      {microphoneError && (
        <div
          className="mx-4 mt-3 px-4 py-3 bg-yellow-50 border border-yellow-300 text-yellow-800 rounded-lg flex items-start gap-3"
          role="alert"
        >
          <MicOff className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div className="flex-1">
            <p className="font-semibold text-sm">{microphoneError}</p>
            <p className="text-xs text-yellow-700 mt-1">
              <strong>How to fix:</strong> Click the lock/camera icon in your browser&apos;s
              address bar → Allow microphone access → Reload the page.
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

      {/* WebSocket error banner */}
      {wsError && !dismissedErrors.has(wsError) && (
        <div
          className="mx-4 mt-3 px-4 py-3 bg-red-50 border border-red-300 text-red-800 rounded-lg flex items-center gap-3"
          role="alert"
        >
          <WifiOff className="w-5 h-5 text-red-600 flex-shrink-0" aria-hidden="true" />
          <div className="flex-1">
            <p className="font-semibold text-sm">Connection Failed</p>
            <p className="text-xs text-red-700 mt-0.5">{wsError}</p>
          </div>
          {retryCount < 3 && (
            <button
              onClick={handleRetryConnection}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-red-100 hover:bg-red-200 text-red-800 text-xs font-medium rounded-lg transition-colors"
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

      {/* Recorder error banner */}
      {recorderError && !wsError && !dismissedErrors.has(recorderError) && (
        <div
          className="mx-4 mt-3 px-4 py-3 bg-red-500 text-white rounded-lg flex items-center justify-between"
          role="alert"
        >
          <span>{recorderError}</span>
          <button onClick={handleDismissError} className="text-white hover:text-gray-100 font-semibold">
            ✕
          </button>
        </div>
      )}

      {/* Initializing microphone indicator */}
      {isInitializingMicrophone && (
        <div className="mx-4 mt-3 px-4 py-2 bg-blue-50 border border-blue-200 text-blue-700 rounded-lg flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-medium">Initializing microphone...</span>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════ */}
      {/* MODALS */}
      {/* ════════════════════════════════════════════════════════ */}

      {/* Auto-save restore modal */}
      {showAutoSaveRestore && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-sm w-full mx-4 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Restore Previous Dictation?</h2>
            <p className="text-sm text-gray-600 mb-6">
              You have an auto-saved dictation from earlier. Would you like to restore it?
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleRestoreAutoSave}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
              >
                Restore
              </button>
              <button
                onClick={handleDiscardAutoSave}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 transition-colors"
              >
                Discard
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Help modal */}
      {showHelpModal && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={() => setShowHelpModal(false)}
        >
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Keyboard className="w-5 h-5 text-blue-600" />
                <h2 className="text-lg font-bold text-gray-900">Keyboard Shortcuts</h2>
              </div>
              <button
                onClick={() => setShowHelpModal(false)}
                className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
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
                        {kidx < shortcut.keys.length - 1 && <span className="text-gray-400 mx-0.5">+</span>}
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

      {/* Commands panel modal */}
      {showCommandsPanel && availableCommands && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={() => setShowCommandsPanel(false)}
        >
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full p-6 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Mic className="w-5 h-5 text-blue-600" />
                <h2 className="text-lg font-bold text-gray-900">Available Voice Commands</h2>
              </div>
              <button onClick={() => setShowCommandsPanel(false)} className="p-1 hover:bg-gray-100 rounded-lg">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              {Object.entries(availableCommands).map(([category, commands]) => (
                <div key={category}>
                  <h4 className="font-semibold text-gray-700 capitalize mb-2">{category}</h4>
                  <ul className="space-y-1 text-gray-600">
                    {commands.slice(0, 8).map((cmd, i) => (
                      <li key={i} className="truncate">"{cmd}"</li>
                    ))}
                    {commands.length > 8 && <li className="text-gray-400">+{commands.length - 8} more</li>}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════ */}
      {/* MAIN CONTENT */}
      {/* ════════════════════════════════════════════════════════ */}
      
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
          {/* Desktop title */}
          <div className="px-6 py-4 border-b border-gray-200 bg-white hidden sm:flex sm:items-center sm:justify-between">
            <h1 className="text-2xl font-bold text-gray-900">New Dictation — {currentDate}</h1>
            <div className="flex items-center gap-2">
              {/* Commands toggle */}
              <button
                onClick={() => commandsEnabled ? disableCommands() : enableCommands()}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
                  commandsEnabled
                    ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                    : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                }`}
                title={commandsEnabled ? 'Voice commands enabled' : 'Voice commands disabled'}
              >
                <Mic className="w-4 h-4" />
                Commands {commandsEnabled ? 'ON' : 'OFF'}
              </button>
              {/* Show commands help */}
              <button
                onClick={() => setShowCommandsPanel(true)}
                className="px-3 py-1.5 text-sm text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
              >
                View Commands
              </button>
            </div>
          </div>

          {/* Mobile title */}
          <div className="px-4 py-3 border-b border-gray-200 bg-white sm:hidden">
            <h1 className="text-lg font-bold text-gray-900">New Dictation</h1>
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

          {/* Bottom bar */}
          <div className="sticky bottom-0 border-t border-gray-200 bg-white px-4 sm:px-6 py-4">
            <div className="flex items-center justify-between gap-4">
              {/* Word/char count + auto-save */}
              <div className="flex items-center gap-4">
                <div className="text-sm text-gray-700">
                  {wordCount} words · {charCount} characters
                </div>
                {autoSaveTimestamp && (
                  <div className="text-xs text-gray-500 hidden sm:block">
                    Auto-saved{' '}
                    {new Date(autoSaveTimestamp).toLocaleTimeString('en-US', {
                      hour: 'numeric',
                      minute: '2-digit',
                    })}
                  </div>
                )}
              </div>

              {/* Visualizer + record button */}
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