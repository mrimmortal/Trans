# Code Understanding

This document explains the current architecture and the preferred way to extend it. Use it as a developer guide before adding services, providers, domain behavior, endpoints, or frontend integrations.

## Project Shape

This project is a vanilla, wrapper-ready real-time transcription app.

- Frontend: Next.js, React, TipTap.
- Backend: FastAPI.
- Speech engine: Faster-Whisper through a service/provider boundary.
- Realtime transport: `WS /ws/audio`.
- Browser audio format: raw 16-bit PCM, 16 kHz, mono.
- Persistence: browser `localStorage` for sessions, snippets/macros, settings, and autosave.
- Built-in transcription domain: `general`.

The main rule is simple: keep the core transcription pipeline stable and put extension behavior behind existing seams.

## Architecture Overview

### Runtime Flow

1. `frontend/src/app/page.tsx` coordinates the main UI.
2. `frontend/src/hooks/useAudioRecorder.ts` captures microphone audio and emits PCM chunks.
3. `frontend/src/hooks/useWebSocket.ts` sends audio chunks to `WS /ws/audio`.
4. `backend/app/main.py` accepts the WebSocket connection and delegates stream work.
5. `backend/app/websocket/audio_stream_handler.py` handles buffering, VAD decisions, flush timing, and domain post-processing.
6. `backend/app/services/stt/service.py` delegates speech detection and transcription to the configured STT provider.
7. `backend/app/services/stt/faster_whisper.py` implements the Faster-Whisper/Silero provider.
8. `backend/app/websocket/stream_text.py` cleans overlap artifacts from streaming text.
9. `backend/app/domains/registry.py` selects a domain adapter.
10. `backend/app/websocket/responses.py` builds the JSON response sent back to the browser.
11. The frontend processes local voice commands/snippets and inserts text into TipTap.

### Backend Layers

- API/presentation layer: `backend/app/main.py`, `backend/app/api/*_routes.py`.
- Composition layer: `backend/app/dependencies.py`.
- Application service layer: `backend/app/services/*/service.py`.
- Provider/adapters layer: `backend/app/services/*/<provider>.py`.
- Domain layer: `backend/app/domains/*`.
- WebSocket internals: `backend/app/websocket/*`.
- Config: `backend/app/audio_config.py` and service-specific config helpers.
- Schemas: `backend/app/models/schemas.py`.

Routes should stay thin. Business behavior belongs in services, providers, domain adapters, or focused WebSocket modules.

## UI To Backend Service Execution Flow

Use this flow when a UI feature calls a backend REST service, such as the existing Local Assistant flow.

1. A visual component receives user input or a button click.
2. The page or feature hook gathers the required UI state, such as editor text.
3. A focused hook in `frontend/src/hooks/` owns orchestration, loading state, errors, and follow-up actions.
4. A client function in `frontend/src/services/` sends the HTTP request to the backend.
5. The backend route in `backend/app/api/` validates the request with Pydantic schemas.
6. The route gets the application service from `backend/app/dependencies.py`.
7. The application service in `backend/app/services/<service>/service.py` handles provider-independent rules.
8. The provider in `backend/app/services/<service>/<provider>.py` talks to an SDK, local model, file system, or external API.
9. The provider returns a normalized result to the service.
10. The route maps expected errors to HTTP responses and returns the response schema.
11. The frontend service client parses the response.
12. The hook updates UI state and triggers any follow-up work, such as audio playback.
13. The visual component renders the final state.

Current example:

```text
LocalAssistantPanel
  -> page.tsx reads TipTap text
  -> useLocalAssistant
  -> services/assistantApi.ts
  -> POST /llm/respond
  -> api/llm_routes.py
  -> dependencies.create_llm_service()
  -> services/llm/service.py
  -> services/llm/lm_studio.py
  -> response returns to hook and UI
```

If the feature also needs generated speech, the hook then calls:

```text
useLocalAssistant
  -> services/ttsApi.ts
  -> POST /tts/synthesize
  -> api/tts_routes.py
  -> dependencies.create_tts_service()
  -> services/tts/service.py
  -> services/tts/supertonic.py
  -> WAV bytes return to browser playback
```

Do not put REST service calls directly inside visual components when orchestration, retries, loading state, or follow-up actions are involved. Use a hook plus a service client.

## How To Add New Capabilities

### Guide: Add A New Backend Service And API

Use this when adding a new capability with its own backend use case and HTTP endpoint, such as translation, summarization, embedding, export, or classification.

Example goal: add `POST /translate/text`.

1. Define request/response schemas in `backend/app/models/schemas.py`.

```python
class TranslateTextRequest(BaseModel):
    text: str
    target_language: str


class TranslateTextResponse(BaseModel):
    translated_text: str
    provider: str = "local"
```

2. Create a service package:

