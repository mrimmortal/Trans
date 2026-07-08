# Audio Processing - Whisper Flow

Use this file to orient audio-processing work for the current Whisper flow
without scanning the full repo. For external WebSocket clients, also read
`docs/WEBSOCKET_CLIENT_CONTRACT.md`.

## Main Flow

Browser or client audio enters `WS /ws/transcribe` as binary packets:

```text
client microphone/file -> CoreSTT audio packet -> decode -> validate -> mono int16 -> 16 kHz -> faster-whisper realtime/final inference
```

Key implementation points:

- `CoreSTT/protocol.py` encodes and decodes binary audio packets.
- `CoreSTT/server.py` owns WebSocket ingestion, packet validation, session
  buffering, VAD checks, realtime inference jobs, and final inference jobs.
- `CoreSTT/CoreSTT/server/audio.py` owns server sample constants, WAV loading,
  int16 resampling, and effective device selection.
- `CoreSTT/CoreSTT/server/inference.py` builds faster-whisper engine config for
  realtime and final jobs.
- `CoreSTT/CoreSTT/transcription_engines/faster_whisper_engine.py` loads
  `faster_whisper.WhisperModel`, optionally wraps it in
  `BatchedInferencePipeline`, and calls `model.transcribe(...)`.

## Terminology

These are the audio and transcription terms used by the current
faster-whisper streaming flow.

