# AI Rules

Reusable AI/Codex rule pack.

Copy this folder and `AGENTS.md` into a repository. The global Codex custom instruction should stay small and route to these files.

## Files

- `CODING_PRACTICES.md` — coding standards and implementation style.
- `ARCHITECTURE_RULES.md` — modular architecture and refactor rules.
- `TESTING_VALIDATION.md` — test and validation discipline.
- `SECURITY_RULES.md` — safety and security rules.
- `DOCS_BOOTSTRAP.md` — create missing project-context docs based on detected repo architecture.
- `FINAL_RESPONSE.md` — final response format.
- `templates/` — optional templates Codex can use when bootstrapping project docs.

## Principle

Do not assume any specific technology. Codex should decide which project docs are necessary after inspecting the repo.

Keep context files short. Long or unnecessary rules can increase exploration and reduce efficiency.
