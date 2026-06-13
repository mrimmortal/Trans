# Testing and Validation

Use this before and after implementation.

## Test selection

- Add or update focused tests when behavior changes.
- Prefer targeted tests over full test suites for small changes.
- Use unit tests for domain/business logic.
- Use integration tests for API/storage boundaries.
- Use contract tests for API/protocol/message changes.
- Use smoke tests for startup/runtime flows.

## Validation command source

Use commands from `docs/COMMANDS.md`, `AGENTS.md`, README files, package scripts, CI config, existing test files, or actual command output.

Do not invent commands.

## After changes

Run the smallest relevant validation command first. When relevant and available, run tests, lint, typecheck, compile, build, or smoke/startup checks.

## Reporting

- Never claim tests passed unless they actually ran and passed.
- If a command was not run, say it was not run.
- If validation cannot run, explain why.
- If tests fail, report the failure honestly.
- For risky changes, suggest the next validation step.

## Documentation

If new commands are discovered and verified, update `docs/COMMANDS.md`.
