---
name: dsem-deep-planner
description: Deeply inspect an existing codebase and turn a large feature, review, or cross-cutting goal into an evidence-backed, dependency-aware implementation or review program. Use before creating substantial new features, changing cross-cutting behavior, coordinating multiple agents, or whenever an agent needs exact repository context, file-level guidance, staged plans, target level (1–5), and trackable TODOs without repeatedly rediscovering the codebase. Triggered explicitly via `/dsem deep-planner <prompt>`.
---

# Deep Planner

Create implementation-ready or review-ready planning artifacts for a substantial goal without implementing production behavior.

Transform a large goal such as "Create authentication" or "Review readiness for Level 5" into a grounded package of repository context, scoped plans, executable tasks, dependencies, validation steps, and an overall order of execution. Produce a repository-specific handoff, not a generic checklist.

## Invocation

Triggered by `/dsem deep-planner <prompt>` or when the planner routes a large/cross-cutting request here.

- **Mode** is inferred from the prompt: _build, implement, create, add_ → implement; _review, audit, assess, evaluate_ → review.
- **Target level** (1–5) is inferred or confirmed before planning begins.

When invoked, this skill runs the planner prerequisite, then performs deep repository inspection to ground the plan in evidence.

## Planner Prerequisite

Before applying this skill, read `.agents/skills/planner/SKILL.md` and run the planner pass first. Carry forward the operating mode, target level, affected layers, skill routing, assumptions, and verification expectations.

If the planner routes part of the work to another skill, load that skill before writing plan details for that area.

## Operating Mode and Target Level

This skill operates on two controls: **operating mode** (`review` or `implement`) and **target level** (`1`-`5`). Use the same target level across API, Android, Next.js, security, and documentation unless the user explicitly overrides it.

**Review mode** creates an evidence-backed assessment program. It maps current maturity, gaps, risks, and verification steps against the target level without mutating production code.

**Implement mode** creates an implementation program. It describes exact file operations, tasks, tests, rollout, and documentation needed to reach the selected level without writing the feature itself.

Levels are the shared project maturity ladder:

- **Level 1:** spike / proof of concept.
- **Level 2:** connected prototype.
- **Level 3:** internally testable product slice and default layered-architecture target.
- **Level 4:** operationally mature pre-production.
- **Level 5:** public production.

Every planning artifact must state the mode and target level. Any intentional level mismatch between stacks must be recorded as a compatibility or rollout decision.

## Core Principles

1. Inspect before proposing. Derive plans from the repository as it exists.
2. Prefer evidence over inference. Support important current-state claims with a file, symbol, command, configuration key, route, schema, or test.
3. Separate current state from proposed state.
4. Decompose by coherent responsibility, not by file.
5. Make prerequisites, parallel work, blockers, and the critical path explicit.
6. Give every task a checkbox and an observable verification condition.
7. Prefer exact paths. Mark paths as `CREATE`, `MODIFY`, `DELETE`, or `CANDIDATE`.
8. Preserve repository conventions unless the plan records a reason to depart from them.
9. Keep plans live by recording discoveries, decisions, deviations, completion evidence, checkbox state, and target-level changes.
10. Do not plan above the selected level except in explicitly deferred higher-level work.

## Reference Map

Load references only when the corresponding phase begins. Read each selected file completely.

- Before repository reconnaissance, read [references/reconnaissance.md](references/reconnaissance.md).
- Before writing `CURRENT-STATE.md` or `REQUIREMENTS.md`, read [references/context-and-requirements.md](references/context-and-requirements.md).
- Before decomposing work or writing any `PLAN-NN-*.md`, read [references/implementation-plans.md](references/implementation-plans.md).
- Before writing the feature `README.md`, read [references/program-control-plane.md](references/program-control-plane.md).
- When updating an existing planning package, tracking TODOs, or recording decisions, read [references/plan-lifecycle.md](references/plan-lifecycle.md).
- Before reporting completion, read and apply [references/quality-gate.md](references/quality-gate.md).

Keep all references one level deep from this file. Do not rely on a reference file to reveal another required instruction.

## Planning-Only Boundary

During deep planning:

- Read source, tests, configuration, schemas, migrations, manifests, documentation, generated API descriptions, relevant history, and current official framework docs where required by a routed skill.
- Run non-destructive discovery and validation commands when useful.
- Create or update planning documentation.
- Do not implement production behavior, refactor unrelated code, install dependencies, or create migrations that alter a live database.
- Do not mark implementation tasks complete without implementation evidence.

Resolve uncertainty with read-only inspection, existing tests, type checks, compilers, or framework introspection. When resolution requires a code change, record a spike instead of implementing it.

## Output Location

Prefer the repository's existing planning convention. Otherwise create:

```text
docs/plans/{feature-slug}/
├── README.md
├── CURRENT-STATE.md
├── REQUIREMENTS.md
├── PLAN-01-{slug}.md
├── PLAN-02-{slug}.md
└── DECISIONS.md            # only when needed
```

Do not create a competing convention when locations such as `specs/{feature}/`, `docs/features/{feature}/`, `planning/{feature}/`, or `.github/specs/{feature}/` already exist.

