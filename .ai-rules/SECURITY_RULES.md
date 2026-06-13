# Security Rules

Use this for APIs, auth, secrets, parsing, subprocesses, networking, file handling, protocols, external integrations, and user-provided input.

## Secrets

Never edit, expose, log, or hardcode secrets, tokens, passwords, API keys, private certificates, real `.env` files, credentials, local machine paths, or production/staging/tunnel URLs.

Use example files such as `.env.example` when documentation is needed.

## Generated/local files

Do not edit generated/local files unless explicitly required: `__pycache__`, `.pyc`, `node_modules`, virtualenvs, logs, coverage output, temporary files, model downloads, compiled artifacts, and build outputs.

## Validation and boundaries

Treat parsers, file uploads/downloads, subprocess calls, shell commands, network requests, auth and permissions, protocol/API message handling, user-provided input, serialization/deserialization, and config loading as security-sensitive.

## Do not weaken safeguards

Do not weaken validation, tests, logging safety, error handling, authentication, authorization, permission checks, input boundaries, or rate/size limits unless explicitly asked.

## Logging/errors

- Avoid logging secrets or sensitive data.
- Make errors actionable but safe.
- Do not leak internal sensitive details in user-facing errors.
