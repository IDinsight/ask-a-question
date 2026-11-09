---
name: dsem-security
description: Identify, assess, implement, review, or refactor application security controls, especially in FastAPI APIs and Next.js applications. Use for security audits, OWASP Top 10:2025 reviews, threat reviews, security posture or maturity assessments, authentication, authorization, sessions or JWTs, secrets, input handling, browser defenses, API abuse controls, sensitive data, audit logging, exceptional conditions, software supply chain, and security tests. Operates across two controls: mode (review or implement) and target level (1–5, aligned with API, Android, Next.js, and documentation). Triggered explicitly via `/dsem security <prompt>`. When triggered, first read `.agents/skills/planner/SKILL.md`.
---

# Security Engineering

Identify exploitable weaknesses, select a security target appropriate to the application's maturity and risk, and produce evidence-backed fixes or findings. Apply this skill to audits as well as implementation work.

## Invocation

Triggered by `/dsem security <prompt>` or when the planner routes security work here.

- **Mode** is inferred from the prompt: _implement, add, fix, harden, configure_ → implement; _review, audit, assess, check, evaluate, analyze_ → review.
- **Target level** (1–5) is confirmed before work begins.

## Planner Prerequisite

Read `.agents/skills/planner/SKILL.md` first. Use the planner pass to identify operating mode, target level, affected layers, assets, trust boundaries, blocking questions, assumptions, sequencing, and verification expectations. Load any stack skill selected by the planner before editing that stack.

## Level Clarification Prerequisite

This skill operates on two independent controls: **operating mode** (`review` or `implement`) and **target level** (`1`-`5`). Use the same target level as API, Android, Next.js, and documentation unless the user explicitly overrides it.

For **reviews**: identify and report the current security level with evidence. Compare it to the target level and do not mutate files.

For **implementation**: confirm the target level before starting. Implement no more than the selected target level, and list higher-level controls as deferred.

## Shared 1-5 Security Model

Treat the levels as cumulative. Level 5 includes every applicable control from Levels 1-4.

**Level 1 — Prototype baseline.** No real secrets, sensitive data, or production credentials in the app. Protected-looking flows are clearly marked mock/prototype. Basic input validation and safe error handling for spike endpoints. Goal: avoid dangerous prototype habits while validating shape.

**Level 2 — Real-data prototype safety.** Adds basic authentication/authorization for real data, environment-based secrets, exact CORS where browser credentials are used, response minimization, basic dependency hygiene, and happy/failure security checks. Goal: safely validate a primary workflow with real persistence.

**Level 3 — Internally testable baseline security.** Default for maintainable internal work. Enforces server-side auth and authorization in the correct layer, deny-by-default protected operations, safe session/token handling, secure headers, CSRF where needed, input/output allowlists, secret/log redaction, negative tests for access control, and CI security checks where available.

**Level 4 — Pre-production hardening.** Adds abuse controls, rate limits, structured audit events, security monitoring hooks, staged environment hardening, migration/rollback security considerations, least-privilege runtime/deployment posture, upload/SSRF defenses where relevant, and documented operational ownership.

**Level 5 — Public production security.** Adds threat modeling, ASVS-backed verification where appropriate, SLIs/SLOs for security-relevant flows, incident runbooks, exercised detection/response, backup/restore and disaster-recovery evidence, secrets-manager integration, privacy/data-retention controls, supply-chain provenance/SBOM, production monitoring, and independent review for high-risk systems.

These are project maturity levels, not a compliance certification. Keep security severity separate from level: a missing Level 2 authorization check can still be Critical.

## Load the Relevant Reference

- Read [references/fastapi.md](references/fastapi.md) completely for FastAPI, Starlette, Python API, or API-gateway work.
- Read [references/nextjs.md](references/nextjs.md) completely for Next.js, React Server Components, Server Functions/Actions, Route Handlers, or browser-facing work.
- Read both for end-to-end flows. Trace identity, permissions, tokens or cookies, sensitive fields, errors, and audit events across the boundary.
- Read the project's API contract before changing an authentication contract, security scheme, error response, or sensitive payload.
- Check current official docs when implementing or modernizing framework security:
  - FastAPI security: https://fastapi.tiangolo.com/tutorial/security/
  - Next.js authentication: https://nextjs.org/docs/app/guides/authentication
  - Next.js data security: https://nextjs.org/docs/app/guides/data-security
  - OWASP Top 10:2025: https://owasp.org/Top10/2025/0x00_2025-Introduction/
  - OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/

## OWASP Top 10:2025 Coverage Gate

Use OWASP Top 10:2025 as the minimum cross-stack risk-coverage baseline and OWASP ASVS for detailed high-assurance verification. The Top 10 is an awareness standard, not proof that an application is secure.

Every assessment must explicitly evaluate all ten categories. Do not silently omit a category; mark it `pass`, `fail`, `unverified`, or `not applicable` with evidence and rationale.