```text
backend/app/services/translation/
  __init__.py
  base.py
  config.py
  service.py
  local_provider.py
```

3. Define the provider boundary in `base.py`.

```python
from typing import Protocol


class TranslationProviderError(Exception):
    pass


class TranslationProvider(Protocol):
    def translate(self, text: str, target_language: str) -> str:
        ...
```

4. Add provider-independent rules in `service.py`.

```python
class TranslationService:
    def __init__(self, provider: TranslationProvider):
        self._provider = provider

    def translate(self, text: str, target_language: str) -> TranslateTextResponse:
        clean_text = text.strip()
        clean_language = target_language.strip()
        if not clean_text:
            raise ValueError("text must not be empty")
        if not clean_language:
            raise ValueError("target_language must not be empty")

        translated = self._provider.translate(clean_text, clean_language)
        return TranslateTextResponse(translated_text=translated)
```

5. Implement infrastructure details in `local_provider.py`. This is where SDK/API/model/file-system calls belong.
6. Read config through `AudioConfig` and a focused `config.py`; do not scatter `os.getenv(...)`.
7. Add a factory in `backend/app/dependencies.py`.

```python
def create_translation_service(config: AudioConfig | None = None) -> TranslationService:
    audio_config = config or AudioConfig()
    return TranslationService(SomeProvider(get_translation_settings(audio_config)))
```

8. Add a thin route in `backend/app/api/translation_routes.py`.

```python
router = APIRouter(prefix="/translate", tags=["translation"])


@router.post("/text", response_model=TranslateTextResponse)
def translate_text(request: TranslateTextRequest) -> TranslateTextResponse:
    service = create_translation_service()
    try:
        return service.translate(request.text, request.target_language)
    except TranslationProviderError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "TRANSLATION_FAILED", "message": str(exc)},
        ) from exc
```

9. Include the router in `backend/app/main.py`.

```python
from app.api.translation_routes import router as translation_router

app.include_router(translation_router)
```

10. Add tests:
   - `backend/tests/test_translation_service.py`
   - `backend/tests/test_translation_routes.py`
   - provider tests if the provider has meaningful behavior
   - dependency construction coverage in `backend/tests/test_dependencies.py`

Keep the route responsible for HTTP status mapping only. Keep provider construction out of route functions except through `dependencies.py`.

### Guide: Add A New API To An Existing Service

Use this when the service already exists and you only need another endpoint.

Example goal: add `POST /llm/summarize` using the existing LLM service.

1. Add schemas to `backend/app/models/schemas.py`.
2. Add a method to the service if the use case is not already represented.

```python
class LLMService:
    def summarize(self, text: str) -> LLMRespondResponse:
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("text must not be empty")
        return self._provider.respond(
            clean_text,
            system_prompt="Summarize the text clearly and concisely.",
        )
```

3. Add a route function to the existing route module, such as `backend/app/api/llm_routes.py`.

```python
@router.post("/summarize", response_model=LLMRespondResponse)
def summarize_text(request: LLMSummarizeRequest) -> LLMRespondResponse:
    service = create_llm_service()
    try:
        return service.summarize(request.text)
    except LMStudioConfigError as exc:
        raise HTTPException(status_code=503, detail={"code": "LM_STUDIO_CONFIG_ERROR", "message": str(exc)}) from exc
    except LMStudioUnavailableError as exc:
        raise HTTPException(status_code=502, detail={"code": "LM_STUDIO_UNAVAILABLE", "message": str(exc)}) from exc
```

4. Add or update route/service tests.
5. Update frontend service client code if the UI needs to call this endpoint.

Do not create a new service package when the behavior naturally belongs to an existing service boundary.

### Add A New STT Provider

Use this when replacing or adding another speech engine.

1. Implement `STTProvider` from `backend/app/services/stt/base.py`.
2. Return the existing typed dict shapes:
   - `SpeechDetectionResult`
   - `TranscriptionResult`
3. Keep runtime keys compatible with current callers:

```python
{
    "has_speech": bool,
    "speech_prob": float,
    "speech_segments": list,
}
```

```python
{
    "text": str,
    "is_final": bool,
    "confidence": float,
    "processing_time_ms": float,
    "error": str | None,
}
```

4. Add provider config in `backend/app/services/stt/config.py` or a focused config helper.
5. Update only `backend/app/dependencies.py` to choose the new provider.
6. Do not change `WS /ws/audio` unless the public protocol is intentionally changing.
7. Add tests for provider contract, service delegation, and WebSocket handler compatibility.

### Guide: Add A Domain Wrapper

Use domains for wrapper-specific transcript formatting or command behavior. Do not put domain behavior inside STT providers or WebSocket protocol code.

Example goal: add a `legal` wrapper that formats dictated transcript text for legal notes.

