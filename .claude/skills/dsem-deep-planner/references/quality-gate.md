# Final Quality Gate

Before reporting that planning is complete, verify every applicable item.

## Repository Grounding

- [ ] Repository instructions were read.
- [ ] Relevant manifests and runtime entry points were inspected.
- [ ] Current execution paths were traced.
- [ ] Existing analogues and conventions were identified.
- [ ] Exact validation commands were found or explicitly reported missing.
- [ ] Every existing file named in a plan was observed.

## Mode and Level Integrity

- [ ] Operating mode is stated as `review` or `implement`.
- [ ] Target level is stated as `1`, `2`, `3`, `4`, or `5`.
- [ ] Current level is assessed for every affected stack with evidence.
- [ ] All routed workstreams use the shared target level unless an override is explicitly documented.
- [ ] No plan requires higher-level capabilities without marking them as target scope or deferred.
- [ ] Level-specific verification expectations are present.

## Plan Integrity

- [ ] Goal, non-goals, requirements, and acceptance scenarios are documented.
- [ ] Work is split into coherent plans.
- [ ] Dependencies and parallel groups are explicit.
- [ ] Every requirement maps to implementation or review work and verification.
- [ ] Every task has files, change/review action, dependencies, target-level relevance, done condition, and verification.
- [ ] Risks, security, observability, rollout, rollback, documentation, and deferred higher-level capabilities were considered.
- [ ] Unknowns are classified as blocking or non-blocking.

## Coordination Readiness

- [ ] Feature `README.md` gives the overall execution order.
- [ ] The critical path is identified.
- [ ] Cross-plan contracts have owners, compatibility rules, and target-level notes.
- [ ] Multi-agent scopes do not overlap unsafely.
- [ ] Global and per-plan TODOs use consistent checkboxes.
- [ ] Completion evidence sections exist.

## Context Usability

- [ ] A new agent can locate relevant code from the planning files.
- [ ] Current behavior and proposed behavior are clearly separated.
- [ ] Documents contain enough exact context to avoid broad rescanning.
- [ ] Irrelevant repository detail was removed.
- [ ] Links between planning files are valid.

## Completion Report

Report:

- where the package was created;
- operating mode and target level;
- current assessed level by stack;
- number and names of plans;
- recommended execution stages;
- critical path and safe parallel work;
- unresolved blockers;
- deferred higher-level capabilities;
- first ready task;
- commands used to validate repository facts.

Do not claim that the feature is implemented. State that the implementation or review program is ready.
