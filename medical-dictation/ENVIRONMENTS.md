# Environment Guide

This project has four supported environments.

## DEV-MAC

Backend env:

```text
backend/.env.mac
```

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

## DEV-WINDOWS

Backend env:

```text
backend/.env.windows
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

## UAT

Backend env:

```text
backend/.env.uat
```

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
backend/.env.prod
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

## Pipeline

GitHub Actions workflow:

```text
.github/workflows/medical-dictation-pipeline.yml
```

The workflow filename still uses the original folder naming. Treat the workflow plus `scripts/run.ps1` as the deployment source of truth until the repository path is renamed.

## Rules

- Do not hardcode dev tunnel URLs in `frontend/src/lib/constants.ts`.
- Frontend API/WebSocket URLs must come from `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL`.
- Backend CORS origins must come from `CORS_ORIGINS`.
- Keep `DEFAULT_TRANSCRIPTION_DOMAIN=general` unless a wrapper adds and documents a new adapter.

## Last Updated Notes

- 2026-05-26: Removed built-in domain-specific environment notes. Vanilla deploys use only `/ws/audio` and the `general` domain.
