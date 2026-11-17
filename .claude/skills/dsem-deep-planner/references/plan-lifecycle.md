# Plan Lifecycle

## Contents

- TODO semantics
- Updating plans during implementation
- Decision recording
- Anti-patterns

## TODO semantics

Use Markdown checkboxes consistently:

```md
- [ ] not started
- [x] complete
```

Represent blocked work without falsely checking it:

```md
- [ ] **T02-04 — Configure callback validation** — BLOCKED by `Q-03`
```

Mark a checkbox complete only when its `Done when` condition is satisfied and its `Verify` evidence is recorded.

For partially completed work, keep the parent unchecked and add checked subtasks:

```md
- [ ] **T02-04 — Add session rotation**
  - [x] Schema added
  - [x] Repository methods added
  - [ ] Concurrency test passes
```

Do not use percentages as a substitute for evidence.

## Updating plans during implementation

When implementation reveals new facts:

1. update the relevant plan before or with the code change;
2. state the discovered fact;
3. describe the changed approach;
4. update affected files, tasks, dependencies, risks, tests, and target-level implications;
5. update the feature `README.md` when ordering or cross-plan contracts change;
6. update `REQUIREMENTS.md` when the fact changes acceptance criteria, target-level gates, or deferred higher-level capabilities;
7. create or update an ADR when a decision is durable, surprising, costly to reverse, and based on a real trade-off.

Do not erase the original reason. Add a concise deviation note:

```md
> **Deviation — 2026-06-21:** The planned middleware hook cannot access the
> tenant context because it is initialized later in `src/http/bootstrap.ts`.
> Authorization will instead run in `TenantGuard`. Tasks T02-03 and T02-04
> were updated accordingly.
```

## Decision recording

Use the repository's ADR practice when available. Create `DECISIONS.md` only for feature-local decisions that aid implementation coordination but do not merit durable system-wide ADRs.

```md
# Feature Decisions

## D-01 — {Decision title}

- Status: proposed | accepted | superseded
- Context:
- Decision:
- Alternatives considered:
- Consequences:
- Affects: plans/tasks/files/target level
```

Do not create ceremonial decisions for obvious or easily reversible choices.

Record an explicit decision when the team intentionally uses different levels across stacks, raises or lowers the target level, or defers a capability normally required at the selected level.

## Anti-patterns

Do not produce:

- a generic software-development checklist;
- an unfiltered repository tree;
- a single giant plan for a multi-layer feature;
- plans based only on filenames without reading relevant contents;
- tasks with no verification;
- file paths guessed from framework convention;
- architecture redesign unrelated to the feature;
- a plan that repeats the request without resolving repository context;
- a `README.md` that is only a link list;
- duplicate task ownership across plans;
- hidden assumptions;
- hidden target-level mismatches;
- premature implementation;
- “update tests” as an afterthought;
- higher-level capabilities described as implemented when they are only deferred;
- false certainty about unresolved product behavior;
- checked TODOs based on intention rather than evidence.
