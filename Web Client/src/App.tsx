import { useRef } from "react";
import type { EditorHandle } from "./components/TranscriptEditor";
import { useTranscriptionSession } from "./hooks/useTranscriptionSession";
import { ConnectionPanel } from "./components/ConnectionPanel";
import { TranscriptionControls } from "./components/TranscriptionControls";
import { RealtimePreview } from "./components/RealtimePreview";
import { TranscriptEditor } from "./components/TranscriptEditor";
import { TranscriptToolbar } from "./components/TranscriptToolbar";
import { EventLog } from "./components/EventLog";
import { ServerStatusPanel } from "./components/ServerStatusPanel";
import "./styles/app.css";

export default function App() {
  const editorRef = useRef<EditorHandle | null>(null);

  const {
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
  } = useTranscriptionSession(editorRef);

  return (
    <>
      <header className="top-bar">
        <h1>CoreSTT Web Client</h1>
        <div className="top-bar-right">
          <span className="chip">
            <span
              className={`dot ${
                connectionState === "STREAMING"
                  ? "red"
                  : connectionState === "READY"
                    ? "green"
                    : connectionState === "CONNECTING" ||
                        connectionState === "CONNECTED"
                      ? "amber"
                      : "gray"
              }`}
            />
            {connectionState}
          </span>
          <span className="chip">{latency} ms</span>
        </div>
      </header>

      <div className="app-layout">
        <aside className="left-panel">
          <ConnectionPanel
            wsUrl={wsUrl}
            connectionState={connectionState}
            latency={latency}
            onUrlChange={setWsUrl}
            onConnect={connect}
            onDisconnect={disconnect}
          />
          <TranscriptionControls
            connectionState={connectionState}
            hasContent={hasContent}
            onStart={startTranscription}
            onStop={stopTranscription}
            onClear={clearTranscript}
          />
          <TranscriptToolbar
            hasContent={hasContent}
            onCopy={copyTranscript}
            onExportTxt={() => exportTranscript("txt")}
            onExportMd={() => exportTranscript("md")}
            onExportHtml={() => exportTranscript("html")}
            onExportDoc={() => exportTranscript("doc")}
          />
          <ServerStatusPanel status={serverStatus} />
          <EventLog events={eventLog} />
        </aside>

        <main className="main-panel">
          <RealtimePreview preview={realtimePreview} />
          <TranscriptEditor
            ref={editorRef}
            onContentChange={handleEditorContentChange}
          />
        </main>
      </div>
    </>
  );
}
