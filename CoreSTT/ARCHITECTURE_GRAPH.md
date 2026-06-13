# CoreSTT Architecture Graph

## Browser Streaming Flow

```text
static/index.html
  -> WS /ws/transcribe
  -> protocol.decode_audio_packet()
  -> CoreSTTService.packet_to_server_samples()
  -> RecorderBackedRealtimeSession
  -> AudioToTextRecorder
  -> SchedulerTranscriptionExecutor
  -> InferenceScheduler
  -> SharedEngineWorker
  -> CoreSTT.transcription_engines.create_transcription_engine()
  -> WebSocket realtime/final/status/timeline events
```

## macOS Client Streaming Flow

```text
../MacOS SwiftUI app
  -> MicrophoneAudioStreamer
  -> AudioPacketEncoder
  -> WebSocketTranscriptionClient
  -> WS /ws/transcribe
  -> same CoreSTT server flow as browser streaming
  -> SwiftUI transcript/status/event views
```

## Main Modules

- `server.py`: FastAPI app, settings, sessions, scheduler, metrics, websocket route.
- `protocol.py`: browser binary audio packet encode/decode and input validation helpers.
- `static/index.html`: microphone capture, signal display, timeline, transcript rendering, websocket commands.
- `../MacOS/`: native SwiftUI macOS client for the same websocket protocol.
- `CoreSTT/audio_recorder.py`: recorder compatibility boundary.
- `CoreSTT/transcription_engines/`: ASR engine contracts and adapters.

## Runtime Boundaries

- Browser audio packets must be binary with a 4-byte little-endian metadata
  length, JSON metadata, and `pcm_s16le` payload.
- External clients, including `../MacOS/`, must keep the same packet layout and
  JSON control messages as the browser client.
- The server owns session admission, runtime config, queue limits, and shared
  inference workers.
- The recorder owns VAD, wake-word callbacks, recording lifecycle, and final
  transcript collection.
- The transcription engine adapters own model loading and ASR execution.
