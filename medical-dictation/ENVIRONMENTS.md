# Environment Guide

This project has four supported environments.

## DEV-MAC

Backend env:

```text
optional: copy backend/.env.example to backend/.env.mac for local overrides
```

If `backend/.env.mac` is absent, `./scripts/run.sh mac-dev` uses `backend/.env.example`.

Frontend env:

```text
frontend/.env.local.mac
```

Start both services:

```bash
cd medical-dictation
./scripts/run.sh mac-dev
```

Default URLs:

```text
Frontend: http://localhost:3000
Backend:  http://127.0.0.1:8000
WebSocket: ws://127.0.0.1:8000/ws/audio
```

Backend transcription domain defaults to vanilla/general:

```text
DEFAULT_TRANSCRIPTION_DOMAIN=general
```

Recommended Mac CPU backend profile:

```text
MODEL_SIZE=base
DEVICE=cpu
COMPUTE_TYPE=int8
```

## DEV-WINDOWS

Backend env:

```text
copy backend/.env.example to backend/.env.windows
```

Frontend env:

```text
frontend/.env.local.windows
```

Start both services from PowerShell:

```powershell
cd medical-dictation
.\scripts\run.ps1 win-dev
```

Default URLs:

```text
Frontend: http://localhost:3000
Backend:  http://127.0.0.1:8000
WebSocket: ws://127.0.0.1:8000/ws/audio
```

Backend transcription domain defaults to vanilla/general:

```text
DEFAULT_TRANSCRIPTION_DOMAIN=general
```

Recommended Windows CPU backend profile:

```text
MODEL_SIZE=base
DEVICE=cpu
COMPUTE_TYPE=int8
```

Recommended Windows GPU backend profile:

```text
MODEL_SIZE=base
DEVICE=cuda
COMPUTE_TYPE=float16
```

## RASPBERRY-PI CPU

Use the same backend env pattern as local development, with smaller model settings:

```text
MODEL_SIZE=tiny
DEVICE=cpu
COMPUTE_TYPE=int8
```

## UAT

Backend env:

```text
copy backend/.env.example to backend/.env.uat
```

For local `uat-check` validation only, `./scripts/run.sh uat-check` falls back to `backend/.env.example` when `backend/.env.uat` is absent.

Frontend env:

```text
frontend/.env.uat
```

Before deploying UAT, replace placeholder domains:

```text
backend/.env.uat: CORS_ORIGINS=https://uat.example.com
frontend/.env.uat: NEXT_PUBLIC_API_URL=https://api-uat.example.com
frontend/.env.uat: NEXT_PUBLIC_WS_URL=wss://api-uat.example.com/ws/audio
```

Validation build:

```bash
cd medical-dictation
./scripts/run.sh uat-check
```

## PROD-WIN

Backend env:

```text
copy backend/.env.example to backend/.env.prod
```

Frontend env:

```text
frontend/.env.prod
```

Before deploying production, replace placeholder domains:

```text
backend/.env.prod: CORS_ORIGINS=https://app.example.com
frontend/.env.prod: NEXT_PUBLIC_API_URL=https://api.example.com
frontend/.env.prod: NEXT_PUBLIC_WS_URL=wss://api.example.com/ws/audio
```

Production deploys only run from a manual workflow dispatch targeting `prod-win` or a pushed version tag matching `v*`.

Local production validation on macOS/Linux:

```bash
cd medical-dictation
./scripts/run.sh prod-check
```

## Pipeline

GitHub Actions workflow:

```text
.github/workflows/medical-dictation-pipeline.yml
```

The workflow filename still uses the original folder naming. Treat the workflow plus `scripts/run.ps1` as the deployment source of truth until the repository path is renamed.

## Rules

- Keep real backend `.env*` files local and untracked. Commit only `backend/.env.example`.
- Local macOS, UAT, and production shell validation helpers may fall back to `backend/.env.example` when local backend `.env*` files are absent.
- Do not hardcode dev tunnel URLs in `frontend/src/lib/constants.ts`.
- Frontend API/WebSocket URLs must come from `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL`.
- Backend CORS origins must come from `CORS_ORIGINS`.
- Keep `DEFAULT_TRANSCRIPTION_DOMAIN=general` unless a wrapper adds and documents a new adapter.
- Use `/diagnostics` and `/diagnostics/*` for local provider health checks before changing env values.

## Last Updated Notes

- 2026-05-26: Removed built-in domain-specific environment notes. Vanilla deploys use only `/ws/audio` and the `general` domain.
- 2026-05-30: Backend real env files are local-only; `backend/.env.example` is the committed template.
- 2026-05-30: `scripts/run.sh` now falls back to `backend/.env.example` for missing local backend env files during macOS dev and local UAT checks.
- 2026-05-30: Added `scripts/run.sh prod-check` for local production build validation.
- 2026-06-02: Documented CPU/GPU/Raspberry Pi profile recommendations and diagnostics health-check guidance.