Always create or update `README.md`, `CURRENT-STATE.md`, and `REQUIREMENTS.md`. Create one or more plan files after decomposition. Create `DECISIONS.md` only for meaningful feature-local trade-offs that do not belong in an existing ADR system.

## Workflow

### Phase 0 — Establish the Target

Restate the requested outcome without prematurely choosing an implementation.

Capture:

- operating mode and target level;
- affected users or systems;
- observable success;
- explicit constraints and non-goals;
- assumptions that still need verification;
- fuzzy domain terms that require repository evidence or user input;
- any intentional stack-level mismatch.

When terminology matters, inspect repository glossaries, schemas, API names, UI copy, `CONTEXT.md`, and `CONTEXT-MAP.md`.

### Phase 1 — Reconnoiter the Repository

Read [references/reconnaissance.md](references/reconnaissance.md), then inspect from the outside inward:

1. repository shape, ownership, instructions, and planning conventions;
2. runtime, build, test, persistence, CI, deployment, and environment setup;
3. feature-adjacent execution paths and important symbols;
4. the nearest implemented analogue and its tests;
5. constraints, invariants, and current maturity level;
6. exact validation commands.

Record the smallest structural map that supports the feature. Do not dump the full tree or invent missing commands.

### Phase 2 — Write `CURRENT-STATE.md`

Read [references/context-and-requirements.md](references/context-and-requirements.md), then create a compact, evidence-backed stocktake of only the repository areas relevant to the feature.

Include mode, target level, observed current level by stack, inspection scope, repository map, current execution flow, existing patterns, verified constraints, validation commands, and classified gaps.

A new agent must be able to locate the relevant code and understand current behavior without broadly rescanning the repository.

### Phase 3 — Write `REQUIREMENTS.md`

Separate requested behavior from implementation choices. Define testable functional requirements, relevant quality requirements, acceptance scenarios, non-goals, compatibility or migration requirements, target-level gates, assumptions, and open questions.

Give requirements and scenarios stable IDs. Maintain a coverage table mapping each requirement to a plan and verification method as plans emerge.

### Phase 4 — Decompose the Work

Read [references/implementation-plans.md](references/implementation-plans.md), then split work at coherent responsibility, deployment, risk, review, or target-level boundaries.

Each plan must:

- deliver a meaningful, reviewable outcome;
- declare mode, target level, inputs, outputs, dependencies, and parallel safety;
- own exact file operations without unsafe overlap;
- include tests, validation, risks, security, observability, documentation, and rollout expectations appropriate to the target level;
- contain checkable tasks with observable completion evidence;
- list intentionally deferred higher-level capabilities.

Merge work that must change atomically to keep the repository buildable. Split independently deployable outcomes, distinct risky migrations, specialist workstreams, or overly broad task lists.

### Phase 5 — Write `PLAN-NN-*.md`

Number plans by dependency order, not discovery order. Apply the template and rules in [references/implementation-plans.md](references/implementation-plans.md).

For every existing path, confirm it was observed. Mark proposed paths `CREATE` and unresolved path choices `CANDIDATE`. Use contracts, pseudocode, type signatures, schema shapes, or payload examples only when they remove implementation ambiguity; do not write the feature implementation.

Every task must state files, change or review action, dependency, done condition, exact verification evidence, and target-level relevance.

### Phase 6 — Write the Feature `README.md`

Read [references/program-control-plane.md](references/program-control-plane.md), then create the control plane for the complete program.

Summarize rather than duplicate the plans. Include goal, mode, target level, current assessed level, status, planning location, reading order, plan index, dependency order, parallel groups, critical path, global TODOs, file or contract ownership, blockers, deferred higher-level work, and definition of done.

Use Mermaid only when the repository already uses it; otherwise use a text dependency graph.

### Phase 7 — Reconcile the Plan Set

Review the complete package for:

- requirement-to-plan-to-verification coverage;
- consistent target level across all workstreams or documented exceptions;
- one primary owner per file and shared-contract coordination;
- acyclic dependencies and safe parallel groups;
- coverage of every affected layer;
- executable task detail;
- current/proposed-state separation;
- context economy and valid links.

Apply [references/quality-gate.md](references/quality-gate.md). Fix failures before declaring the planning package ready.

## Level-Gated Planning Expectations

- **Level 1:** keep plans small, disposable, and explicit about mock/static/in-memory limits.
- **Level 2:** include real data/backend integration, basic setup, thin layers, and happy/failure verification.
- **Level 3:** require full layered architecture, baseline security, meaningful automated tests, CI quality checks, and developer docs.
- **Level 4:** include staging, observability, audit logging, rate limits or abuse controls, migration/rollback, and operational ownership.
- **Level 5:** include production SLOs, load/capacity, idempotency, multi-instance correctness, zero-downtime changes, backup restoration, DR, threat model, incident runbooks, privacy/retention, and production monitoring.

## Completion Response

Report:

- planning directory;
- operating mode and target level;
- assessed current level by stack;
- number and names of plans;
- recommended execution stages and critical path;
- plans that may run in parallel;
- unresolved blockers;
- deferred higher-level capabilities;
- first ready task;
- commands used to validate repository facts.

State that the implementation or review program is ready. Do not claim that the feature itself is complete.
