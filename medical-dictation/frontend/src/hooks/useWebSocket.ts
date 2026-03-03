'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { TranscriptionMessage } from '../types';

interface WebSocketHook {
  isConnected: boolean;
  isConnecting: boolean;
  lastMessage: TranscriptionMessage | null;
  error: string | null;
  connect: () => void;
  disconnect: () => void;
  sendBinary: (data: ArrayBuffer) => void;
  sendControl: (action: string) => void;
}

/**
 * React hook that manages a single WebSocket connection to the backend
 * transcription server.  It handles connection state, automatic
 * reconnection with exponential backoff, keep‑alive pings, and provides
 * methods for sending both binary audio chunks and JSON control messages.
 *
 * The hook returns a small API that components can use to drive the
 * dictation session while reacting to incoming transcription messages.
 *
 * @param url the full ws:// or wss:// URL to open
 */
export function useWebSocket(url: string): WebSocketHook {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [lastMessage, setLastMessage] = useState<TranscriptionMessage | null>(null);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const pingIntervalRef = useRef<number | null>(null);

  const connect = useCallback(() => {
    // avoid duplicate connections
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
        setIsConnected(true);
        setIsConnecting(false);
        reconnectAttemptsRef.current = 0;

        // ping every 25 seconds to keep the socket alive
        pingIntervalRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: 'ping' }));
          }
        }, 25000);
      };

      ws.onmessage = (evt) => {
        if (typeof evt.data === 'string') {
          try {
            const msg: TranscriptionMessage = JSON.parse(evt.data);
            setLastMessage(msg);
            if (msg.type === 'error') {
              setError(msg.message || 'Unknown error');
            }
          } catch (e) {
            // ignore parse errors
            console.error('Failed to parse ws message', e);
          }
        }
      };

      ws.onclose = (evt) => {
        if (pingIntervalRef.current !== null) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        setIsConnected(false);
        setIsConnecting(false);

        // abnormal closure: attempt reconnect
        if (evt.code !== 1000 && evt.code !== 1001) {
          if (reconnectAttemptsRef.current < 3) {
            const attempt = reconnectAttemptsRef.current;
            const delay = Math.pow(2, attempt) * 1000;
            reconnectAttemptsRef.current += 1;
            setTimeout(connect, delay);
          }
        }
      };

      ws.onerror = (evt) => {
        setError('WebSocket error');
        setIsConnecting(false);
      };
    } catch (err) {
      setError((err as Error).message);
      setIsConnecting(false);
    }
  }, [url]);

  const disconnect = useCallback(() => {
    reconnectAttemptsRef.current = 3;
    if (pingIntervalRef.current !== null) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify({ action: 'flush' }));
      } catch {
        // ignore
      }
      setTimeout(() => {
        ws.close(1000, 'client disconnect');
      }, 500);
    }
    setIsConnected(false);
    setIsConnecting(false);
  }, []);

  const sendBinary = useCallback((data: ArrayBuffer) => {
    const ws = wsRef.current;
    console.log(`WS send: ${data.byteLength} bytes, readyState: ${ws ? ws.readyState : 'no socket'}`);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(data);
    }
  }, []);

  const sendControl = useCallback((action: string) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action }));
    }
  }, []);

  // cleanup on unmount
  useEffect(() => {
    return () => {
      // deliberately call disconnect logic
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected,
    isConnecting,
    lastMessage,
    error,
    connect,
    disconnect,
    sendBinary,
    sendControl,
  };
}