| Term | Meaning in this project |
|---|---|
| Audio packet | One binary WebSocket message containing metadata plus PCM audio bytes. Encoded and decoded by `CoreSTT/protocol.py`. |
| Metadata | JSON object at the start of each audio packet. It carries fields such as `sampleRate`, `channels`, `format`, and optional `frames`. |
| Metadata length | The first 4 bytes of an audio packet. It is an unsigned 32-bit little-endian integer telling the server how many metadata bytes follow. |
| PCM | Pulse-code modulation: raw audio sample values without a container such as WAV or MP3. CoreSTT streaming accepts raw PCM bytes inside its packet format. |
| `pcm_s16le` | Signed 16-bit little-endian PCM. This is the only accepted streaming packet audio format. Each sample uses 2 bytes. |
| Sample | One measured audio amplitude value. In `pcm_s16le`, each sample is an integer from `-32768` to `32767`. |
| Sample rate | Number of samples per second, in hertz. Clients send the original `sampleRate`; the server resamples streaming audio to `16000 Hz`. |
| Frame | One time step of audio across all channels. For mono audio, one frame is one sample. For stereo audio, one frame contains two channel samples. |
| Frame width | Bytes per frame. In this project it is `channels * 2` because `pcm_s16le` uses 2 bytes per channel sample. |
| Channel | One audio stream inside the packet. Mono has 1 channel; stereo has 2. The server accepts up to 8 channels and averages multi-channel audio to mono. |
| Mono | Single-channel audio. This is the recommended client format and the server's internal streaming shape after channel mixing. |
| Chunk | A small group of audio frames sent in one packet. The browser client targets about `40 ms` chunks before server-side resampling. |
| Resampling | Converting samples from the input sample rate to another sample rate. Streaming input is resampled to `SERVER_SAMPLE_RATE`, currently `16000 Hz`. |
| `SERVER_SAMPLE_RATE` | Server internal streaming sample rate constant in `CoreSTT/CoreSTT/server/audio.py`; currently `16000`. |
| Int16 audio | Audio represented as signed 16-bit integers. Packet payloads arrive as int16 PCM. |
| Float32 audio | Audio represented as 32-bit floating-point values, usually normalized near `-1.0` to `1.0`. This is the shape passed into faster-whisper inference jobs. |
| Normalization | Preparing audio before faster-whisper transcription. `FasterWhisperEngine.transcribe(...)` calls `_normalize_audio(...)` before `model.transcribe(...)`. |
| Clipping | Limiting sample values to a valid range. Client Float32 capture should be clamped to `[-1.0, 1.0]` before conversion to int16. |
| RMS | Root mean square amplitude. The server uses RMS as the fallback energy measurement for voice activity detection. |
| VAD | Voice activity detection. Used to decide whether an audio region contains speech. Server streaming uses `webrtcvad` when available, then falls back to RMS energy. |
| `webrtcvad` | Optional VAD library used by `VoiceActivityDetector` in `CoreSTT/server.py`. It checks fixed-size 16 kHz int16 frames. |
| Energy threshold | RMS cutoff used by fallback VAD. Configured by `vad_energy_threshold`. |
| Prebuffer | Recent audio kept before recording starts so the beginning of speech is not lost. Configured by `pre_recording_buffer_duration`. |
| Recording frames | In-memory samples for the current active speech segment in `RealtimeSession.recording_frames`. |
| Recording sample count | Count of samples accumulated for the current recording. Used to decide whether enough audio exists for realtime inference. |
| Realtime transcription | Interim faster-whisper transcription while the user is still speaking. It uses the realtime model/settings and is throttled by `realtime_processing_pause`. |
| Final transcription | Faster-whisper transcription after a recording segment is complete. It produces the committed final text for a segment. |
| Inference job | Work item submitted to the scheduler for realtime or final faster-whisper transcription. It contains audio, language, prompt settings, segment id, and timing data. |
| Segment | One logical speech/transcript unit tracked by the server timeline and transcript state. Realtime and final messages refer to segment ids. |
| faster-whisper | The default transcription backend in this checkout. The adapter lives in `CoreSTT/CoreSTT/transcription_engines/faster_whisper_engine.py`. |
| Whisper model | The `faster_whisper.WhisperModel` instance created with model name/path, device, compute type, GPU index, and optional download root. |
| Realtime model | The model/settings used for interim transcription. Defaults come from `realtime_model` and `beam_size_realtime`. |
| Final model | The model/settings used for committed transcript segments. Defaults come from `model` and `beam_size`. |
| Beam size | Decoding search width passed to faster-whisper as `beam_size`. Final and realtime paths can use different values. |
| Batch size | Optional faster-whisper batched inference setting. When `batch_size > 0`, the adapter wraps the model in `BatchedInferencePipeline`. |
| faster-whisper VAD filter | faster-whisper's own `vad_filter` option passed to `model.transcribe(...)`. This is separate from the server's speech-start/speech-stop VAD. |
| Initial prompt | Text prompt passed to faster-whisper as `initial_prompt` to bias vocabulary, style, or domain. |
| Hotwords | Domain/profile words passed to faster-whisper as `hotwords` when configured. |
| Domain profile | Server-owned profile selected by WebSocket `start.domain`; in the faster-whisper flow it can provide prompts and hotword biasing for a session. |
| Queue depth | Amount of pending audio or inference work. Used in status and metrics to expose overload or latency pressure. |
| Dropped chunk | Audio chunk the server could not keep because of queue/session limits. Tracked in session diagnostics. |
| Stale realtime job | Realtime inference work discarded because it became too old or no longer matched the current session generation. |

## Audio Packet Contract

The WebSocket packet format is:

```text
[uint32 metadataLength little-endian][metadata JSON UTF-8][pcm_s16le audio bytes]
```

Current server requirements:

- `sampleRate` metadata is required and must be a positive integer.
- `channels` defaults to `1`, must be positive, and must be at most `8`.
- `format` defaults to `pcm_s16le`; no other packet audio format is accepted.
- Payload bytes must align to whole frames: `channels * 2` bytes per frame.
- Optional `frames` metadata, when present, must match payload length.
- Metadata is capped at `64 KiB` in `CoreSTT/protocol.py`.
- Full packet size is capped by `ServerSettings.max_audio_packet_bytes`; the
  default is `512 KiB`.

