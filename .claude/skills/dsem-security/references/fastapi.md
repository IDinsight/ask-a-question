# FastAPI Security Reference

Use this reference to audit or implement security in FastAPI and its Starlette runtime. Apply every applicable control up to the selected shared target level. Verify deployed proxy, gateway, identity-provider, and cloud controls as well as Python code.

## Contents

- Inspection map
- Current FastAPI authentication baseline
- OWASP Top 10:2025 FastAPI coverage
- Shared Level 1-5 controls
- Common FastAPI failure patterns
- Verification guide
- Authoritative references

## Inspection Map

Inspect the actual repository equivalents of:

- App creation, middleware, exception handlers, lifespan hooks, mounted apps, and OpenAPI/docs configuration.
- Every router and alternate entry point, including WebSockets, callbacks/webhooks, background jobs, admin routes, and health/debug endpoints.
- `Depends`, `Security`, authentication dependencies, permission policies, and data-access filters.
- Password, API-key, OAuth/OIDC, session, JWT, refresh, revocation, and recovery code.
- Pydantic request/response models, file uploads, serializers, and database queries.
- Settings, secret loading, logging/redaction, CORS, trusted hosts, proxy headers, TLS termination, containers, and gateways.
- Python dependency manifests and lockfiles, CI security checks, tests, migrations, and runbooks.

Search for bypasses: routers missing the protected dependency, direct service calls without authorization context, raw SQL or shell execution, unsafe deserialization, user-controlled URLs or filenames, wildcard CORS, token decoding options, debug mode, default secrets, and sensitive response fields.

## Current FastAPI Authentication Baseline

Treat official FastAPI security guides as living documentation and re-check them before implementing or modernizing authentication.

- Use `pwdlib[argon2]` and `PasswordHash.recommended()` for new password hashing. Store new passwords with Argon2; do not select `passlib`/bcrypt as the default for new work merely because an older example used it.
- Inventory existing password-hash schemes before migration. When bcrypt is retained, install `pwdlib[argon2,bcrypt]`, configure Argon2 as current and bcrypt as fallback, use `verify_and_update()`, persist replacement hashes atomically, test mixed-hash accounts, and remove fallback only after migration evidence.
- Use `PyJWT` for new FastAPI JWT encoding and decoding, matching the current official tutorial. Install `pyjwt[crypto]` when RSA or ECDSA algorithms are required.
- Treat existing `python-jose` usage as a software-supply-chain review signal. Check version, advisories, transitive dependencies, algorithm behavior, and migration compatibility before changing it.
- Keep JWT optional. Opaque sessions or an external OIDC provider can be a better fit when immediate revocation, browser sessions, or centralized identity matters.
- For browser clients, list trusted CORS origins exactly. Never use `allow_origins=["*"]` with credentials; restrict methods and headers to what the client needs and test deployed response headers.

## OWASP Top 10:2025 FastAPI Coverage

Use this map to ensure a FastAPI review covers every OWASP Top 10:2025 category. This table is an index, not a substitute for evidence.

| Category | FastAPI evidence to inspect |
| -------- | --------------------------- |
| **A01 Broken Access Control** | Router/dependency coverage, function/object/tenant policy, CORS/CSRF, paths, redirects, SSRF, and denial tests. |
| **A02 Security Misconfiguration** | App/proxy/cloud settings, debug/docs/metrics exposure, trusted hosts, headers, permissions, defaults, error configuration. |
| **A03 Software Supply Chain Failures** | Python and image lockfiles, direct/transitive inventory, supported versions, SCA/patch process, registry trust, CI identities, SBOM/provenance. |
| **A04 Cryptographic Failures** | TLS, password hashing, random/token generation, JWT/session keys, algorithms, key storage/rotation, sensitive-data encryption and retention. |
| **A05 Injection** | Pydantic boundaries plus SQL/NoSQL, shell, template, path, header, log, parser/deserializer, and ORM query construction. |
| **A06 Insecure Design** | Trust boundaries, business invariants, tenant model, upload/outbound-request design, quotas, failure states, abuse cases, threat model. |
| **A07 Authentication Failures** | Login/recovery/MFA, enumeration and automation controls, JWT/OAuth validation, rotation, revocation, logout, audience/scope. |
| **A08 Software or Data Integrity Failures** | Mass assignment, unsafe deserialization, webhook/callback signatures and replay, artifact/update integrity, CI/CD trust and promotion. |
| **A09 Security Logging and Alerting Failures** | Auth, access-control, validation, admin, data, and error events; redaction/encoding; monitoring, alert ownership, retention, tamper resistance. |
| **A10 Mishandling of Exceptional Conditions** | Local/global handlers, safe errors, fail-closed auth/dependencies, transaction rollback, idempotency/races, cleanup, limits, repeated-error alerts. |

