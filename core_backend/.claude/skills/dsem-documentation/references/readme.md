---
name: documentation-skill-readme
description: >
  Level-aware README guidance. Load when creating or substantially restructuring a
  project or area README. Apply only the sections required by the selected target
  level and the repository's actual stack.
---

# README Reference

A `README.md` should be present at every implementation level, but its depth must match the target level. Use the repository's existing README style first; use this as a fallback structure.

Do not describe higher-level capabilities as implemented. Put them under **Deferred Capabilities** when they are intentionally outside the selected level.

## Level-Aware Expectations

| Level | README expectation |
| ----- | ------------------ |
| **Level 1 — Spike** | Project purpose, prototype status, how to run the demo, smoke/manual check, mock/static/in-memory data limits. |
| **Level 2 — Connected prototype** | Adds real data/backend setup, env vars, primary workflow, basic architecture, and happy/failure checks. |
| **Level 3 — Internally testable** | Adds layered architecture, clean-checkout setup, API contracts, auth behavior, automated test commands, CI, troubleshooting, and developer handoff. |
| **Level 4 — Pre-production** | Adds staging/deployment, migration and rollback, observability/audit logging, rate limits or abuse controls, accessibility/performance/security checks, and operational ownership. |
| **Level 5 — Public production** | Adds SLOs/SLIs, incident runbooks, backup/restore, DR, privacy/data retention, secrets management, production monitoring, support escalation, versioning, and zero-downtime release procedures. |

## Suggested Structure

# Project Name

One or two sentences explaining what the project does and who it is for.

## Status

- Target level:
- Current level:
- Production status: Prototype / Internal / Staging / Production
- Current version:
- Build status:
- Documentation:
- Service health or monitoring: `Level 4+ only`

## Tech Stack

- Language:
- Framework:
- Database:
- Messaging or queues:
- Infrastructure:
- Testing:
- Observability:

## Setup Instructions

### Prerequisites

- List required software, libraries, tools, and versions.

### Installation

Include only real setup required at the selected level:

- dependency installation;
- database or data-layer setup, if Level 2+;
- environment variables or configuration files;
- seed scripts, if applicable;
- how to run the application locally.

## Run, Build, And Test

```sh
# exact commands from the repository
```

For Level 1, smoke/manual checks may be enough. For Level 3+, include automated test, lint, type-check, and build commands where they exist.

## Repository Structure

```text
.
├── src/          # Application source code
├── tests/        # Automated tests
├── scripts/      # Development and operational scripts
├── docs/         # Additional documentation
├── config/       # Configuration files
├── migrations/   # Database migrations, Level 2+
└── README.md
```

Use the actual repository paths. Do not paste this tree unchanged if it does not match.

## Architecture

Explain the implemented architecture at the selected level.

- **Level 1:** inline spike, mock/static data, no durable architecture promise.
- **Level 2:** thin layers and real data/backend integration.
- **Level 3:** full layered architecture. Show UI/router/controller, service/use case, persistence/query layer, models/entities, schemas/DTOs, and tests.
- **Level 4:** repository layer where warranted, observability, audit logging, staging, migration/rollback, and operational hardening.
- **Level 5:** production operations: SLOs, incident response, backup/restore, DR, retention/privacy, secrets manager, versioning, zero-downtime release.

Categorize architecture by feature where useful so a reader can see UI, API/router, service, repository/persistence, database, sync, and operational boundaries.

Include a Mermaid diagram only when the repository already uses Mermaid or the diagram materially improves handoff.

## API Contract

Include when an API exists:

- source-of-truth spec path;
- auth/security scheme;
- base URL or local route prefix;
- pagination/error conventions;
- idempotency or versioning policy when required by level.

## Configuration

Document env vars and secrets without exposing real values.

| Name | Required | Level | Purpose |
| ---- | -------- | ----- | ------- |
| `EXAMPLE_VAR` | yes/no | L2+ | ... |

At Level 4+, include staging/production differences. At Level 5, point to the secrets manager or operational process.

## Operations

Include only when required by the selected level:

- deployment and staging: Level 4+;
- migration and rollback: Level 4+;
- observability and audit logs: Level 4+;
- SLOs, incident response, backup/restore, DR, privacy/retention: Level 5.

## Manual QA

List realistic manual checks, especially for UI, mobile, offline/sync, security, and deployment behavior that automated tests do not cover.

## Deferred Capabilities

List important items above the selected level that were intentionally not implemented or documented as complete.

| Capability | Required at | Reason deferred |
| ---------- | ----------- | --------------- |
| ... | L4/L5 | Target is L3 |
