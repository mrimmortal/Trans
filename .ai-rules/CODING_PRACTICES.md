# Coding Practices

Use this for normal feature work, bug fixes, cleanup, and small improvements.

## Core rules

- Make the smallest safe change that solves the task.
- Preserve existing behavior unless explicitly asked to change it.
- Follow existing project patterns, naming, folder structure, and style.
- Verify facts from source code or docs before changing anything.
- Do not guess file names, functions, commands, APIs, env vars, dependencies, or runtime behavior.
- Search before creating new helpers, abstractions, configs, or dependencies.
- Do not add dependencies unless clearly required.
- Do not rename, restructure, or refactor unrelated code.
- Avoid broad formatting-only changes.
- Avoid hidden side effects.

## Clean code

Write code that is simple, readable, explicit, testable, loosely coupled, highly cohesive, and easy to delete or replace.

Functions should do one clear thing, have clear names, avoid surprising side effects, avoid excessive parameters, return predictable results, and keep IO and pure logic separate where practical.

Classes/modules should have one clear reason to change, expose small public APIs, hide internal implementation details, avoid unnecessary inheritance, and avoid becoming dumping grounds.

## Naming

- Use clear domain language.
- Avoid vague names like `manager`, `helper`, or `utils` unless truly generic.
- Prefer explicit names over abbreviations.

## Comments

- Prefer self-explanatory code.
- Add comments only for non-obvious decisions, constraints, or tradeoffs.
- Remove outdated comments.

## Refactoring

- Refactor incrementally.
- Keep behavior unchanged unless asked.
- Add or adjust tests around moved logic when possible.
- Do not combine major refactor with feature work unless required.
- Preserve public contracts unless explicitly changing them.
- Remove dead code only when verified unused or directly part of the task.