| Category                                       | Required review focus                                                                                                                                    |
| ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A01 Broken Access Control**                  | Deny by default; server-side function, object, tenant, CSRF, CORS, path, redirect, and SSRF boundaries; authorization tests.                             |
| **A02 Security Misconfiguration**              | Secure defaults; minimal features and privileges; safe headers, errors, cloud permissions, proxy, and framework settings.                                |
| **A03 Software Supply Chain Failures**         | Inventory and supported versions at lower levels; automated SCA, SBOM, provenance, signing, and separation of duties as level increases.                 |
| **A04 Cryptographic Failures**                 | Data classification, TLS, password hashing, approved primitives, secure randomness, key lifecycle, and crypto agility.                                   |
| **A05 Injection**                              | Context-safe APIs and parameterization for SQL/NoSQL, commands, templates, logs, headers, HTML/JS, paths, and other interpreters.                        |
| **A06 Insecure Design**                        | Explicit security requirements, trust boundaries, business invariants, abuse/resource limits, failure states, and threat modeling proportional to level. |
| **A07 Authentication Failures**                | Maintained identity/session mechanisms, credential defenses, enumeration resistance, rotation/revocation, audience/scope checks, MFA by risk.            |
| **A08 Software or Data Integrity Failures**    | Reject untrusted serialized state/code/updates, prevent mass assignment, verify webhooks/artifacts/critical data, protect CI/CD trust boundaries.        |
| **A09 Security Logging and Alerting Failures** | Safe logging at lower levels; monitored, owned, tamper-resistant evidence and exercised detections at higher levels.                                     |
| **A10 Mishandling of Exceptional Conditions**  | Validate early, fail closed, roll back partial transactions, bound resources, and test dependency, privilege, race, and recovery failures.               |

## Operating Mode

### Review mode

1. Set scope, target level, and assumptions.
2. Map the attack surface: actors, assets, entry points, trust boundaries, sessions/tokens, privileged operations, tenants, secrets, uploads, outbound requests, third parties, data stores, caches, queues, and deployment edges.
3. Inspect implementation evidence: code, config, manifests, lockfiles, infrastructure, tests, docs, and operational evidence required by the target level.
4. Assess cumulatively through the target level and complete the OWASP Top 10:2025 coverage gate.
5. Demonstrate the security consequence for each finding with file/line evidence, preconditions, plausible exploit path, asset, and impact.
6. Report current security level, target level, confidence, findings, blockers, quick wins, and roadmap.

Do not assign a level based on dependency presence or comments alone. Require working evidence.

### Implement mode

1. Confirm target level and stack references.
2. Preserve the existing architecture when it is technically sound; align with the selected stack skill.
3. Prefer maintained libraries and framework primitives.
4. Enforce validation and authorization on server entry points and close to protected data.
5. Add negative tests for every security control introduced or changed.
6. Update API contracts, env examples, runbooks, and docs through the documentation skill.
7. Verify the target-level gate and report deferred higher-level controls.

Never invent cryptography or silently weaken a control to make tests pass.

## Severity Rules

- **Critical:** Practical path to broad account, tenant, sensitive-data, signing-key, infrastructure, or privileged compromise; unauthenticated remote code execution; or catastrophic integrity/availability impact.
- **High:** Practical unauthorized access or action with significant confidentiality, integrity, or availability impact.
- **Medium:** Exploitable weakness requiring meaningful preconditions or limited impact, or substantial defense-in-depth failure.
- **Low:** Limited-impact hardening issue, information exposure, or control-quality concern.

Raise severity for low complexity, no authentication requirement, broad blast radius, sensitive data, privileged victims, or evidence of exposure. Lower it only with verified mitigating controls.

## Non-Negotiable Reasoning Rules

- Separate authentication from authorization.
- Do not prescribe JWT merely to "add security"; choose session, cookie, token, or provider architecture from revocation and client needs.
- Treat browsers, Client Components, mobile clients, request metadata, and all client-supplied identifiers as untrusted.
- Keep secrets, credentials, signing operations, and privileged provider calls server-side and out of URLs, logs, analytics, errors, and client bundles.
- Minimize sensitive inputs, storage, and outputs. Encrypt transport, apply retention rules, and fail closed when a security dependency fails.
- Treat middleware, hidden UI, CORS, security headers, API documentation settings, and obscurity as defense in depth, not primary access control.
- Do not claim "secure", "Level 5", OWASP compliance, or penetration-test coverage without evidence. Record uncertainty as `unverified`.

## Required Finding Format

For each finding provide:

- `ID and title`
- `Severity` and `required level`
- `Status`: confirmed, likely, or unverified
- `Evidence`: file and line, configuration, test, or runtime observation
- `Attack path`: precondition and concise abuse scenario
- `Impact` and affected assets/users
- `Remediation`: smallest safe fix, plus stronger option where useful
- `Verification`: negative and positive tests or operational check
- `Reference`: relevant CWE, OWASP category, framework guidance, or ASVS identifier when useful

Finish reviews with scope, target level, assessed level, assumptions, findings ordered by severity, cumulative control matrix, OWASP Top 10 coverage summary, quick wins, blockers, roadmap, verification performed, and limitations.

## Completion Gate

Before finishing implementation work, confirm that:

- Every changed entry point authenticates and authorizes as required by level.
- Object, tenant, and function-level access tests include denial cases where relevant.
- Inputs, outputs, logs, caches, analytics, and errors do not leak sensitive data.
- Session, token, cookie, CORS, CSRF, and browser behavior match the chosen architecture.
- Secrets and production settings fail closed and have no unsafe defaults at the selected level.
- Dependency, build, deployment, serialized-data, webhook, and update trust assumptions have integrity controls appropriate to the level.
- Exceptional conditions preserve authorization and transaction integrity, release resources, return safe errors, and produce actionable telemetry where required.
- Security events are observable at the target level without recording credentials or sensitive content.
- Tests, API specifications, environment examples, and developer documentation reflect final behavior.
