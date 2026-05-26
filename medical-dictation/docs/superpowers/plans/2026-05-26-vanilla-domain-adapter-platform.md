# Vanilla Domain Adapter Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate production-grade vanilla transcription from domain-specific behavior so medical, legal, and future use cases can wrap the same core.

**Architecture:** Add a backend domain adapter boundary. `general` is the vanilla default and does not apply medical formatting, templates, or voice commands. `medical` preserves the current formatter/command/template behavior behind an adapter. The WebSocket remains `/ws/audio` and accepts an optional `domain` query parameter.

**Tech Stack:** FastAPI WebSocket, Faster-Whisper, Python unittest, existing Next.js client.

---

### Task 1: Domain Adapter Boundary

**Files:**
- Create: `backend/app/domains/base.py`
- Create: `backend/app/domains/general.py`
- Create: `backend/app/domains/medical.py`
- Create: `backend/app/domains/registry.py`
- Test: `backend/tests/test_domain_adapters.py`

- [ ] Write tests proving `general` returns raw text with no commands and `medical` applies formatter/command processing.
- [ ] Implement `DomainAdapter`, `NoopCommandProcessor`, `GeneralDomainAdapter`, `MedicalDomainAdapter`, and `get_domain_adapter`.
- [ ] Run `venv/bin/python -m unittest tests.test_domain_adapters`.

### Task 2: WebSocket Handler Integration

**Files:**
- Modify: `backend/app/audio_config.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_audio_stream_handler_domains.py`

- [ ] Add tests proving `AudioStreamHandler(..., domain="general")` does not apply medical formatting/commands and `domain="medical"` does.
- [ ] Add `DEFAULT_TRANSCRIPTION_DOMAIN=general`.
- [ ] Update `AudioStreamHandler` to use domain adapters and expose `domain`.
- [ ] Let `/ws/audio?domain=medical` select the medical adapter, otherwise use default.
- [ ] Run `venv/bin/python -m unittest tests.test_audio_stream_handler_domains`.

### Task 3: Docs And Verification

**Files:**
- Modify: `AI_CONTEXT.md`
- Modify: `ARCHITECTURE_GRAPH.md`
- Modify: `frontend/src/types/index.ts`

- [ ] Document vanilla core/domain adapter split and WebSocket domain selection.
- [ ] Add optional `domain` to server config type.
- [ ] Run backend tests, Python compile, frontend TypeScript, and frontend build.