1. Create `backend/app/domains/legal.py`.

```python
from app.domains.base import DomainAdapter


class LegalDomainAdapter(DomainAdapter):
    name = "legal"
    commands_enabled = False

    def process_transcript(self, text: str):
        processed = text.strip()
        return processed, []
```

2. Register it in `backend/app/domains/registry.py`.

```python
from app.domains.legal import LegalDomainAdapter

_DOMAIN_REGISTRY: dict[str, type[DomainAdapter]] = {
    GeneralDomainAdapter.name: GeneralDomainAdapter,
    LegalDomainAdapter.name: LegalDomainAdapter,
}
```

Alternatively, a wrapper package can call:

```python
register_domain("legal", LegalDomainAdapter)
```

3. Verify `get_available_domains()` includes `legal`.
4. Use the domain through the existing WebSocket query parameter:

```text
ws://127.0.0.1:8000/ws/audio?domain=legal
```

5. Add tests:
   - `get_domain_adapter("legal")` returns `LegalDomainAdapter`
   - unknown domains still fall back to `general`
   - `process_transcript(...)` returns the expected text and commands
   - WebSocket welcome/config metadata includes the registered domain

6. If the frontend wrapper should choose the domain, add the query parameter in `frontend/src/lib/constants.ts` or wrapper-specific WebSocket URL construction.

Keep `general` vanilla. Unknown domains must continue falling back to `general`.

### Add A WebSocket Control Message

Only do this when the feature is truly part of the realtime audio session.

1. Add parsing/handling in `backend/app/websocket/control_messages.py`.
2. Keep response payload construction in `backend/app/websocket/responses.py` if the response shape is reusable.
3. Update frontend handling in `frontend/src/hooks/useWebSocket.ts`.
4. Update `ARCHITECTURE_GRAPH.md` with the exact message shape.
5. Add contract tests for the message.

Do not route unrelated services through `/ws/audio`. LLM and TTS are intentionally REST flows.

### Add A Frontend Integration For A Backend Service

1. Add API client code under `frontend/src/services/`.
2. Add UI orchestration in a focused hook under `frontend/src/hooks/`.
3. Keep visual components in `frontend/src/components/`.
4. Keep URL constants in `frontend/src/lib/constants.ts`.
5. Keep wrapper branding/toggles in `frontend/src/lib/appConfig.ts`.
6. Do not mix backend REST calls into `useAudioRecorder` or `useWebSocket` unless the feature is part of their existing responsibility.

## Configuration Rules

- Use `backend/app/audio_config.py` as the central environment/config entry point.
- For service-specific settings, create a small `services/<name>/config.py` helper that reads from `AudioConfig`.
- Update `backend/.env.example` when adding required or useful optional settings.
- Do not hardcode local, tunnel, staging, or production URLs.
- Do not add `.env` files to the repository.

## Testing Guide

For backend changes, prefer focused unit tests first, then the full backend suite.

Common targets:

- Service contract tests: `backend/tests/test_<service>_service.py`.
- Provider tests: `backend/tests/test_<provider>_client.py` or similar.
- Route tests: `backend/tests/test_<service>_routes.py`.
- Architecture guard tests: `backend/tests/test_backend_architecture_rules.py`.
- WebSocket contract tests: `backend/tests/test_websocket_pipeline_modules.py`.

Run:

```bash
cd medical-dictation/backend
venv/bin/python -m unittest discover -s tests -v
```

For documentation-only changes:

```bash
cd medical-dictation
git diff --check
```

## Documentation Update Rules

Update docs when a change affects architecture, runtime flow, protocol, config, storage, or cross-module behavior.

- Update `AI_CONTEXT.md` for future AI/developer orientation.
- Update `ARCHITECTURE_GRAPH.md` for runtime flow, protocol, or dependency graph changes.
- Update `backend/app/websocket/README.md` for WebSocket internals.
- Update `docs/adr/*` when a durable architecture decision changes.
- Update `README.md` when setup, run, build, or user-visible behavior changes.

Tiny implementation fixes normally do not need architecture doc updates.

## Extension Checklist

Before implementing:

- Identify whether the change is REST, WebSocket, STT provider, domain adapter, frontend-only, or config-only.
- Confirm the public contract that must stay stable.
- Read the focused files listed above instead of scanning the whole repository.
- Add or update focused tests.

While implementing:

- Keep routes thin.
- Keep provider construction in `backend/app/dependencies.py`.
- Keep environment reads centralized.
- Keep domain behavior out of the vanilla core pipeline.
- Preserve `/ws/audio` unless the task explicitly changes it.
- Do not add a second transcription pipeline.

Before finishing:

- Run relevant tests.
- Run `git diff --check`.
- Update architecture docs if boundaries, runtime flow, config, or contracts changed.
- Report exactly what validation was run.
