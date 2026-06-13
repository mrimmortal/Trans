# AGENTS.md

This file routes AI/Codex sessions to the smallest useful context.

## Read order

For every task:
1. Read this file first.
2. Read `AI_CONTEXT.md` if present.
3. Read only the relevant `.ai-rules/*.md` files for the task.
4. Read project docs in `docs/` only when needed.
5. Inspect source files only after identifying the smallest relevant file set.

Do not scan the whole repository by default.

## Rule routing

Use these reusable rules:

- `.ai-rules/CODING_PRACTICES.md` — default coding standards for most tasks.
- `.ai-rules/ARCHITECTURE_RULES.md` — use for architecture, refactor, module boundaries, public contracts, storage, deployment, or cross-module work.
- `.ai-rules/TESTING_VALIDATION.md` — use before and after implementation.
- `.ai-rules/SECURITY_RULES.md` — use for APIs, auth, secrets, parsing, subprocesses, networking, files, protocols, integrations, and user input.
- `.ai-rules/DOCS_BOOTSTRAP.md` — use when project AI-context docs are missing or outdated.
- `.ai-rules/FINAL_RESPONSE.md` — use before final response.

## Context-saving rule

Prefer repo markdown files over rediscovering context repeatedly.

If useful project docs are missing, create the smallest useful set using `.ai-rules/DOCS_BOOTSTRAP.md`.

## File safety

- Do not overwrite user work.
- Do not edit secrets or real `.env` files.
- Do not edit generated files, caches, build outputs, virtualenvs, model downloads, or compiled artifacts unless explicitly required.
- Do not change unrelated files.

## Git

User handles git manually.

Do not:
- create branches
- commit
- amend commits
- push
- open PRs
- run git workflow actions

Use normal file editing only unless the user explicitly asks for git work.

## Project-specific docs

Codex should create/update project-specific docs only when useful.

Common docs:
- `AI_CONTEXT.md`
- `docs/COMMANDS.md`
- `docs/MODULE_MAP.md`
- `docs/SESSION_LOG.md`

Optional docs, decided by repo architecture:
- `ARCHITECTURE_GRAPH.md`
- `docs/API_CONTRACTS.md`
- `docs/PROTOCOL_CONTRACTS.md`
- `docs/INTEGRATION_GUIDE.md`
- `docs/DECISIONS.md`
- `docs/TODO_BACKLOG.md`
- `docs/FEATURE_WORKFLOW.md`

Keep all docs short and practical.