## Shared Level 1-5 Controls

### Level 1 — Prototype Baseline

Level 1 is for disposable spikes only.

- Use dummy secrets and dummy identities only; never connect prototype auth to production credentials or real sensitive data.
- Label mock authentication and authorization clearly in code comments or README notes.
- Validate basic request shape with Pydantic or route-level constraints.
- Return safe errors instead of tracebacks for user-triggered failures.
- Keep CORS and OpenAPI/docs exposure suitable for local/demo use only and document that it is not production-safe.
- Smoke-test that the app starts, the example route responds, invalid input is rejected, and no real credentials are committed.

### Level 2 — Real-Data Prototype Safety

Apply Level 1, then add controls for prototypes with persistence or real backend integration.

- Require authentication on every protected operation through a shared dependency.
- Enforce basic server-side authorization for function-level and object/tenant access; never trust client-supplied user, role, tenant, household, or owner IDs.
- Load secrets from environment or local development secret files excluded from version control.
- Use exact CORS origins for credentialed browser traffic.
- Define response models or DTOs that allowlist safe fields; never serialize password hashes, tokens, internal flags, or unnecessary PII.
- Use parameterized ORM/query APIs; do not interpolate untrusted input into SQL, shell, paths, templates, or dynamic imports.
- Add happy-path plus failure-path tests for missing auth, forbidden object access where relevant, validation errors, and sensitive response fields.

### Level 3 — Internally Testable Baseline Security

Apply Levels 1-2, then align with full layered architecture.

- Keep HTTP concerns in routers, business authorization in services/use cases, and query filtering in persistence/query modules as appropriate.
- Use maintained identity/session libraries or provider integrations. If the app manages passwords, use Argon2 via `pwdlib` and generic login/recovery responses where account existence is sensitive.
- If using JWT, pin an algorithm allowlist, verify signature and time claims, validate issuer/audience where tokens cross boundaries, validate a stable `sub`, and keep claims non-sensitive.
- Deny by default. Return consistent `401`, `403`, and `404` behavior.
- Prevent mass assignment by mapping explicitly permitted fields to persistence models.
- Install baseline security headers and a global safe exception handler according to the stack setup reference.
- Redact passwords, tokens, cookies, authorization headers, secret query values, and sensitive request/response bodies from logs.
- Add negative tests for protected routes, cross-object/tenant access, malicious or oversized input where relevant, and response-field leakage.
- Run available test, lint, type, dependency, and secret checks in CI or document missing checks.

### Level 4 — Pre-Production Hardening

Apply Levels 1-3, then add operational controls.

- Use short-lived access credentials and a defined renewal mechanism. Rotate refresh tokens on use when applicable, detect reuse where supported, and revoke on logout/reuse.
- Require MFA for administrative or materially privileged accounts.
- Rate-limit and monitor login, OTP, password recovery, registration, token refresh, uploads, searches, exports, webhooks, and expensive endpoints by appropriate dimensions.
- Enforce request/body/upload limits, pagination caps, query complexity bounds, timeouts, concurrency limits, and queue limits at the earliest reliable layer.
- Use least-privilege database identities and separate migration/admin credentials from runtime credentials.
- Emit structured audit events for login, renewal, logout, credential changes, permission changes, denials, exports, sensitive reads, admin actions, and security configuration changes.
- Alert on credential stuffing, token reuse, repeated authorization denials, high-volume enumeration, unexpected admin actions, and audit-pipeline failure.
- Harden container/runtime posture: non-root user, minimal image, dropped capabilities, resource limits, patched base images.
- Document staging deployment, migration/rollback, key/session rotation, dependency patching, backup/restore, and incident-response procedures.

### Level 5 — Public Production Security

Apply Levels 1-4, then verify production readiness.

