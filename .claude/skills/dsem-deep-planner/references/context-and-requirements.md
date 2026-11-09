# Current State and Requirements Artifacts

## Contents

- `CURRENT-STATE.md` template
- Current-state quality bar
- `REQUIREMENTS.md` template
- Requirements quality rules

## `CURRENT-STATE.md` Template

````md
# Current State: {Feature Name}

## Planning controls

- Operating mode: `review | implement`
- Target level: `1 | 2 | 3 | 4 | 5`
- Requested stack-level overrides: `none` or list
- Assessed current level by stack:
  - API:
  - Android:
  - Next.js:
  - Security:
  - Documentation:

## Scope of this inventory

{What was inspected and what was intentionally excluded.}

## Repository map

| Path | Role | Relevance | Evidence |
| ---- | ---- | --------- | -------- |
| `path/to/file` | What it does today | Why the feature touches or depends on it | observed/read/tested |

## Stack and tooling

| Concern | Current setup | Evidence |
| ------- | ------------- | -------- |
| Runtime | ... | `path` |
| Framework | ... | `path` |
| Tests | ... | `path` |
| Persistence | ... | `path` |
| CI | ... | `path` |
| Deployment | ... | `path` |

## Current execution flow

1. `path:symbol` receives ...
2. `path:symbol` calls ...
3. `path:symbol` persists ...
4. `path:test` verifies ...

## Existing patterns to preserve

### {Pattern name}

- Evidence: `path`, `path`
- Current level implication:
- How it works:
- Why it matters for this feature:

## Existing feature-adjacent behavior

{What already exists, including partial implementations.}

## Constraints and invariants

- **Verified** — ...
- **Requested** — ...
- **Proposed** — ...

## Validation commands

```sh
{exact commands found in the repository}
```

## Gaps and unknowns

| ID | Question | Why it matters | How to resolve | Blocking? | Level impact |
| -- | -------- | -------------- | -------------- | --------- | ------------ |
| U-01 | ... | ... | inspect/test/ask | yes/no | L3/L4/etc. |
````

## Current-State Quality Bar

A new agent must be able to answer:

- What kind of repository is this?
- Which application or package owns the feature?
- What operating mode and target level apply?
- What is the current assessed level for each affected stack?
- Where does execution begin?
- Which files define current behavior?
- Which existing pattern should be followed?
- Which commands prove the work?
- What remains unknown and whether it affects the target level?

If not, the inventory is incomplete. Keep current-state facts evidence-backed and separate from proposed changes.

## `REQUIREMENTS.md` Template

```md
# Requirements: {Feature Name}

## Planning controls

- Operating mode: `review | implement`
- Target level: `1 | 2 | 3 | 4 | 5`
- Shared-level assumption: {All stacks use the same target level unless listed below.}
- Stack-level overrides: `none` or list

## Goal

{One concise outcome statement.}

## Actors

- **{Actor}** — ...

## Functional requirements

- **FR-01** — ...
- **FR-02** — ...

## Quality requirements

- **QR-01 Security** — ...
- **QR-02 Reliability** — ...
- **QR-03 Performance** — ...
- **QR-04 Observability** — ...
- **QR-05 Accessibility** — ...
- **QR-06 Documentation** — ...

Include only relevant categories. Tie each quality requirement to the selected target level.

## Target-level requirements

- **L1** — Spike/prototype constraints and disclaimers.
- **L2** — Real data flow and basic setup expectations.
- **L3** — Layered architecture, tests, baseline security, CI, and docs.
- **L4** — Staging, observability, audit, abuse controls, migration/rollback.
- **L5** — Production SLOs, incident readiness, DR, privacy/retention, production monitoring.

Include only the selected level and lower levels. Add higher levels only under deferred capabilities.

## Acceptance scenarios

### AS-01 — {Scenario}

**Given** ...
**When** ...
**Then** ...

## Non-goals

- ...

## Compatibility and migration requirements

- ...

## Deferred higher-level capabilities

- ...

## Assumptions

- **A-01** — ...

## Open questions

- **Q-01** — ...

## Requirement coverage

| Requirement | Target level | Planned in | Verification |
| ----------- | ------------ | ---------- | ------------ |
| FR-01 | L3 | `PLAN-01-...md` | test or manual check |
```

## Requirements Quality Rules

- Separate desired behavior from implementation choices.
- Preserve stable IDs supplied by the source requirement; otherwise assign stable IDs.
- Include only applicable quality categories.
- Make requirements observable and testable.
- Tie every requirement to the selected target level or mark it as deferred.
- Replace phrases such as "support secure login" with explicit lifetime, failure, protection, audit, and revocation behavior when those concerns are in scope.
- Map every requirement and acceptance scenario to at least one plan and verification method.
