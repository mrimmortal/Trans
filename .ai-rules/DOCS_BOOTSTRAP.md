# Docs Bootstrap

Use this when useful project-context docs are missing, outdated, or too weak to reduce future AI/Codex context usage.

## Goal

Create a small project-specific documentation layer so future sessions can avoid scanning the full repository.

## Important rules

- Do not create every markdown file blindly.
- First inspect repo structure, README/package files, CI config, scripts, and key entrypoints.
- Let the detected project architecture decide which docs are necessary.
- Create the smallest useful context set.
- Do not overwrite existing docs without reading them first.
- If a doc exists, update it instead of recreating it.
- Mark unknown facts as `Unknown` or `To verify`; do not guess.
- Keep docs short and practical.
- Prefer pointers to source files instead of copying large explanations.
- User handles git manually; do not perform git actions.

## Default bootstrap set

Create these when missing and useful:
- `AI_CONTEXT.md`
- `docs/COMMANDS.md`
- `docs/MODULE_MAP.md`
- `docs/SESSION_LOG.md`

`AGENTS.md` is normally copied from the reusable rule pack. If missing, create a minimal router version.

## Optional docs

Create only when the repo actually needs them:
- `ARCHITECTURE_GRAPH.md` — architecture, APIs, storage, background jobs, or cross-module runtime flow exist.
- `docs/API_CONTRACTS.md` — public HTTP/RPC/GraphQL APIs exist.
- `docs/PROTOCOL_CONTRACTS.md` — WebSocket, messaging, event, file-format, CLI, SDK, or other protocol contracts exist.
- `docs/INTEGRATION_GUIDE.md` — external systems, clients, SDK consumers, or platform integrations exist.
- `docs/DECISIONS.md` — meaningful architecture/product decisions need tracking.
- `docs/TODO_BACKLOG.md` — known follow-ups, risks, or deferred cleanup exist.
- `docs/FEATURE_WORKFLOW.md` — repeated feature workflow needs to be standardized.

Do not assume a specific technology such as WebSocket, REST, database, queue, frontend framework, or cloud platform. Detect what exists and document only what is useful.

## Suggested file limits

- `AGENTS.md`: under 120 lines when practical.
- `AI_CONTEXT.md`: under 100 lines when practical.
- `docs/COMMANDS.md`: only verified commands.
- `docs/MODULE_MAP.md`: concise mapping, not full code explanation.
- `docs/SESSION_LOG.md`: compact recent entries only.

## `AI_CONTEXT.md` should contain

- project summary
- active modules
- key entrypoints
- important runtime paths
- test/validation starting point
- what future sessions should read first
- unknowns/to verify

## `docs/COMMANDS.md` should contain

Only commands verified from README, package scripts, CI config, repo scripts, or actual command output.

Include only what applies: setup, run, test, lint/typecheck/build, smoke checks, platform-specific notes, dependency-heavy command notes.

## `docs/MODULE_MAP.md` should contain

- common work area
- source files/modules to inspect
- related tests
- related docs
- “do not change unless asked” boundaries

## Contract docs should contain

Create a contract doc only when useful. The contract type can be any technology: HTTP/RPC/GraphQL API, WebSocket, message queue/event contract, CLI command contract, SDK/library interface, file format, database schema boundary, or external system integration.

## `docs/SESSION_LOG.md` entry format

Use after meaningful work:

```md
## YYYY-MM-DD - Task title

Changed:
- ...

Validation:
- ...

Next:
- ...
```

Do not add session log entries for tiny changes unless useful for continuation.
