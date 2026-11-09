---
name: dsem-planner
description: Use first before any other local skill or implementation work. Trigger whenever any `.agents/skills/*` skill would be used, when the user invokes `/dsem` with any skill name, or when the user provides a user story, acceptance criteria, product requirement, bug report, implementation plan, feature request, review request, or cross-stack task. Analyze the request, confirm operating mode and target level, classify affected layers, route to stack skills, and produce the level-aware planning context the called skill must follow.
---

# Planner Orchestrator Skill

Use this skill first. When another skill in `.agents/skills/` is triggered, read this planner before executing that skill's procedural steps and use the planner's output to choose mode, level, scope, sequence, references, tests, and additional skills.

This skill does not provide stack-specific implementation details directly. It analyzes the requirement, identifies gaps, determines affected layers, aligns all workstreams to the selected project maturity level, routes each workstream to the appropriate stack skill, and produces handoff-ready implementation or review tasks.

For simple, single-layer requests, keep the planning pass lightweight and proceed with the called skill. For user stories, acceptance criteria, product requirements, bug reports, implementation plans, cross-stack work, reviews, or requests that explicitly ask for a plan, produce a concrete multi-step planning output.

## Invocation

This skill is triggered in one of three ways:

1. **Explicit:** The user types `/dsem <skill> <prompt>` — the planner runs first, then routes to the named skill.
2. **Implicit:** The user's prompt matches a skill description — the planner activates automatically.
3. **Direct:** The user types `/dsem planner <prompt>` — the planner runs as the primary skill.

### Mode inference from the prompt

Infer the operating mode from the user's language:

- Words like _build, add, implement, create, scaffold, refactor, change, migrate, fix, upgrade_ → **implement**
- Words like _review, audit, check, assess, inspect, evaluate, analyze, compare_ → **review**

If ambiguous, ask before proceeding.

### Review-mode discovery pass

When planning an **implement** request against an existing codebase, the planner first invokes the relevant stack skills in **review mode** to discover current state:

1. Run each affected skill's review procedure (read-only) to determine the current level with evidence.
2. Compare current state against the user's desired target level.
3. Identify the delta — what exists vs. what the target level requires.
4. Produce an implementation plan that only builds what's missing, respecting existing conventions.

This means a request like _"bring this API to Level 4"_ triggers a review pass first, then an implement plan for the gap.

## Primary Objective

Convert a user request, story, review request, or acceptance-criteria document into clear, sequenced, level-aware context before stack-specific work begins.

The plan must:

- Identify operating mode: `review` or `implement`.
- Identify target level: `1` through `5`.
- Use one shared target level across API, Android, Next.js, security, and documentation unless the user explicitly asks for different levels.
- Identify knowns, unknowns, blocking gaps, and safe assumptions.
- Route work to the correct stack skills and references.
- Produce tasks that can be executed or reviewed by an engineering agent.
- Produce verification tied to acceptance criteria and target level.
- Decide whether a full planning artifact is needed or a lightweight internal plan is enough.

## Operating Mode

Confirm the mode before routing when it is not obvious.

**Review mode** applies when the user asks to assess, audit, evaluate, compare, or recommend improvements. Do not mutate files. Determine the current level with evidence, compare it to the target level, and report gaps, risks, and a prioritized path.

**Implement mode** applies when the user asks to create, scaffold, configure, upgrade, fix, or modify behavior. For an existing project, infer the current level first, then implement no more than the selected target level.

## Shared Target Levels

Use these levels as the cross-stack control plane. Stack skills may define stack-specific details, but the level number must mean the same project maturity everywhere.

**Level 1 — Spike / proof of concept.** Disposable prototype. Static or in-memory data, no real persistence, no production auth, minimal smoke verification. Goal: validate routing, screens, API shape, or concept quickly.

**Level 2 — Connected prototype.** Real primary workflow with basic structure. Persistence or backend integration exists where needed, thin layers are introduced, happy-path plus at least one failure-path check. Goal: validate real data flow.

**Level 3 — Internally testable product slice.** Default sweet spot. Full layered architecture, explicit service/data boundaries, auth where product requires it, baseline security, complete states, meaningful automated tests, lint/type/build checks, and setup docs. Goal: maintainable internal testing.

**Level 4 — Operationally mature pre-production.** Builds on Level 3. Repository or formal persistence boundaries where complexity warrants, observability, structured/audit logging, abuse controls, staging readiness, migration/rollback procedures, accessibility/performance/security hardening. Goal: controlled external or staging validation.

**Level 5 — Public production.** Builds on Level 4. SLIs/SLOs, load/capacity testing, idempotency and multi-instance correctness, zero-downtime deployment/migrations, backup restoration, threat model, incident runbooks, privacy/data-retention controls, secrets-manager integration, production monitoring, and ownership.

### Cross-Stack Level Alignment

- If the user requests "Level 5", every routed skill uses Level 5 unless the user explicitly scopes a different level for a specific stack.
- If one stack level is known, default all routed stacks to the same level and record that assumption.
- Do not silently mix Level 1 API work with Level 5 Android or Next.js work. If a mismatch is intentional, document it as a compatibility or rollout constraint.
- For review mode, report both the current level and the target level for every affected stack.

## Planning Protocol

Follow this process. For lightweight passes, run the same checks but keep notes brief and do not produce the full planning output unless the user asked for a plan or the request is broad enough to benefit from one.

### 1. Parse the Request

Extract:

- Operating mode: review or implement.
- Requested or inferred target level.
- User role, desired capability, and business/user value.
- Acceptance criteria and test cases.
- Explicit tags such as UI, backend, security, audit, observability, database, mobile, web, documentation, or deployment.
- Timeline, rollout, or sequencing hints.
- External dependencies.

