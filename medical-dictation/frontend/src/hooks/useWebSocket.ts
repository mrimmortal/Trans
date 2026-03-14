'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { 
  TranscriptionMessage, 
  VoiceCommand, 
  AvailableCommands, 
  CustomCommandRegistration,
  CommandHistoryItem 
} from '../types';

interface WebSocketHook {
  // Connection state
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  
  // Messages
  lastMessage: TranscriptionMessage | null;
  lastTranscription: string | null;
  lastCommands: VoiceCommand[];
  
  // Available commands from server
  availableCommands: AvailableCommands | null;
  commandsEnabled: boolean;
  
  // Connection methods
  connect: () => void;
  disconnect: () => void;
  
  // Audio methods
  sendBinary: (data: ArrayBuffer) => void;
  
  // Control methods
  sendControl: (action: string) => void;
  flush: () => void;
  reset: () => void;
  getStats: () => void;
  
  // Command methods
  enableCommands: () => void;
  disableCommands: () => void;
  getAvailableCommands: () => void;
  registerCustomCommand: (command: CustomCommandRegistration) => void;
  getCommandHistory: (limit?: number) => void;
}

/**
 * React hook managing a WebSocket connection to the transcription server
 * with full voice command support.
 */
export function useWebSocket(url: string): WebSocketHook {
  // ══════════════════════════════════════════════════════════
  // STATE
  // ══════════════════════════════════════════════════════════
  
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [lastMessage, setLastMessage] = useState<TranscriptionMessage | null>(null);
  const [lastTranscription, setLastTranscription] = useState<string | null>(null);
  const [lastCommands, setLastCommands] = useState<VoiceCommand[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [availableCommands, setAvailableCommands] = useState<AvailableCommands | null>(null);
  const [commandsEnabled, setCommandsEnabled] = useState(true);

  // ══════════════════════════════════════════════════════════
  // REFS
  // ══════════════════════════════════════════════════════════
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const pingIntervalRef = useRef<number | null>(null);

  // ══════════════════════════════════════════════════════════
  // MESSAGE HANDLER
  // ══════════════════════════════════════════════════════════
  
  const handleMessage = useCallback((data: string) => {
    try {
      const msg: TranscriptionMessage = JSON.parse(data);
      setLastMessage(msg);

      switch (msg.type) {
        case 'connected':
          console.log('[WS] Connected:', msg.message);
          // Store available commands from config
          if (msg.config?.available_commands) {
            setAvailableCommands(msg.config.available_commands);
          }
          if (msg.config?.commands_enabled !== undefined) {
            setCommandsEnabled(msg.config.commands_enabled);
          }
          break;

        case 'transcription':
          // Update transcription
          if (msg.text) {
            setLastTranscription(msg.text);
          }
          // Update commands
          if (msg.commands && msg.commands.length > 0) {
            setLastCommands(msg.commands);
            console.log('[WS] Commands executed:', msg.commands.map(c => c.action));
          } else {
            setLastCommands([]);
          }
          break;

        case 'available_commands':
          if (msg.commands_list) {
            setAvailableCommands(msg.commands_list);
          }
          break;

        case 'control_ack':
          console.log('[WS] Control acknowledged:', msg.action);
          if (msg.action === 'enable_commands') {
            setCommandsEnabled(true);
          } else if (msg.action === 'disable_commands') {
            setCommandsEnabled(false);
          }
          break;

        case 'error':
          console.error('[WS] Server error:', msg.message);
          setError(msg.message || 'Unknown server error');
          break;

        case 'pong':
          // Heartbeat response - connection is alive
          break;

        case 'stats':
          console.log('[WS] Stats:', msg.data);
          break;

        default:
          console.log('[WS] Unknown message type:', msg.type);
      }
    } catch (e) {
      console.error('[WS] Failed to parse message:', e);
    }
  }, []);

  // ══════════════════════════════════════════════════════════
  // CONNECTION METHODS
  // ══════════════════════════════════════════════════════════
  
  const connect = useCallback(() => {
    // Avoid duplicate connections
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      return;
    }

    setIsConnecting(true);
    setError(null);

    try {
      const ws = new WebSocket(url);
      ws.binaryType = 'arraybuffer';
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WS] Connected to', url);
        setIsConnected(true);
        setIsConnecting(false);
        reconnectAttemptsRef.current = 0;

        // Start ping interval
        pingIntervalRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 25000);
      };

      ws.onmessage = (evt) => {
        if (typeof evt.data === 'string') {
          handleMessage(evt.data);
        }
      };

      ws.onclose = (evt) => {
        console.log('[WS] Closed:', evt.code, evt.reason);
        
        if (pingIntervalRef.current !== null) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        
        setIsConnected(false);
        setIsConnecting(false);

        // Abnormal closure: attempt reconnect with exponential backoff
        if (evt.code !== 1000 && evt.code !== 1001) {
          if (reconnectAttemptsRef.current < 3) {
            const attempt = reconnectAttemptsRef.current;
            const delay = Math.pow(2, attempt) * 1000;
            reconnectAttemptsRef.current += 1;
            console.log(`[WS] Reconnecting in ${delay}ms (attempt ${attempt + 1}/3)`);
            setTimeout(connect, delay);
          } else {
            setError('Connection lost. Please try again.');
          }
        }
      };

      ws.onerror = () => {
        console.error('[WS] Connection error');
        setError('WebSocket connection error. Is the backend running?');
        setIsConnecting(false);
      };
    } catch (err) {
      setError((err as Error).message);
      setIsConnecting(false);
    }
  }, [url, handleMessage]);

  const disconnect = useCallback(() => {
    // Prevent automatic reconnection
    reconnectAttemptsRef.current = 3;

    if (pingIntervalRef.current !== null) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        // Flush before disconnect
        ws.send(JSON.stringify({ type: 'flush' }));
      } catch {
        // Ignore send errors during shutdown
      }
      // Give server time to process the flush before closing
      setTimeout(() => {
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          ws.close(1000, 'client disconnect');
        }
      }, 500);
    }
    
    setIsConnected(false);
    setIsConnecting(false);
  }, []);

  // ══════════════════════════════════════════════════════════
  // AUDIO METHODS
  // ══════════════════════════════════════════════════════════
  
  const sendBinary = useCallback((data: ArrayBuffer) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(data);
    }
  }, []);

  // ══════════════════════════════════════════════════════════
  // CONTROL METHODS
  // ══════════════════════════════════════════════════════════
  
  const sendControl = useCallback((action: string) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: action }));
    }
  }, []);

  const flush = useCallback(() => {
    sendControl('flush');
  }, [sendControl]);

  const reset = useCallback(() => {
    sendControl('reset');
    setLastTranscription(null);
    setLastCommands([]);
  }, [sendControl]);

  const getStats = useCallback(() => {
    sendControl('stats');
  }, [sendControl]);

  // ══════════════════════════════════════════════════════════
  // COMMAND METHODS
  // ══════════════════════════════════════════════════════════
  
  const enableCommands = useCallback(() => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'enable_commands' }));
    }
  }, []);

  const disableCommands = useCallback(() => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'disable_commands' }));
    }
  }, []);

  const getAvailableCommands = useCallback(() => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'get_commands' }));
    }
  }, []);

  const registerCustomCommand = useCallback((command: CustomCommandRegistration) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'register_command',
        pattern: command.pattern,
        replacement: command.replacement,
        action: command.action || 'custom',
      }));
    }
  }, []);

  const getCommandHistory = useCallback((limit: number = 50) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'command_history',
        limit: limit,
      }));
    }
  }, []);

  // ══════════════════════════════════════════════════════════
  // CLEANUP
  // ══════════════════════════════════════════════════════════
  
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // ══════════════════════════════════════════════════════════
  // RETURN
  // ══════════════════════════════════════════════════════════
  
  return {
    // Connection state
    isConnected,
    isConnecting,
    error,
    
    // Messages
    lastMessage,
    lastTranscription,
    lastCommands,
    
    // Commands
    availableCommands,
    commandsEnabled,
    
    // Connection methods
    connect,
    disconnect,
    
    // Audio methods
    sendBinary,
    
    // Control methods
    sendControl,
    flush,
    reset,
    getStats,
    
    // Command methods
    enableCommands,
    disableCommands,
    getAvailableCommands,
    registerCustomCommand,
    getCommandHistory,
  };
}