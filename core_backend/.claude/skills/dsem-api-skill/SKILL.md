---
name: dsem-api-skill
description: >
  Use whenever a user wants to build, add, implement, or work on a backend
  feature that creates or modifies API behavior, routes, controllers, services,
  schemas, or data access, even if they never use the words endpoint, route, or
  API. Trigger on feature-level requests such as building a named feature,
  adding CRUD for a resource, implementing a module, or working on a flow. Also
  trigger when the user shares or references an API spec document and asks to
  implement any part of it. Triggered explicitly via `/dsem api-skill <prompt>`.
  When triggered, first read `.agents/skills/planner/SKILL.md` and use its
  routing, assumptions, sequence, and verification plan before this skill's
  steps. When in doubt about whether a feature needs API support, use this skill
  and confirm expected backend behavior. Do not trigger for existing-code-only
  bug fixes, reviews, tests, or refactors that do not create or modify routes.
---

# API Skill

This skill applies to feature work on an existing API codebase. It works alongside codebases built with `api-setup` or any project that follows a layered backend architecture.

## Invocation

Triggered by `/dsem api-skill <prompt>` or when the planner routes backend feature work here.

- **Mode** is inferred from the prompt: _build, add, implement, create, change_ → implement; _review, audit, assess, check_ → review.
- **Target level** (1–5) is detected from the codebase or confirmed with the user.

## Planner Prerequisite

Before applying this skill, read `.agents/skills/planner/SKILL.md` and run the planner pass first. Use it to confirm affected layers, blocking questions, non-blocking assumptions, task order, additional skills or references, and verification expectations.

If the planner routes part of the work to another skill, load that skill before editing files in that area.

---

## Level Clarification Prerequisite

Detect the codebase level by reading the folder structure and a representative route file before starting any work. If ambiguous, confirm with the user.

**Level 1 — inline spike.** Routes, logic, and data may all live in a single file. No layer separation required. Tests are optional and smoke-only if present. Takes the least time.

**Level 2 — thin layers.** Router → service → model structure exists. Schemas are separate from models. Happy-path tests expected.

**Level 3 — full layered architecture.** Persistence layer separates query logic from services. Auth is via dependency injection. Full test suite (happy path, failure cases, auth), lint, and type checking all pass. This is the sweet spot for most production-internal work.

**Level 4 — pre-production.** Repository layer present for complex or repeated data access. Observability hooks (structured logging, request IDs) are wired into the application. Rate limiting applied where relevant.

**Level 5 — production.** Idempotency required for mutation endpoints. All changes assessed against SLOs. Full security review before merge. Takes the most time.

Testing begins at Level 2 (happy-path only). A full test suite is required from Level 3.

---

## Operating Mode

**Review mode** — read-only assessment of an existing feature against the codebase level. No file changes. Output: detected level, gaps, prioritised recommendations.

**Implement mode** — add or modify a feature conforming to the codebase's current level. Follow steps 0–8 below.

---

### Review Mode — Steps

1. **Detect level.** Inspect folder structure and a representative route to determine the codebase level.
2. **Identify scope.** Confirm which feature, route, or module is being reviewed.
3. **Assess each layer** against level expectations:
   - Router: HTTP concerns only; correct status codes; no business logic; auth dependencies wired.
   - Service: no `HTTPException`; returns domain values; business invariants enforced explicitly.
   - Persistence layer (L3+): query logic isolated from service logic in its own module.
   - Repository (L4+): present for complex/repeated queries; not a generic CRUD wrapper for every model.
   - Models vs schemas: distinct files; no sensitive fields in any response schema.
4. **Assess tests:** smoke only (L1) → happy-path (L2) → full suite with auth and edge cases (L3+).
5. **Report.** State the detected level, list gaps marked blocking or advisory, order recommendations by impact.

---

## Architecture: Separation of Concerns

Each layer has one responsibility and never does another layer's job:

- **Router / controller** — HTTP concerns: parse request, validate input, inject dependencies, apply auth, set status codes, translate service results to responses. No business rules. No direct data access.
- **Service** — business logic: rules, orchestration, authorization, invariants. Framework-agnostic; returns domain values or sentinels. Never raises `HTTPException`.
- **Persistence (Level 3+)** — query logic: ORM queries, filters, joins. Services call these; they never write queries inline.
- **Repository (Level 4+)** — formal persistence boundary. Introduce only when a service becomes cluttered with data-access code. Always ask the user before adding one.
- **Model** — the ORM entity (data structure).
- **Schema / DTO** — request and response shapes. Always separate from models; never expose sensitive model fields.

Default shape: **router → service → models/schemas**. Persistence layer adds at L3. Repository layer adds at L4, only when earned.

---

## 0. Stack Detection

Identify the stack by inspecting the project root.

| Signal                          | Stack              | Load                    |
| ------------------------------- | ------------------ | ----------------------- |
| `pyproject.toml` with `fastapi` | FastAPI + SQLModel | `references/fastapi.md` |

Load the matching reference file and follow its conventions for folder structure, naming, imports, and response patterns throughout all steps.

