import { useState, useRef, useCallback, useEffect } from "react";
import TurndownService from "turndown";
import type { ConnectionState, ServerMessage } from "../types/websocket-contract";
import type { RealtimePreviewState } from "../types/transcript";
import type { EditorHandle } from "../components/TranscriptEditor";
import { WebSocketClient } from "../services/websocketClient";
import { AudioCapture } from "../services/audioCapture";
import { DEFAULTS } from "../config/defaults";
import { loadWsUrl, saveWsUrl } from "../services/transcriptStorage";

export interface EventEntry {
  id: number;
  type: string;
  message: string;
  timestamp: number;
}

export interface ServerStatusState {
  sessionId: string;
  model: string;
  realtimeModel: string;
  engine: string;
  device: string;
  queueDepth: number;
  state: string;
  activeSessions: number;
  activeSpeakers: number;
  wakeWordEnabled: boolean;
}

const MAX_EVENTS = 200;
let eventIdCounter = 0;

const turndown = new TurndownService({
  headingStyle: "atx",
  codeBlockStyle: "fenced",
});

export function useTranscriptionSession(editorRef: React.RefObject<EditorHandle | null>) {
  const [connectionState, setConnectionState] =
    useState<ConnectionState>("DISCONNECTED");
  const [latency, setLatency] = useState(0);
  const [wsUrl, setWsUrlState] = useState(loadWsUrl);
  const [hasContent, setHasContent] = useState(false);
  const [serverStatus, setServerStatus] = useState<ServerStatusState>({
    sessionId: "",
    model: "",
    realtimeModel: "",
    engine: "",
    device: "",
    queueDepth: 0,
    state: "",
    activeSessions: 0,
    activeSpeakers: 0,
    wakeWordEnabled: false,
  });
  const [realtimePreview, setRealtimePreview] = useState<RealtimePreviewState>({
    text: "",
    segmentId: null,
    queueDelayMs: 0,
    inferenceMs: 0,
    latencyMs: 0,
  });
  const [eventLog, setEventLog] = useState<EventEntry[]>([]);

  const wsClientRef = useRef<WebSocketClient | null>(null);
  const audioCaptureRef = useRef<AudioCapture | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const hasContentRef = useRef(false);

  useEffect(() => {
    hasContentRef.current = hasContent;
  }, [hasContent]);

  const addEvent = useCallback((type: string, message: string) => {
    const entry: EventEntry = {
      id: ++eventIdCounter,
      type,
      message,
      timestamp: Date.now(),
    };
    setEventLog((prev) => [entry, ...prev].slice(0, MAX_EVENTS));
  }, []);

  const stopPing = useCallback(() => {
    if (pingIntervalRef.current !== null) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  const startPing = useCallback(() => {
    stopPing();
    pingIntervalRef.current = setInterval(() => {
      const client = wsClientRef.current;
      if (client && client.isOpen) {
        client.sendCommand("ping");
      }
    }, DEFAULTS.pingIntervalMs);
  }, [stopPing]);

  const handleServerMessage = useCallback(
    (message: ServerMessage) => {
      switch (message.type) {
        case "hello":
          setServerStatus((prev) => ({
            ...prev,
            sessionId: message.sessionId ?? prev.sessionId,
          }));
          addEvent("hello", `Session ${message.sessionId ?? ""}`);
          break;

        case "ready":
          setConnectionState("READY");
          setServerStatus((prev) => {
            const s = message.settings ?? {};
            return {
              ...prev,
              sessionId: message.sessionId ?? prev.sessionId,
              model: String(s.model ?? prev.model),
              realtimeModel: String(s.realtime_model ?? s.model ?? prev.realtimeModel),
              engine: String(s.transcription_engine ?? prev.engine),
              device: String(s.device ?? prev.device),
            };
          });
          addEvent("ready", "Server ready");
          break;

        case "status":
          setServerStatus((prev) => ({
            ...prev,
            queueDepth: message.queueDepth ?? prev.queueDepth,
            state: message.state ?? prev.state,
            activeSessions: message.activeSessions ?? prev.activeSessions,
            activeSpeakers: message.activeSpeakers ?? prev.activeSpeakers,
            wakeWordEnabled: message.wakeWordEnabled ?? prev.wakeWordEnabled,
          }));
          if (message.state === "recording") {
            setConnectionState("STREAMING");
          }
          break;

        case "realtime":
          setRealtimePreview({
            text: message.displayText ?? message.text ?? "",
            segmentId: message.segmentId ?? null,
            queueDelayMs: message.queueDelayMs ?? 0,
            inferenceMs: message.inferenceMs ?? 0,
            latencyMs: message.latencyMs ?? 0,
          });
          addEvent("realtime", `[${message.segmentId}] ${(message.displayText ?? message.text ?? "").slice(0, 60)}`);
          break;

        case "final": {
          setRealtimePreview({ text: "", segmentId: null, queueDelayMs: 0, inferenceMs: 0, latencyMs: 0 });
          const finalText = message.text ?? "";
          if (finalText && editorRef.current) {
            editorRef.current.appendFormattedText(finalText);
            setHasContent(true);
          }
          addEvent("final", `[${message.segmentId}] ${finalText.slice(0, 60)}`);
          break;
        }

        case "timeline":
          addEvent("timeline", `${message.event ?? ""} [${message.segmentId ?? ""}]`);
          break;

        case "clear":
          editorRef.current?.clear();
          setHasContent(false);
          setRealtimePreview({ text: "", segmentId: null, queueDelayMs: 0, inferenceMs: 0, latencyMs: 0 });
          addEvent("clear", "Transcript cleared by server");
          break;

        case "warning":
          addEvent("warning", message.message ?? "");
          break;

        case "error":
          addEvent("error", message.message ?? "Unknown error");
          if (message.where === "admission") {
            setConnectionState("ERROR");
          }
          break;

        case "pong":
          setLatency(Math.round(performance.now() - nowAtLastPing));
          break;

        case "metrics":
          addEvent("metrics", "Metrics snapshot received");
          break;
      }
    },
    [addEvent, editorRef]
  );

  let nowAtLastPing = 0;

  const connect = useCallback(() => {
    if (
      connectionState === "CONNECTING" ||
      connectionState === "CONNECTED" ||
      connectionState === "READY" ||
      connectionState === "STREAMING"
    ) {
      return;
    }

    setConnectionState("CONNECTING");
    setLatency(0);
    setServerStatus({
      sessionId: "", model: "", realtimeModel: "", engine: "", device: "",
      queueDepth: 0, state: "", activeSessions: 0, activeSpeakers: 0, wakeWordEnabled: false,
    });

    const client = new WebSocketClient();
    wsClientRef.current = client;
    saveWsUrl(wsUrl);

    client.connect(wsUrl, {
      onOpen: () => {
        setConnectionState("CONNECTED");
        addEvent("connected", "WebSocket connected");
        startPing();
      },
      onClose: () => {
        stopPing();
        audioCaptureRef.current?.stop();
        audioCaptureRef.current = null;
        setConnectionState("CLOSED");
        addEvent("disconnected", "WebSocket disconnected");
        setLatency(0);
      },
      onError: () => {
        addEvent("ws_error", "WebSocket connection error");
        setConnectionState("ERROR");
      },
      onMessage: (message) => {
        nowAtLastPing = performance.now();
        handleServerMessage(message);
      },
    });
  }, [connectionState, wsUrl, startPing, stopPing, addEvent, handleServerMessage]);

  const disconnect = useCallback(() => {
    stopPing();
    audioCaptureRef.current?.stop();
    audioCaptureRef.current = null;
    wsClientRef.current?.disconnect();
    wsClientRef.current = null;
    setConnectionState("DISCONNECTED");
    setLatency(0);
    addEvent("disconnected", "Disconnected");
  }, [stopPing, addEvent]);

  const setWsUrl = useCallback(
    (url: string) => {
      if (connectionState === "DISCONNECTED" || connectionState === "ERROR" || connectionState === "CLOSED") {
        setWsUrlState(url);
      }
    },
    [connectionState]
  );

  const startTranscription = useCallback(async () => {
    if (connectionState !== "READY") return;
    setConnectionState("STREAMING");

    const client = wsClientRef.current;
    if (!client) return;

    client.sendCommand("start");
    addEvent("start_sent", "Start command sent");

    const capture = new AudioCapture();
    audioCaptureRef.current = capture;

    try {
      await capture.start(
        {
          onPacket: (packet: ArrayBuffer) => {
            if (client.isOpen) client.sendAudioPacket(packet);
          },
          onError: (error: string) => addEvent("mic_error", error),
        },
        DEFAULTS.targetChunkMs
      );
    } catch {
      setConnectionState("READY");
      audioCaptureRef.current = null;
    }
  }, [connectionState, addEvent]);

  const stopTranscription = useCallback(() => {
    audioCaptureRef.current?.stop();
    audioCaptureRef.current = null;
    wsClientRef.current?.sendCommand("stop");
    addEvent("stop_sent", "Stop command sent");
    setConnectionState("READY");
    setRealtimePreview({ text: "", segmentId: null, queueDelayMs: 0, inferenceMs: 0, latencyMs: 0 });
  }, [addEvent]);

  const clearTranscript = useCallback(() => {
    editorRef.current?.clear();
    setHasContent(false);
    setRealtimePreview({ text: "", segmentId: null, queueDelayMs: 0, inferenceMs: 0, latencyMs: 0 });
    wsClientRef.current?.sendCommand("clear");
    addEvent("clear_sent", "Clear command sent");
  }, [addEvent, editorRef]);

  const copyTranscript = useCallback(async () => {
    const text = editorRef.current?.getText() ?? "";
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      addEvent("copy", "Transcript copied to clipboard");
    } catch {
      addEvent("copy", "Failed to copy transcript");
    }
  }, [addEvent, editorRef]);

  const exportTranscript = useCallback(
    (format: "txt" | "md" | "html" | "doc") => {
      const html = editorRef.current?.getHTML() ?? "";
      const text = editorRef.current?.getText() ?? "";
      if (!html && !text) return;

      const now = new Date();
      const dateStr =
        `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}-` +
        `${String(now.getHours()).padStart(2, "0")}${String(now.getMinutes()).padStart(2, "0")}${String(now.getSeconds()).padStart(2, "0")}`;

      let content: string;
      let mimeType: string;
      let extension: string;

      switch (format) {
        case "txt":
          content = text;
          mimeType = "text/plain";
          extension = "txt";
          break;
        case "md":
          content = turndown.turndown(html || `<p>${text}</p>`);
          mimeType = "text/markdown";
          extension = "md";
          break;
        case "html":
          content = `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Transcript</title><style>body{font-family:system-ui,sans-serif;max-width:800px;margin:0 auto;padding:20px;line-height:1.6}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:6px}blockquote{border-left:3px solid #ccc;margin:0 0 0 8px;padding:0 12px}pre{background:#f5f5f5;padding:12px;border-radius:4px;overflow-x:auto}</style></head><body>${html}</body></html>`;
          mimeType = "text/html";
          extension = "html";
          break;
        case "doc":
          content = `<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40"><head><meta charset="utf-8"><title>Transcript</title></head><body>${html}</body></html>`;
          mimeType = "application/msword";
          extension = "doc";
          break;
      }

      const blob = new Blob(["\ufeff" + content], { type: mimeType + ";charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `transcript-${dateStr}.${extension}`;
      a.click();
      URL.revokeObjectURL(url);
      addEvent("export", `Exported as .${extension}`);
    },
    [addEvent, editorRef]
  );

  const handleEditorContentChange = useCallback(
    (hasContentVal: boolean) => {
      setHasContent(hasContentVal);
    },
    []
  );

  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasContentRef.current) {
        e.preventDefault();
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, []);

  useEffect(() => {
    return () => {
      stopPing();
      audioCaptureRef.current?.stop();
      wsClientRef.current?.disconnect();
    };
  }, [stopPing]);

  return {
    connectionState,
    latency,
    wsUrl,
    setWsUrl,
    hasContent,
    serverStatus,
    realtimePreview,
    eventLog,
    connect,
    disconnect,
    startTranscription,
    stopTranscription,
    clearTranscript,
    copyTranscript,
    exportTranscript,
    handleEditorContentChange,
  };
}
