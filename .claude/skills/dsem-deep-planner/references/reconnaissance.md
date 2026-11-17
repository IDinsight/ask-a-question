# Repository Reconnaissance

## Contents

- Repository shape
- Runtime and build stack
- Feature-adjacent execution paths
- Existing analogues
- Constraints and invariants
- Test and validation inventory
- Search strategy
- Large repositories
- Handling uncertainty

## Repository shape

Identify:

- monorepo or single application;
- applications, packages, services, libraries, workers, and infrastructure directories;
- generated-code directories;
- vendored or third-party code;
- ownership boundaries;
- planning, ADR, and agent-instruction files.

Start with likely orientation files:

```text
README*
AGENTS.md
CLAUDE.md
CONTRIBUTING*
CONTEXT.md
CONTEXT-MAP.md
docs/
package.json
pnpm-workspace.yaml
yarn.lock
package-lock.json
pyproject.toml
uv.lock
poetry.lock
go.mod
Cargo.toml
Gemfile
composer.json
pom.xml
build.gradle*
*.sln
Directory.Build.*
Makefile
Taskfile.yml
docker-compose*
Dockerfile*
.github/workflows/
```

Do not dump the entire tree. Record the smallest useful structural map.

## Runtime and build stack

Determine, with file evidence:

- languages and versions;
- frameworks and package managers;
- build tools and runtime entry points;
- local development commands;
- test, lint, formatting, and type-check tools;
- code generation;
- container and deployment setup;
- CI checks and environment configuration;
- persistence and migration tooling;
- external integrations.
- maturity signals for each affected stack: Level 1 spike, Level 2 connected prototype, Level 3 internally testable, Level 4 pre-production, or Level 5 production.

Prefer exact findings:

```md
- `apps/api/package.json` — NestJS API; `npm run start:dev` starts local development.
- `apps/api/src/main.ts` — creates the HTTP application and installs global pipes.
- `.github/workflows/api.yml` — runs lint, unit tests, and build on pull requests.
```

Avoid vague findings such as “The backend uses Node” or “There are some tests.”

## Feature-adjacent execution paths

Trace concrete files and symbols through every relevant layer.

For a backend feature:

```text
request entry
→ router/controller
→ validation
→ application/service layer
→ domain/service logic
→ persistence/query layer
→ repository/data access where Level 4+ or existing convention warrants it
→ database or external integration
→ response mapping
→ logging/telemetry
→ tests
```

For a frontend feature:

```text
route
→ page/screen
→ state/data loader
→ API client
→ components
→ forms and validation
→ error/loading/empty states
→ analytics
→ tests
```

For infrastructure:

```text
source configuration
→ build artifact
→ deployment definition
→ secrets/configuration
→ runtime health checks
→ observability
→ rollback path
```

## Existing analogues

Find the nearest implemented feature, not merely files with matching words. Record:

- reusable code and patterns;
- house-style tests;
- important differences from the requested feature;
- utilities or abstractions that should not be duplicated.

Example:

```md
`src/modules/invitations/` is the closest vertical slice:

- `invitations.controller.ts` shows route and DTO conventions.
- `invitations.service.ts` shows transaction boundaries.
- `invitations.repository.ts` shows query composition.
- `invitations.e2e-spec.ts` shows the expected test harness.

Authentication differs because it is cross-cutting and also integrates with
`src/bootstrap/http.ts` and request context.
```

## Constraints and invariants

Inspect tenancy, authorization, transactions, backward compatibility, API contracts, event schemas, migration safety, idempotency, performance budgets, platform support, feature flags, security, audit, and observability.

Classify every constraint:

- **Verified constraint** — backed by a file or test.
- **Requested constraint** — supplied by the user.
- **Proposed constraint** — introduced by the plan.
- **Level constraint** — required by the selected target level or intentionally deferred above it.
- **Unknown** — unresolved and potentially blocking.

## Test and validation inventory

Find exact commands and locations for:

- unit, integration, and end-to-end tests;
- lint, formatting, type checking, and build;
- schema and migration validation;
- contract tests;
- manual validation;
- required CI workflows.
- target-level verification gates, such as smoke checks for Level 1, happy/failure checks for Level 2, full automated checks for Level 3, staging/observability checks for Level 4, and production readiness evidence for Level 5.

Never invent a command. Explicitly report commands that cannot be found.

## Search strategy

Move from high signal to narrow detail:

1. repository instructions and manifests;
2. application entry points;
3. feature keywords and domain terms;
4. nearest analogous feature;
5. call sites and dependency edges;
6. tests;
7. configuration and CI;
8. history only when current code does not explain a decision.

Search route strings, exported symbols, data-store names, event names, environment variables, feature flags, error codes, test descriptions, dependency registrations, and migration identifiers. Use semantic and literal search when available.

## Large repositories

Divide reconnaissance by bounded concern when necessary:

- repository and build topology;
- backend path;
- frontend path;
- persistence;
- infrastructure;
- tests and CI;
- domain language.

When parallel exploration is authorized, require each result to contain:

```md
## Scope inspected
## Operating mode and target level
## Relevant files
| Path | Role | Key symbols |
## Current flow
## Existing conventions
## Current level evidence
## Constraints
## Unknowns
## Suggested plan implications
```

Reconcile results into one canonical `CURRENT-STATE.md`; do not concatenate raw reports.

## Handling uncertainty

Classify each uncertainty:

- **Resolvable by inspection** — continue exploring.
- **Resolvable by a non-destructive command** — run it.
- **Requires product or domain input** — record an open question.
- **Requires implementation experiment** — create a spike task.
- **Non-blocking** — select and document a safe default.
- **Blocking** — prevent dependent tasks from being marked ready.
- **Level-affecting** — changes the target level, assessed current level, or whether a higher-level capability is in scope.

Do not hide uncertainty behind confident prose.
