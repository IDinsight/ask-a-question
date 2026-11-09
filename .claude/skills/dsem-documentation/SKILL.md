---
name: dsem-documentation
description: Use whenever creating, changing, reviewing, or refactoring code, configuration, APIs, data models, user flows, setup steps, tests, deployment behavior, operations, security posture, or architecture in any project so documentation stays current automatically. Operates across two controls: mode (review or implement) and target level (1–5, from spike notes to public production runbooks). Triggered explicitly via `/dsem documentation <prompt>`. When triggered, first read `.agents/skills/planner/SKILL.md`.
---

# Documentation

Use this skill as a level-aware documentation impact pass for repository changes. The goal is to keep docs current with minimal manual effort from engineers while matching the selected project maturity level.

Do not finish a code/config/API change by merely saying documentation should be updated. Update the relevant documentation files in the same change unless the user explicitly asks not to.

## Invocation

Triggered by `/dsem documentation <prompt>` or when the planner routes documentation work here.

- **Mode** is inferred from the prompt: _update, write, create, add_ → implement; _review, assess, check, audit_ → review.
- **Target level** (1–5) is confirmed before work begins.

## Planner Prerequisite

Before applying this skill, read `.agents/skills/planner/SKILL.md` and run the planner pass first. Use it to confirm operating mode, target level, affected layers, blocking questions, assumptions, task order, additional skills or references, and verification expectations.

If the planner routes part of the work to another skill, load that skill before editing files in that area.

## Level Clarification Prerequisite

This skill operates on two independent controls: **operating mode** (`review` or `implement`) and **target level** (`1`-`5`). Documentation uses the same target level as API, Android, Next.js, and security unless the user explicitly overrides it.

For **reviews**: identify and report the current documentation level for each affected area, then compare it to the target level.

For **implementation**: confirm the target level before editing docs. Do not document higher-level capabilities as implemented when they are deferred.

**Level 1 — Spike notes.** Minimal setup/run instructions, prototype status, major limitations, mock/static data callouts, and smoke-test/manual-check notes.

**Level 2 — Connected prototype docs.** Adds real data/backend setup, environment variables, primary workflow, happy-path and failure-path checks, and basic architecture notes.

**Level 3 — Internally testable docs.** Explains full layered architecture, setup from a clean checkout, API contracts, auth behavior, test commands, CI checks, troubleshooting, and developer handoff. This is the default for maintainable internal work.

**Level 4 — Pre-production docs.** Adds staging/deployment procedures, migration and rollback notes, observability/audit logging, performance/accessibility checks, rate limits or abuse controls, and operational ownership.

**Level 5 — Public production docs.** Adds SLIs/SLOs, incident runbooks, backup/restore evidence, disaster recovery, data retention/privacy notes, secrets-management expectations, production monitoring, support escalation, versioning policy, and zero-downtime release procedures.

## Operating Mode

### Review mode

Use when the user asks to assess documentation quality, readiness, or gaps.

1. Inspect repository docs, API contracts, env examples, runbooks, planning files, and changed files when relevant.
2. Do not modify files.
3. Determine current documentation level by evidence, not file names alone.
4. Compare against the target level.
5. Report missing, stale, misleading, or over-claimed documentation and the smallest path to the target level.

### Implement mode

Use when the user asks to create or update docs as part of code/config/API/architecture work.

1. Inspect changed files with `git status --short` and, when useful, `git diff --name-only`.
2. Identify whether the change affects behavior, setup, public contracts, architecture, configuration, data models, workflows, tests, deployment, security, operations, or product scope.
3. Update the nearest relevant documentation file.
4. If no suitable README exists for a changed top-level area, create one only when the change introduces setup instructions, architecture, commands, external contracts, or operational knowledge.
5. Re-read edited docs and verify they match implementation, file paths, commands, and selected level exactly.

## Reference Loading

Load `.agents/skills/documentation/references/readme.md` when creating or substantially restructuring a README. Use the project’s existing docs style first; use the reference as the fallback structure.

When a stack-specific docs question arises, use the relevant stack skill or current official docs as the source of truth:

- Android architecture: https://developer.android.com/topic/architecture
- Next.js App Router authentication and data security: https://nextjs.org/docs/app/guides/authentication
- FastAPI security: https://fastapi.tiangolo.com/tutorial/security/
- OWASP Top 10:2025: https://owasp.org/Top10/2025/0x00_2025-Introduction/
- OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/

## Primary Documentation Targets

First identify how the project is laid out. Map common folder names to the actual repository structure.

- **Backend README**: setup, run/test commands, layered architecture, dependencies, env vars, database/migration steps, auth behavior, background jobs, observability, and implemented API behavior.
- **API contract/spec**: paths, methods, request/response schemas, status codes, auth/security, pagination, errors, enums, uploads, idempotency, operation descriptions, and shared components.
- **Android README**: setup, build/test commands, architecture, Compose/Material 3 patterns, API integration, offline save, local storage, queued sync, WorkManager, environment/config, and QA steps.
- **Next.js/frontend README**: setup, scripts, routes, user flows, data fetching, auth, environment variables, deployment, and testing.
- **Planning/project-management docs**: product scope, status, estimates, priorities, completed work, and links to source-of-truth docs.
- **Operational docs**: `.env.example`, sample config, migration notes, ADRs, generated API/client docs, runbooks, monitoring notes, incident procedures, and release docs.

## API Spec Rules

When the project keeps an API contract or spec, treat it as the backend/client contract and keep it synchronized with implementation and client expectations.

Update it when a change adds, removes, renames, or changes endpoint paths, methods, parameters, headers, request bodies, response bodies, status codes, schemas, validation, auth/security, pagination, errors, uploads, idempotency, or operation descriptions.

Do not update the spec for purely internal refactors that do not change the public API contract. Preserve existing OpenAPI style and component reuse, keep stable operation IDs unless the operation changes, and validate YAML structure if tooling is available.

## Level-Aware Architecture Documentation

Document the actual implemented shape:

- **Level 1:** inline spike, mock/static data, no durable architecture promises.
- **Level 2:** thin layers and real data/backend integration.
- **Level 3:** full layered architecture: UI/router/controller, service/use case, persistence/query layer, models/entities, schemas/DTOs, tests.
- **Level 4:** repository layer where warranted, observability, audit logging, staging, migration/rollback, performance/accessibility/security hardening.
- **Level 5:** production operations: SLOs, incident response, backup/restore, DR, retention/privacy, secrets manager, versioning, and zero-downtime release.

Do not imply a Level 4 or Level 5 capability is present just because it is desirable. List it under deferred capabilities when the selected level is lower.

## Change Mapping

- API route/service/schema/auth/error changes: update backend README and API contract/spec.
- API-only internal refactor: update backend README only if architecture, setup, commands, or behavior changed.
- Database model or migration changes: update README with migration/run/test details and affected API schemas.
- Android offline/sync/data/network changes: update Android README; update API contract/spec if client expectations changed.
- Compose UI or Material 3 changes: update Android README when feature, navigation, pattern, or QA flow changed.
- Web route/auth/data-fetching changes: update frontend README; update API docs/spec if backend contracts changed.
- Environment/config changes: update README and `.env.example` or sample config.
- Test or command changes: update README command sections.
- Scope/status changes: update planning/project-management docs.

## Minimal Effort Principle

Make the smallest documentation edits that keep future engineers unblocked:

- Do not rewrite whole READMEs unless they are empty, generated boilerplate, or misleading.
- Co-locate docs with the changed area before creating broad root-level docs.
- Prefer exact commands and paths over vague prose.
- Record deferred higher-level work explicitly when useful.
- If a doc would be misleading without a missing decision from the user, add a short limitation and surface the open question in the final response.

## Review Checklist

Before finishing:

- Operating mode and target level are clear.
- Relevant docs are updated or intentionally unchanged for a clear reason.
- Public API contract changes are reflected in the spec.
- New commands, dependencies, env vars, ports, migrations, and QA steps are documented.
- Cross-area changes are reflected in every affected area.
- Documentation uses real paths, commands, behavior, and level language from the repo.
- Deferred higher-level capabilities are not described as implemented.
- Final response lists documentation files changed and any docs intentionally left unchanged.