- Maintain a versioned threat model and abuse cases for identity, authorization, tenants, supply chain, insiders, availability, uploads, outbound requests, and recovery.
- Trace high-assurance requirements to OWASP ASVS where appropriate and cite versioned identifiers.
- Prefer a hardened OIDC identity provider and phishing-resistant MFA for privileged or high-risk access.
- Centralize deny-by-default authorization policy with subject, action, resource, tenant, and context. Continuously test policy and tenant isolation.
- Protect keys through a secrets manager or KMS/HSM-backed service with rotation, access logging, separation of duties, and tested recovery.
- Generate an SBOM, verify provenance/signatures for critical artifacts, protect build/release identities, pin deployment inputs, and enforce separation of duties for production release.
- Send tamper-resistant security audit records to a separately controlled monitoring/SIEM system with staffed escalation and tested detections.
- Exercise playbooks for credential/key compromise, tenant breach, malicious upload, data exfiltration, dependency compromise, denial of service, and audit loss.
- Prove session/key revocation, backup restoration, recovery objectives, rollback, and forensic preservation.

Level 5 cannot be established solely through code review. Missing runtime, identity-provider, gateway, cloud, SIEM, incident exercise, or independent-test evidence must remain `unverified`.

## Common FastAPI Failure Patterns

- A router has `Depends(get_current_user)` but never verifies access to the requested object or tenant.
- A shared dependency is omitted from one router, mounted sub-application, WebSocket, webhook, or admin endpoint.
- JWT validation disables signature or expiry verification, accepts an algorithm from the token, omits audience/issuer boundaries, or uses a checked-in/default HMAC secret.
- New password hashes still use a legacy bcrypt/passlib default without a migration plan.
- `python-jose` remains in active JWT code without a current maintenance/advisory review.
- Long-lived bearer tokens have no rotation, revocation, reuse detection, or incident response path.
- Cookie authentication is added without CSRF protection, or permissive CORS is mistaken for CSRF/authentication protection.
- Pydantic validates syntax, but authorization-relevant IDs, query cost, file size, or domain invariants remain unconstrained.
- ORM objects expose hashes, internal flags, tenant IDs, tokens, or private fields.
- User input reaches raw SQL, `subprocess`, archive extraction, filesystem paths, templates, pickle/YAML loaders, or outbound URLs unsafely.
- Logs, APM spans, error trackers, or audit payloads capture authorization headers, cookies, bodies, or presigned URLs.
- Broad exception handling suppresses an authorization, persistence, or dependency failure and continues.

## Verification Guide

At minimum, add or run tests appropriate to the target level for:

- Missing, malformed, expired, wrong-issuer/audience, revoked, and reused credentials.
- Argon2 password hashes, mixed legacy-hash login, and rehash-on-login when passwords are in scope.
- `401` versus `403` behavior and every role/action combination.
- Horizontal and vertical access attempts across users, objects, households/tenants, and admin boundaries.
- Mass assignment and response-field leakage.
- SQL/command/path/template injection inputs and malformed parser inputs where applicable.
- CORS preflight and actual responses; CSRF rejection for cookie-authenticated mutations.
- Rate-limit boundaries, oversized requests/files, pagination/query caps, timeouts, and dependency failure.
- SSRF attempts against loopback, private/link-local, metadata, redirects, IPv6, and alternate address encodings where outbound fetch exists.
- Secret/log redaction and audit-event content.
- Transaction rollback, idempotency/concurrency, cleanup, fail-closed identity/policy outages, exhausted resources, and repeated exceptional conditions.
- Production startup with missing/default secrets and unsafe debug/proxy configuration.

Use focused unit tests for policies and validators, integration tests for dependency wiring and persistence, and deployment/runtime tests for proxies, TLS, limits, headers, and network boundaries.

## Authoritative References

- [FastAPI security tutorial](https://fastapi.tiangolo.com/tutorial/security/)
- [FastAPI OAuth2, password hashing, and JWT example](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [FastAPI CORS guidance](https://fastapi.tiangolo.com/tutorial/cors/)
- [`pwdlib` password migration guide](https://frankie567.github.io/pwdlib/guide/)
- [`PyJWT` documentation](https://pyjwt.readthedocs.io/)
- [Starlette middleware](https://www.starlette.io/middleware/)
- [OWASP Top 10 — 2025 introduction](https://owasp.org/Top10/2025/0x00_2025-Introduction/)
- [OWASP API Security Top 10 — 2023](https://owasp.org/API-Security/editions/2023/en/0x11-t10/)
- [OWASP Application Security Verification Standard](https://owasp.org/www-project-application-security-verification-standard/)
- [OWASP REST Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html)
- [OWASP JSON Web Token Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_Cheat_Sheet.html)
- [OWASP Server-Side Request Forgery Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