Keep `docs/WEBSOCKET_CLIENT_CONTRACT.md` in sync when changing packet layout,
metadata rules, accepted formats, server response shapes, or client lifecycle
requirements.

## Internal Audio Shape

Server-side streaming normalizes packet audio to:

- signed 16-bit integer samples after packet decode;
- mono audio, by averaging channels when `channels > 1`;
- `16000 Hz`, via `resample_int16(..., SERVER_SAMPLE_RATE)`;
- float32 arrays for inference paths that need normalized model input.

`SERVER_SAMPLE_RATE` is currently `16000` in `CoreSTT/CoreSTT/server/audio.py`.
`INT16_MAX_ABS_VALUE` is `32768.0` for int16-to-float scaling.

## Realtime Processing

`RealtimeSession` in `CoreSTT/server.py` tracks per-session audio state:

- `prebuffer` retains recent audio before recording starts.
- `recording_frames` holds current segment samples.
- `recording_sample_count` gates realtime inference.
- `realtime_processing_pause` throttles realtime job submission.
- `realtime_min_audio_seconds` prevents too-short realtime jobs.
- `realtime_max_audio_seconds` limits audio sent to realtime inference.
- `max_realtime_queue_age_ms` gives realtime jobs a deadline.

Voice activity detection first attempts `webrtcvad` when available. If that
fails or is unavailable, the server falls back to RMS energy with
`vad_energy_threshold`.

## Tuning Knobs

Start with `CoreSTT/CoreSTT/server/settings.py` and
`CoreSTT/CoreSTT/server/cli.py` for configurable faster-whisper flow behavior:

- Input/session controls: `audio_queue_size`, `max_audio_packet_bytes`,
  `max_audio_queue_seconds_per_session`, `pre_recording_buffer_duration`,
  `min_length_of_recording`, `post_speech_silence_duration`,
  `realtime_processing_pause`, `realtime_min_audio_seconds`,
  `realtime_max_audio_seconds`, `vad_energy_threshold`, `webrtc_sensitivity`.
- faster-whisper model controls: `model`, `realtime_model`, `language`,
  `device`, `compute_type`, `gpu_device_index`, `download_root`.
- faster-whisper decode controls: `beam_size`, `beam_size_realtime`,
  `batch_size`, `realtime_batch_size`, `vad_filter`, `normalize_audio`,
  `initial_prompt`, `initial_prompt_realtime`.
- Domain biasing: `domain_profiles_path`, `default_domain`, profile
  `initial_prompt`, profile `initial_prompt_realtime`, and profile `hotwords`.

Some settings are active runtime settings, some apply only to new sessions, and
some are startup-only. Check `ACTIVE_RUNTIME_SETTINGS`,
`NEW_SESSION_RUNTIME_SETTINGS`, and `STARTUP_ONLY_SETTINGS` before changing
runtime config behavior.

## Tests To Start With

For packet/protocol changes:

```bash
cd CoreSTT
.venv/bin/python -m unittest tests/test_server_protocol.py
```

For server settings, limits, and config exposure:

```bash
cd CoreSTT
.venv/bin/python -m unittest tests/test_server_config.py
```

For broad validation after audio behavior changes:

```bash
cd CoreSTT
.venv/bin/python -m unittest discover tests
```

Create `CoreSTT/.venv` and install `CoreSTT/requirements.txt` before running
tests. See `docs/COMMANDS.md` for setup details.

## Boundaries

- Do not change the binary packet contract without updating tests and
  `docs/WEBSOCKET_CLIENT_CONTRACT.md`.
- Do not weaken packet size, metadata, channel, frame alignment, or format
  validation.
- Do not change faster-whisper prompt, hotword, VAD-filter, beam, batching, or
  model-selection behavior without focused tests.
- Do not add audio dependencies unless the existing fallback paths are
  insufficient and the change is intentional.
- Treat model downloads and virtualenvs as generated/local artifacts, not AI
  edit targets.
