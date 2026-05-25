# Environment Guide

This project has four supported environments.

## DEV-MAC

Local macOS development.

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

Backend dependencies are installed into `backend/venv` from:

```text
backend/requirements-mac.txt
```

Default URLs:

```text
Frontend: http://localhost:3000
Backend:  http://127.0.0.1:8000
WebSocket: ws://127.0.0.1:8000/ws/audio
```

## DEV-WINDOWS

Local Windows development.

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

Backend dependencies are installed into `backend\venv` from:

```text
backend/requirements.txt
```

Default URLs:

```text
Frontend: http://localhost:3000
Backend:  http://127.0.0.1:8000
WebSocket: ws://127.0.0.1:8000/ws/audio
```

`backend/requirements.txt` is the Windows dependency file. For CUDA on Windows, edit `backend/.env.windows` after verifying the machine has a working CUDA stack:

```text
DEVICE=cuda
COMPUTE_TYPE=float16
```

Keep the default CPU settings for machines without CUDA.

## UAT

Hosted Windows web app used for acceptance testing before production.

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

GitHub Actions deployment target:

```text
Environment: UAT
Runner labels: self-hosted, Windows, uat-win
Deploy command: scripts/run.ps1 uat-win
Service restart: handled by scripts/run.ps1
```

Required GitHub environment secrets:

```text
UAT_BACKEND_ENV
UAT_FRONTEND_ENV
```

Optional GitHub environment variables:

```text
WIN_INSTALL_ROOT
BACKEND_SERVICE_NAME
FRONTEND_SERVICE_NAME
```

## PROD-WIN

Hosted Windows production web app.

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

GitHub Actions deployment target:

```text
Environment: Production
Runner labels: self-hosted, Windows, prod-win
Deploy command: scripts/run.ps1 prod-win
Service restart: handled by scripts/run.ps1
```

Required GitHub environment secrets:

```text
PROD_BACKEND_ENV
PROD_FRONTEND_ENV
```

Optional GitHub environment variables:

```text
WIN_INSTALL_ROOT
BACKEND_SERVICE_NAME
FRONTEND_SERVICE_NAME
```

Production deploys only run from a manual workflow dispatch targeting `prod-win` or a pushed version tag matching `v*`.

## Pipeline

GitHub Actions workflow:

```text
.github/workflows/medical-dictation-pipeline.yml
```

Jobs:

```text
mac-dev-validate   runs on macos-latest
win-dev-validate   runs on windows-latest
package-deployment creates the source artifact
deploy-uat-win     runs on self-hosted Windows runner labeled uat-win
deploy-prod-win    runs on self-hosted Windows runner labeled prod-win
```

Branch and deployment behavior:

```text
pull_request to main/develop/custome_template: validate only
push to custome_template or develop: validate, package, deploy UAT
push tag v*: validate, package, deploy Production
manual dispatch uat-win: validate, package, deploy UAT
manual dispatch prod-win: validate, package, deploy Production
```

## Rules

- Do not hardcode dev tunnel URLs in `frontend/src/lib/constants.ts`.
- Frontend API/WebSocket URLs must come from `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL`.
- Backend CORS must come from `CORS_ORIGINS`.
- UAT must use HTTPS and WSS.
- Production must use HTTPS and WSS.
- UAT and Production deployments require self-hosted Windows GitHub Actions runners with the labels above.
- If an environment file changes the runtime contract, update `AI_CONTEXT.md` and `ARCHITECTURE_GRAPH.md`.
