# CoreSTT Web Client

A Vite + React + TypeScript transcription editor that connects to the CoreSTT WebSocket microservice, streams microphone audio, receives realtime/final transcript messages, and provides an editable transcript editor.

## How it connects to CoreSTT

The app connects to the CoreSTT server via WebSocket at `/ws/transcribe`. It follows the contract in `docs/WEBSOCKET_CLIENT_CONTRACT.md`:

- Sends JSON control messages (`start`, `stop`, `clear`, `ping`, `metrics`)
- Sends binary audio packets (`[uint32 metadataLength LE][JSON metadata][pcm_s16le audio]`)
- Receives `hello`, `ready`, `status`, `realtime`, `final`, `timeline`, `clear`, `warning`, `error`, `pong`, and `metrics` messages

## How to run CoreSTT server

From the repo root:

```bash
cd CoreSTT
.venv/bin/python server.py --host 127.0.0.1 --port 8020 --device cpu --no-model-warmup
```

Domain-specific example with medical dictation prompts:

```bash
cd CoreSTT
.venv/bin/python server.py \
  --model small.en \
  --realtime-model tiny.en \
  --language en \
  --initial-prompt "This is a medical dictation. Common terms include hypertension, diabetes mellitus, HbA1c, atorvastatin, metformin, dyspnea, auscultation, tachycardia, creatinine, eGFR." \
  --initial-prompt-realtime "Medical dictation. Use clinical terms and drug names accurately."
```

## How to run Web Client

```bash
cd "Web Client"
npm install
npm run dev
```

## Default WebSocket URL

```
ws://127.0.0.1:8020/ws/transcribe
```

## Commands

| Command | Description |
|---|---|
| `npm install` | Install dependencies |
| `npm run dev` | Start dev server |
| `npm run build` | TypeScript check and production build |
| `npm run preview` | Preview production build |

## Manual test steps

1. Start the CoreSTT server (see above)
2. Start the web client (`npm run dev`)
3. Open the app in a browser (default `http://localhost:5173`)
4. Verify the WebSocket URL is `ws://127.0.0.1:8020/ws/transcribe`
5. Click **Connect** — connection state should show "READY"
6. Click **Start Transcription** — allow microphone permission
7. Speak — realtime transcript should appear in the preview panel
8. After silence, final segments should append to the editor
9. Edit the transcript manually — edits should not be overwritten
10. Click **Stop Transcription** — streaming should stop
11. Use **Copy**, **Export .txt**, **Export .md** to export the transcript
12. Click **Clear Transcript** to reset
13. Close and reopen the page — transcript draft should be restored

## Known limitations

- AudioWorklet is preferred but falls back to ScriptProcessor if unavailable
- No automatic reconnection with backoff (reconnect manually via Disconnect/Connect)
- Editor is a plain textarea (not contenteditable); final segments are appended as newline-separated text
- No wake-word support in this client
- No audio visualizer
