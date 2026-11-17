---
name: dsem-api-setup
description: >
  Use this skill to scaffold or review a backend API project. Framework-agnostic —
  stack-specific details live in references/stacks/. Operates across two controls:
  mode (review or implement) and target level (1–5, from API spike to public
  production). Triggered explicitly via `/dsem api-setup <prompt>`.
  When triggered, first read .agents/skills/planner/SKILL.md.
  Works for new projects and existing projects being upgraded.
---

# API Setup Skill

This skill is framework-agnostic. The layered architecture principles defined here apply to any stack. Stack-specific folder names, dependency choices, and implementation patterns live in the stack reference.

This skill operates on two independent controls: **operating mode** (review or implement) and **target level** (1–5). Confirm both before doing any work.

## Invocation

Triggered by `/dsem api-setup <prompt>` or when the planner routes API scaffolding/setup work here.

- **Mode** is inferred from the prompt: _scaffold, create, set up, bootstrap_ → implement; _review, assess, audit, evaluate_ → review.
- **Target level** (1–5) is inferred or confirmed before work begins.

## Planner Prerequisite

Before applying this skill, read `.agents/skills/planner/SKILL.md` and run the planner pass first.

If the planner routes part of the work to another skill, load that skill before editing files in that area.

## Level Clarification Prerequisite

For **reviews**: identify and report the current level. For **implementation**: confirm the target level before starting. Do not implement above the selected level.

**Level 1 — API spike.** All logic lives in the router. In-memory or dummy data only. No database, no auth, no persistent state. OpenAPI documentation exposed. Smoke tests only. Goal: validate the API contract and routing as quickly as possible. Label the result as a disposable prototype not suitable for shared use.

**Level 2 — Database-backed prototype.** Adds a thin service layer and real persistence. Database configured with migration tooling, dev and test databases. Basic environment configuration. Happy-path and at least one failure-path test. Goal: validate the primary workflow with real data.

**Level 3 — Internally testable service (sweet spot).** Full layered architecture: HTTP concerns in the router, business logic in the service/use case layer, data access in the persistence layer (query modules or persistence functions). Consistent error mapping. Explicit transaction ownership. Auth and authorization where the product requires it. Restrictive CORS and baseline security headers. Unit, integration, and API tests covering edge cases. Linting, formatting, type checking, and CI. Setup and architecture documentation. Goal: maintainable service suitable for internal testing. Most projects should target this level.

**Level 4 — Operationally mature pre-production API.** Builds on Level 3. Introduces a formal repository layer between service and database. Structured and redacted logging with request and correlation IDs. Observability hooks: metrics, error tracking, tracing. Robust auth with refresh tokens and revocation. Rate limiting and abuse protection. Audit logging. Secure container configuration. CI quality gates. Reproducible staging deployment. Migration and rollback procedures documented. Goal: ready for staging and controlled external testing.

**Level 5 — Public production API.** Builds on Level 4. Adds explicit SLIs/SLOs, load and capacity tests, idempotency for retryable writes, graceful startup and shutdown, multi-instance correctness, safe deployment and rollback automation, zero-downtime migrations, tested backup restoration, disaster-recovery planning, threat modeling, secrets-manager integration, data retention and privacy controls, incident runbooks, and API versioning policy.

## Operating Mode

### Review mode

Use when the user asks to assess, audit, evaluate, or recommend improvements.

1. Inspect the repository, configuration, tests, and documentation.
2. Do not create or modify files. Do not install or remove dependencies.
3. Determine current maturity across: architecture, data management, testing, security, observability, and delivery.
4. Compare against the target level.
5. Report: inferred current level, evidence, strengths, risks, missing requirements, prioritized path to target, and what is optional vs necessary.

Do not assign a level based on directory names or dependency presence alone. Require evidence that the relevant behavior works.

### Implement mode

Use when the user asks to create, scaffold, configure, upgrade, or modify an API.

1. Determine whether this is a new scaffold or an upgrade of an existing project.
2. For an existing project: infer the current level first.
3. Confirm only blocking questions before implementation.
4. Preserve established project conventions when they are technically sound.
5. Implement no more than the selected target level.
6. Verify each gate before continuing to the next step.
7. Report all changes, command results, unresolved blockers, and intentionally deferred higher-level capabilities.

## Reference Loading

Load only the files that apply before starting work.

### Stack reference (always)

| Framework        | Load                           |
| ---------------- | ------------------------------ |
| FastAPI / Python | `references/stacks/fastapi.md` |

If no reference exists for the requested framework, inform the user and ask whether to adapt the closest available one or pause until a reference is added.

### Database reference (Level 2+)

Level 1 requires no database reference.

For Level 2+, always load `references/database/database.md`, then load the variant:

| Database                   | Load                                        |
| -------------------------- | ------------------------------------------- |
| PostgreSQL                 | `references/database/variants/postgres.md`  |
| PostgreSQL + pgvector      | `references/database/variants/postgres.md` then `references/database/variants/pgvector.md` |
| MongoDB                    | `references/database/variants/mongodb.md`   |
| Redis (optional add-on)   | `references/database/variants/redis.md`     |

