# Implementation Plan Design

## Contents

- Plan boundaries
- Split and merge rules
- Target-level gates
- `PLAN-NN-*.md` template
- Task quality rules
- Complete-plan consistency review

## Plan Boundaries

Create multiple plans when a goal crosses responsibilities, layers, deployment stages, target levels, risk boundaries, or review boundaries.

Useful boundaries include:

- data model and migration;
- domain or application behavior;
- API or event contracts;
- authorization and policy;
- frontend experience;
- mobile/offline/sync behavior;
- external integrations;
- observability and operations;
- migration or rollout;
- test infrastructure;
- documentation and cleanup.

Avoid one plan per file. Each plan must deliver a coherent capability, be reviewable in isolation, have clear inputs and outputs, declare dependencies, list exact files, include tests and validation, identify risk and rollback implications, and avoid overlapping ownership.

## Split and Merge Rules

Split a plan when:

- outcomes are independently deployable;
- different specialist capabilities are required;
- the work belongs to different target-level gates;
- it contains more than one risky migration;
- foundational work is mixed with user-facing behavior;
- safe parallel execution is possible after a shared prerequisite;
- the task list is too broad to understand without rescanning the repository.

Merge plans when their tasks must change atomically to keep the repository buildable or preserve a contract.

## Target-Level Gates

Apply only the selected level and lower levels. Higher-level items belong in "Deferred higher-level capabilities" unless the user explicitly raises the target.

- **Level 1:** disposable spike, static/mock/in-memory data, minimal setup, smoke/manual checks.
- **Level 2:** real data/backend integration, thin layers, env setup, happy-path plus failure-path verification.
- **Level 3:** full layered architecture, baseline security, meaningful automated tests, lint/type/build checks, CI, developer docs.
- **Level 4:** staging/deployment, observability, structured/audit logging, abuse controls, migration/rollback, accessibility/performance/security hardening.
- **Level 5:** SLIs/SLOs, load/capacity, idempotency, multi-instance correctness, zero-downtime release/migrations, backup restore, DR, threat model, privacy/retention, incident runbooks, production monitoring.

## `PLAN-NN-*.md` Template

```md
# Plan NN: {Outcome-oriented title}

## Status

`not-started | in-progress | blocked | complete`

## Planning controls

- Operating mode: `review | implement`
- Target level: `1 | 2 | 3 | 4 | 5`
- Stack/layer:
- Level alignment: {Uses shared target level / intentional override with reason}

## Outcome

{What capability exists, or what assessment is complete, when this plan is complete.}

## Why this plan exists

{How it contributes to the feature and why it is a separate unit.}

## Requirements covered

- `FR-01`
- `QR-01`
- `AS-02`

## Dependencies

### Requires

- `PLAN-00-...` or `None`

### Enables

- `PLAN-...`

### May run in parallel with

- `PLAN-...`

## Current-state anchors

| File or symbol | Current role | Current level evidence | Planned use |
| -------------- | ------------ | ---------------------- | ----------- |
| `path` | ... | ... | preserve/extend/replace |

## File operations

| Operation | Path | Planned change | Reason |
| --------- | ---- | -------------- | ------ |
| `MODIFY` | `existing/path` | ... | ... |
| `CREATE` | `new/path` | ... | ... |
| `DELETE` | `old/path` | ... | ... |
| `CANDIDATE` | `possible/path` | decision required | ... |

Every existing path must have been observed. Every new path must be marked `CREATE`.

## Implementation or review design

### 1. {Change or review area}

Describe:

- exact behavior, data flow, or review scope;
- public interfaces and relevant types or symbols;
- errors and edge cases;
- interaction with current abstractions;
- why this fits repository conventions;
- how the work satisfies the selected target level.

## Contracts and examples

Include concise pseudocode, type signatures, API examples, schema shapes, or event payloads only when they remove ambiguity. Do not write a full implementation.

## Task checklist

- [ ] **TNN-01 — {Task title}**
  - Files: `path`, `path`
  - Change or review action: ...
  - Target-level relevance: L1/L2/L3/L4/L5
  - Depends on: `TNN-00` or none
  - Done when: ...
  - Verify: `exact command`, test name, runtime observation, or review evidence

## Test and verification plan

### Unit

- ...

### Integration

- ...

### End-to-end

- ...

### Manual or operational

- ...

### Review evidence

- ...

## Failure modes and edge cases

| Case | Expected behavior | Planned coverage | Level |
| ---- | ----------------- | ---------------- | ----- |
| ... | ... | test/task | L3 |

## Security and privacy

- threat or trust-boundary implications;
- secrets and sensitive data handling;
- authorization checks;
- logging redaction;
- abuse or rate-limit considerations;
- target-level security gate.

Write `Not materially affected at the selected level` when appropriate.

## Observability

- logs, metrics, and traces;
- audit events;
- alerts or dashboards;
- correlation identifiers;
- target-level observability gate.

Write `Not required at the selected level` when appropriate.

## Documentation

- docs, specs, README, runbooks, or env examples to update;
- target-level documentation expectation;
- deferred higher-level docs.

## Rollout and rollback

- feature flag or staged rollout;
- compatibility window;
- migration ordering;
- rollback behavior;
- irreversible steps;
- target-level release gate.

Write `No special rollout required at the selected level` only when justified.

## Deferred higher-level capabilities

| Capability | Required at | Why deferred |
| ---------- | ----------- | ------------ |
| ... | L4/L5 | Target is L3 |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner plan/task |
| ---- | ---------- | ------ | ---------- | --------------- |
| ... | low/medium/high | ... | ... | ... |

## Open questions

- **Q-NN-01** — ...
  - Default if unanswered:
  - Blocks: task/plan/none
  - Level impact:

## Completion evidence

Complete this section during implementation or review:

- Pull request or commit:
- Tests run:
- Validation result:
- Review evidence:
- Deviations from plan:
- Follow-up work:
```

## Task Quality Rules

Every task must specify:

- where to work;
- what to change or review;
- which target level it satisfies;
- what it depends on;
- what completion means;
- how to verify it.

Rewrite tasks such as "implement auth" or "add tests." Use exact observed paths for current files. Mark proposed files `CREATE`, removals `DELETE`, and uncertain choices `CANDIDATE`.

## Complete-Plan Consistency Review

Verify:

- every functional, quality, compatibility, and acceptance requirement maps to a plan and verification method;
- every plan states mode and target level;
- all workstreams share the requested level or document an intentional override;
- every file has one primary owning plan;
- shared files and contracts have explicit sequencing and coordination;
- dependencies are acyclic and prerequisites precede consumers;
- parallel plans cannot mutate the same contract unsafely;
- rollout follows compatibility work;
- tests are not deferred beyond risky integration when they can be built earlier;
- selected-level security, observability, operations, documentation, and testing gates are covered;
- higher-level capabilities are deferred explicitly rather than accidentally omitted;
- irrelevant repository facts are removed.
