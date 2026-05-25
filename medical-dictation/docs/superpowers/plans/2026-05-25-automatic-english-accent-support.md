# Automatic English Accent Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve recognition for multiple English accents using backend model/prompt configuration.

**Architecture:** Keep the existing WebSocket protocol and UI. Add accent-aware config in `AudioConfig`, pass the composed prompt into Faster-Whisper, and expose the accent settings through `/config` and the WebSocket welcome config.

**Tech Stack:** FastAPI, Faster-Whisper, Python unittest, Next.js type compatibility.

---

### Task 1: Accent Config

**Files:**
- Modify: `backend/app/audio_config.py`
- Create: `backend/tests/test_accent_support_config.py`

- [ ] Add tests for `ACCENT_SUPPORT_ENABLED`, `TRANSCRIPTION_LANGUAGE`, accent-aware model default, and prompt composition.
- [ ] Implement config fields and prompt composition.
- [ ] Run `venv/bin/python -m unittest tests.test_accent_support_config`.

### Task 2: Whisper Argument Contract

**Files:**
- Modify: `backend/app/services/transcription_engine.py`
- Create: `backend/tests/test_transcription_engine_accent_support.py`

- [ ] Add a fake model test proving `_run_whisper` sends `language=config.TRANSCRIPTION_LANGUAGE` and `initial_prompt=config.get_initial_prompt()`.
- [ ] Update `_run_whisper` and `transcribe_file` to use config language and composed prompt.
- [ ] Run `venv/bin/python -m unittest tests.test_transcription_engine_accent_support`.

### Task 3: Protocol Metadata And Docs

**Files:**
- Modify: `backend/app/main.py`
- Modify: `frontend/src/types/index.ts`
- Modify: `AI_CONTEXT.md`
- Modify: `ARCHITECTURE_GRAPH.md`

- [ ] Expose accent support metadata in REST `/config` and WebSocket connected config.
- [ ] Add optional frontend type fields.
- [ ] Update AI docs.
- [ ] Run backend tests, Python compile, TypeScript, and frontend build.