If the input is already structured as acceptance criteria, preserve the original criterion IDs.

### 2. Clarify Mode and Level

If mode or target level is absent:

- Infer mode from verbs and context when safe.
- Infer Level 3 for maintainable internal product work when the user asks for a normal implementation and gives no level.
- Infer Level 2 for demo/prototype work with real data.
- Infer Level 1 only when the user asks for a mockup, spike, prototype shell, or proof of concept.
- Infer Level 4 or Level 5 only when the user asks for staging, public production, public launch, compliance, incident readiness, scale, or operational maturity.

Ask only if the level changes scope, architecture, data model, security posture, rollout, or verification in a way that cannot be safely assumed.

### 3. Classify Affected Layers

Classify each requirement into one or more layers:

- Android UI, Android local storage, Android networking, Android sync, Android security.
- Next.js UI, routing, server components, client components, server actions, route handlers.
- Backend API, database, persistence layer, repository layer, background jobs.
- Authentication/session management, authorization, security defense, security audit.
- Observability, audit logging, DevOps/deployment, QA/testing, documentation.

Record the target level for each layer.

### 4. Identify Knowns and Unknowns

List explicit implementation facts such as screens, routes, API behavior, persistence, auth, security constraints, audit logging, rate limits, device binding, migration needs, deployment requirements, and test cases.

Classify unknowns:

- **Blocking** when the answer changes data model, API contract, auth/authorization, security posture, user flow, external provider, acceptance criteria, compatibility, rollout, migration, or target level.
- **Non-blocking** when implementation can proceed safely using a documented assumption.

Ask clarifying questions only for blocking unknowns. Continue with provisional assumptions where possible.

### 5. Route to Stack Skills

Route each affected layer to the appropriate skill and pass the same mode and target level.

- Android UI, navigation, state, networking, storage, sync, security, or tests:
  - `.agents/skills/android/SKILL.md`
  - `.agents/skills/android/references/testing-and-deps.md` when tests or dependencies are involved.

- FastAPI backend feature implementation:
  - `.agents/skills/api-skill/SKILL.md`
  - `.agents/skills/api-skill/references/fastapi.md`

- API setup, infrastructure, database, observability, or stack setup:
  - `.agents/skills/api-setup/SKILL.md`
  - Stack reference, database variant references for Level 2+, observability reference for Level 3+.

- Next.js UI, routing, Server Components, Client Components, Server Actions, forms, or web tests:
  - `.agents/skills/nextjs/SKILL.md`
  - `.agents/skills/nextjs/references/testing-patterns.md` when tests are involved.

- Cross-cutting security:
  - `.agents/skills/security/SKILL.md`
  - FastAPI and/or Next.js security references when those stacks are involved.

- CI/CD pipelines, GitHub Actions workflows, automated testing in CI, deployment automation, environment promotion, or pipeline troubleshooting:
  - `.agents/skills/ci-cd/SKILL.md`
  - `.agents/skills/ci-cd/references/github-actions.md` when the platform is GitHub Actions.

- Documentation, README, API docs, runbooks, planning docs, env examples, or handoff docs:
  - `.agents/skills/documentation/SKILL.md`
  - `.agents/skills/documentation/references/readme.md` when README structure is needed.

### 6. Produce Level-Aware Workstreams

Create one workstream per affected area. Each workstream must include:

- Operating mode and target level.
- Scope and acceptance criteria covered.
- Skill references to consult.
- Files or modules to inspect.
- Expected outputs appropriate to the target level.
- Tests, checks, or review evidence required at that level.
- Risks and intentionally deferred higher-level capabilities.

### 7. Produce the Sequence

Default implementation order:

1. Resolve blocking product/security/API questions.
2. Inspect existing similar flows.
3. Define or confirm API contract.
4. Define persistence/session/security model.
5. Implement backend primitives.
6. Add backend tests.
7. Implement client integration.
8. Implement UI states.
9. Add client tests.
10. Add audit/observability checks when required by level.
11. Run end-to-end verification.
12. Update documentation.

For review mode, inspect in dependency order: architecture and contracts, data/security boundaries, user-facing flows, tests, observability, deployment, and documentation.

### 8. Produce Handoff-Ready Task Cards

Each task card must include:

- Task ID and title.
- Mode and target level.
- Stack/layer.
- Acceptance criteria covered.
- Skill to consult.
- Context/files to inspect before editing or reviewing.
- Implementation or review steps.
- Tests/evidence.
- Done condition.
- Dependencies.
- Risks and deferred higher-level items.

Task cards should be small enough for an implementation or review agent to complete independently.

### 9. Produce a Verification Matrix

Map:

- Acceptance criterion.
- Workstream or task.
- Target level.
- Test/check/review evidence.
- Test type.
- Manual/automated status.
- Expected result.

Include only verification appropriate to the selected level, plus explicit deferred checks for higher levels.

### 10. Produce Final Output

When the user asks for planning output or the request is a user story, acceptance-criteria document, product requirement, bug report, implementation plan, review, or cross-stack feature, use:

# Implementation Planning Output

## Story Interpretation

## Operating Mode and Target Level

## Acceptance Criteria Map

## Affected Layers

## Blocking Questions

## Non-Blocking Assumptions

## Stack Skill Routing

## Workstreams

## Implementation or Review Sequence

## Handoff-Ready Task Cards

## Verification Matrix

## Risks and Edge Cases

## Definition of Done

## Recommended Next Agent Action

For direct implementation turns, do not stop after planning. Carry the relevant planner output into the called skill and continue with implementation.
