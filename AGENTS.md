# AI Coding Instructions

Before changing this project, read:

1. `medical-dictation/AI_CONTEXT.md`
2. `medical-dictation/ENVIRONMENTS.md` when setup, deployment, URLs, CORS, or platform behavior matters
3. `medical-dictation/ARCHITECTURE_GRAPH.md` only when architecture or data flow matters

Keep AI context small:

- Do not scan the whole repository first.
- Start from the files named in `AI_CONTEXT.md`.
- Treat paths, endpoint names, storage keys, and protocol details in these docs as facts to verify before changing.
- If a requested change touches audio, WebSocket messages, templates, commands, editor insertion, or persistence, update the graph docs in the same change.
- Do not invent alternate endpoints. The backend WebSocket endpoint is `/ws/audio`.
- Do not duplicate core transcription, formatting, command, or template logic in new places.
- Do not hardcode temporary tunnel URLs in source code. Use environment files and `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL`.
- Keep DEV-MAC, DEV-WINDOWS, UAT-WIN, PROD-WIN, and pipeline docs current after environment-related changes.
- Deployment pipeline source of truth is `.github/workflows/medical-dictation-pipeline.yml` plus `medical-dictation/scripts/run.ps1`.
