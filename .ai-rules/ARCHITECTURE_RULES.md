# Architecture Rules

Use this for architecture, public contracts, APIs, protocols, storage, config, deployment, cross-module behavior, large refactors, or module-boundary changes.

## Planning

Before architecture changes:
- Make a short plan.
- Explain current structure briefly.
- Explain proposed modular design.
- List affected files/modules.
- Mention migration or compatibility risk.
- Keep changes incremental.

## Modular architecture

Prefer clear separation of concerns, single responsibility per module, explicit boundaries between layers, dependency injection where useful, interfaces/ports for external systems when useful, adapters for infrastructure/framework code, pure business logic separated from IO/frameworks where practical, simple composition over inheritance, and readable names over clever abstractions.

Avoid god files, god classes, circular imports, hidden global state, business logic inside controllers/routes/components, direct database calls from UI/controller layers, framework-specific code inside core domain logic, large utilities dumping unrelated functions together, premature abstraction, unnecessary design patterns, and unnecessary microservices.

## Recommended layering when suitable

- presentation / API / UI layer
- application / use-case layer
- domain / business logic layer
- infrastructure / adapters layer
- shared utilities only for truly generic code

Dependency direction:
- outer layers may depend on inner layers
- inner/domain layers should not depend on framework, database, UI, or external APIs
- external systems should be accessed through interfaces/adapters where practical

## Frontend

- Separate UI components, hooks, services, config, types, and state management.
- Keep components focused and small.
- Keep client/integration logic outside visual components.
- Avoid mixing business rules into styling components.
- Avoid global state unless needed.

## Backend

- Separate routes/controllers, schemas/DTOs, services/use-cases, domain logic, repositories/adapters, config, and infrastructure.
- Keep routes/controllers thin.
- Validate inputs at system boundaries.
- Centralize config access.
- Centralize logging and error handling where appropriate.
- Avoid scattered direct environment variable reads.
- Do not leak sensitive details in errors or logs.

## Public contracts

Do not change these unless explicitly asked:
- public APIs
- protocols/message contracts
- CLI contracts
- SDK/library interfaces
- config names
- file formats
- database schemas
- runtime behavior
- external integration contracts

If any contract changes, update the relevant project docs.