If the stack has no reference file, inform the user and ask whether to proceed by matching existing conventions or wait for a reference to be added.

---

## 1. Requirements

Read the API spec if one exists and extract: HTTP method, URL, path and query parameters, request/response schemas, auth requirements. For spec-driven work, read the components section to determine what belongs in the model vs the schema — sensitive fields (passwords, tokens, internal flags) belong in the model but must be excluded from response schemas.

**If no spec exists**, gather requirements conversationally. Ask only what is needed. Confirm before starting:

```
Method: POST /orders
Body: customer_id, items (list), delivery_address, status (default: pending)
Returns: 201 with created order
Auth: authenticated user required
Proceed?
```

---

## 2. Data Layer

Create the model using folder conventions from the reference file. Include all persistence fields, correct types, validation constraints, and indexes on columns used in WHERE or JOIN.

**Before running a migration**, notify the user and ask for confirmation. If the migration causes data loss (`drop_table`, `drop_column`, `drop_index`), do NOT run it automatically — provide the command and require a manual backup step first.

Seed data only if the project already has a seeding mechanism.

---

## 3. Schema Layer (Level 2+)

Create request and response schemas (Base / Create / Update / Read pattern) per the reference file.

- Response schemas never expose sensitive fields (passwords, tokens, admin flags).
- Update schemas make all fields optional (partial updates).
- Read schemas always include the primary key.

---

## 4. Tests — Write First (Level 2+)

Write tests before implementing the router and service. They should fail at this stage — that confirms they exercise the missing behaviour.

Cover at Level 3+:

- Happy path (200 GET, 201 POST, 204 DELETE)
- Validation error (422)
- Business conflict (409)
- Unauthenticated (401) and forbidden (403)
- Not found (404)
- Business edge cases (duplicates, constraint violations, ownership checks)

At Level 2, happy-path only is the minimum. **If no test suite exists**, propose setting one up before proceeding. If the user declines, skip this layer and document a manual test plan in step 8.

---

## 5. Router Layer

Routers are thin: declare the route, inject dependencies, call the service, translate results to HTTP responses.

`None` return semantics:

| Operation        | `None` means                    | HTTP response |
| ---------------- | ------------------------------- | ------------- |
| Create (POST)    | Business or uniqueness conflict | 409 Conflict  |
| Get / Update     | Not found                       | 404 Not Found |
| Delete (`False`) | Not found                       | 404 Not Found |

Paginate every list endpoint with bounded `offset`/`limit` query params. Never return an unbounded collection — including filtered endpoints (`/search`, `/findByStatus`).

Apply auth via dependency injection — never in the service. Register the new router in the application entry point after creating it. Then run the tests; they should still fail (service not implemented), confirming the router wiring is correct.

Refer to the reference file for exact route declarations, dependency names, and response conventions.

---

## 6. Service Layer

Services contain all business logic. Structure every function:

1. Validate (existence, uniqueness, permissions)
2. Perform the operation
3. Return the result or a sentinel (`None` / `False`) on failure

Rules:

- Naming: `create_X`, `get_X`, `update_X`, `delete_X`, `list_X`
- `session` (or equivalent DB context) is always the first parameter
- Never raise `HTTPException` in a service — return domain values only; the router translates failure into HTTP errors
- Enforce invariants explicitly before inserting; do not rely solely on database constraint errors
- Bulk operations use a single transaction; never loop over individual service calls that each commit
- Group parameters into a schema object when count exceeds ~3

**Repository layer (Level 4+).** Only introduce when a service is genuinely cluttered — long multi-clause queries, duplicated selects, or query logic obscuring the business rule. Do not add silently. Pause and ask the user with a short justification. Only proceed if they agree.

After implementing the service, run the full test suite. All tests should pass. Fix failures before proceeding.

---

## 7. Quality Gate (Level 3+)

Run and fix before reporting done:

```bash
uv run pytest -v
uv run ruff check .
uv run mypy app
```

Also verify:

- No unused imports or variables
- No N+1 query patterns — filter, sort, and join at the query level; use batch loads for related data
- No sensitive fields in any response schema
- Auth dependencies on all protected routes
- No hardcoded secrets or credentials in any new file

---

## 8. Handoff

Summarise:

- Files created and endpoints added
- Layer decisions made (why a repository was or was not added, why a persistence layer was introduced)
- Any spec deviations and the reason
- User actions required (manual migration, new env vars, config changes)
- **Deferred items:** anything required at the next level that was not implemented (observability hooks at L4, idempotency at L5, etc.)

If tests were skipped, include a manual test plan:

| Method | URL          | Scenario               | Expected Status |
| ------ | ------------ | ---------------------- | --------------- |
| POST   | /orders      | Valid payload          | 201             |
| POST   | /orders      | Missing required field | 422             |
| POST   | /orders      | Duplicate / conflict   | 409             |
| POST   | /orders      | Unauthenticated        | 401             |
| GET    | /orders/{id} | Valid id               | 200             |
| GET    | /orders/{id} | Unknown id             | 404             |
| DELETE | /orders/{id} | Non-admin user         | 403             |
