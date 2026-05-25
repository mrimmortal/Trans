# Balanced Realtime Transcription Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce perceived transcription delay while preserving enough audio context to avoid missing words.

**Architecture:** Keep the existing final-transcript WebSocket protocol. Tune backend buffering and Whisper inference defaults through `AudioConfig`, then expose real processing timing in handler results and WebSocket responses.

**Tech Stack:** FastAPI, Faster-Whisper, Silero VAD/RMS VAD, Python unittest, Next.js client unchanged.

---

### Task 1: Realtime Config Defaults

**Files:**
- Modify: `backend/app/audio_config.py`
- Test: `backend/tests/test_audio_config_realtime.py`

- [ ] Add tests asserting the default profile uses shorter realtime thresholds: `MIN_CHUNK_DURATION_SECONDS == 0.6`, `SILENCE_TIMEOUT_SECONDS == 0.7`, `MAX_CHUNK_DURATION_SECONDS == 6.0`, `BEAM_SIZE == 2`, and byte sizes derive from duration.
- [ ] Update `AudioConfig` defaults to those values.
- [ ] Run: `venv/bin/python -m unittest tests.test_audio_config_realtime`

### Task 2: Transcription Timing Metadata

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_audio_stream_handler_latency.py`

- [ ] Add a unit test with a fake engine returning text plus `processing_time_ms`; verify `_transcribe_buffer()` returns that timing, audio duration, and a flush reason.
- [ ] Track `pending_flush_reason` for natural pause, max buffer, manual flush, and unknown.
- [ ] Include timing metadata in the WebSocket transcription response instead of the current hardcoded `50`.
- [ ] Run: `venv/bin/python -m unittest tests.test_audio_stream_handler_latency`

### Task 3: Docs And Verification

**Files:**
- Modify: `AI_CONTEXT.md`
- Modify: `ARCHITECTURE_GRAPH.md`

- [ ] Document the balanced realtime defaults and final-only insertion constraint.
- [ ] Run backend unit tests and compile check.
- [ ] Run frontend TypeScript/build checks to confirm protocol compatibility.