### Observability reference (Level 3+)

Load `references/observability.md` at Level 3+. This is an evaluation guide — it describes what to look for and what good looks like at each level. It does not prescribe tooling.

### Security

Security hardening is outside the scope of this skill. At Level 3+, apply baseline security headers as specified in the stack reference. For deeper hardening or a security review, use the security skill at `.agents/skills/security/`.

## Pre-flight

Confirm the following in a single message before doing anything.

**Always required:** operating mode, target level, framework/stack.

**Implement mode only:** project name (used for directory and database names), project directory.

**Level 2+:** primary database, pgvector (yes/no), Redis (yes/no).

Present a summary and wait for explicit confirmation.

## Scaffold (implement mode)

Implement only steps at or below the target level. Defer the rest and list them in the handoff.

Follow the loaded stack reference for folder structure, dependency names, and specific implementation patterns. The layer boundaries below are authoritative regardless of framework.

### Layer responsibilities

**Router / controller:** HTTP concerns only. Request parsing, input validation, auth dependency injection, mapping results to response schemas, HTTP status codes. No business logic. No direct database calls.

**Service / use case:** Business logic, rules, orchestration, authorization checks. Calls the persistence layer. Does not know about HTTP. Does not write queries directly.

**Persistence layer (Level 3):** Query modules or persistence functions. Owns query logic. Translates between domain objects and database models. Services call these functions; they do not write queries themselves.

**Repository layer (Level 4):** Formal persistence boundary introduced when services grow cluttered with query logic or the same data-access logic is reused across services. Do not introduce a repository for every model automatically.

**Models and schemas:** ORM entities, domain/app models, and API schemas are kept separate. DTOs cross the HTTP boundary; ORM entities cross the DB boundary; domain models live in between.

### Step routing

| Step                                                                | Min level |
| ------------------------------------------------------------------- | --------- |
| Project init: git, .gitignore, entry point                          | 1         |
| Folder structure (per stack reference)                              | 1         |
| Router layer                                                        | 1         |
| In-memory / dummy data                                              | 1         |
| OpenAPI / schema documentation                                      | 1         |
| Smoke tests                                                         | 1         |
| Environment config (.env.example, .env, .env.test)                  | 2         |
| Database setup (naming, connectivity, migrations)                   | 2         |
| Service layer                                                       | 2         |
| Happy-path and failure-path tests                                   | 2         |
| Persistence layer (query modules)                                   | 3         |
| Middleware: CORS, request ID, global error handler                  | 3         |
| Baseline security headers                                           | 3         |
| Auth and authorization                                              | 3         |
| Full test suite: unit, integration, API, edge cases                 | 3         |
| Linting, formatting, type checking, CI                              | 3         |
| Repository layer                                                    | 4         |
| Structured and redacted logging, request/correlation IDs            | 4         |
| Observability hooks (metrics, error tracking, tracing)              | 4         |
| Refresh tokens, revocation, rate limiting, audit logging            | 4         |
| Containerisation: Dockerfile, docker-compose                        | 4         |
| Operational readiness: SLOs, load tests, runbooks, secrets rotation | 5         |

## Review checklist (review mode)

For each dimension below, determine the current maturity and compare to the target level.

**Architecture:** Are HTTP, business, and persistence responsibilities separated? Does the layer depth match the claimed level? Does business logic live in services rather than routers or models?

**Data management:** Is schema state managed through migrations only? Are dev and test databases isolated? Are indexes and constraints appropriate for the access patterns?

**Testing:** Are the right test types present for the level? Do tests run against an isolated test database? Are edge cases and failure paths covered?

**Security:** Are baseline security headers present (Level 3+)? Is auth tested? Are secrets absent from version control?

**Observability:** Is structured logging in place (Level 4+)? Are metrics and error tracking configured? Can a request be traced across the system?

**Delivery:** Is CI configured (Level 3+)? Can another engineer run the project from the documentation alone? Is staging reproducible (Level 4+)?

## Verification gates

Run the gate for the target level before reporting done.

**Level 1:** Application starts. Example endpoint responds correctly. Invalid input is rejected. Smoke tests pass.

**Level 2:** Migrations apply cleanly. Database connectivity succeeds. Primary workflow persists and retrieves data. Happy-path tests pass against the test database.

**Level 3:** CI passes. HTTP, business, and persistence responsibilities are separated and tested independently. Auth behavior tested where present. Another engineer can run the project from the documentation alone.

**Level 4:** Staging deployment succeeds. Observability signals reach their configured destinations. Migration and rollback procedures are documented and tested. Critical security controls are tested.

**Level 5:** Representative load tests pass. Alerts have been exercised. Backup restoration has been demonstrated. Deployment and rollback have been tested end-to-end. Production ownership and incident procedures are documented.

## Handoff (implement mode)

Summarise:

- Project structure (one-level tree)
- Databases created (names and connection strings)
- Dependencies installed with versions
- How to run: dev server, tests, Docker

**Deferred capabilities:** list every step above the target level that was intentionally skipped with a one-line note on what it adds.
