# Next.js Security Reference

Use this reference to audit or implement security in a Next.js application. Prioritize App Router patterns, but inspect Pages Router and legacy API routes when present. Treat Client Components and serialized data as browser-visible, and treat Server Functions/Actions and Route Handlers as public entry points.

## Contents

- Inspection map
- Current App Router security model
- OWASP Top 10:2025 Next.js coverage
- Shared Level 1-5 controls
- Common Next.js failure patterns
- Verification guide
- Authoritative references

## Inspection Map

Inspect the actual repository equivalents of:

- `app/**/page.*`, dynamic segments such as `app/[id]`, `layout.*`, `route.*`, every exported Server Function/Action, `proxy.*` or legacy `middleware.*`, Pages Router API routes, and data-fetching functions.
- Authentication/session modules, server-side cookie writes, callbacks, logout, recovery, role/permission checks, Data Access Layer (DAL), DTOs, direct database calls, and API clients.
- Every `'use client'` and `'use server'` boundary, `server-only` guards, props passed to Client Components, React taint use/configuration, environment-variable use, generated HTML, MDX, third-party scripts, and redirects.
- `next.config.*`, response headers, CSP, image/remote patterns, rewrites, source maps, cache directives, logging/instrumentation, and deployment configuration.
- `package.json`, lockfiles, CI security checks, browser/integration tests, and incident/runbook documentation.

Search for alternate entry points and bypasses: actions without authorization or schema validation, client-only guards, layout-only checks, dynamic route IDs used without object authorization, broad Proxy/middleware match exclusions, direct database access outside the chosen boundary, raw HTML, secrets prefixed `NEXT_PUBLIC_`, browser token storage, user-controlled redirects or fetch URLs, shared caches containing personalized data, state-changing GET requests, and sensitive objects serialized to the client.

## Current App Router Security Model

- Treat every used/exported Server Function or Action as a public HTTP entry point reachable through a direct `POST`, not as a private function. Encrypted action IDs and dead-code elimination are defense in depth, not authorization.
- Require each Server Action to authenticate the current session, authorize the exact action and resource/tenant against authoritative server data, validate all client input with a server-side schema such as Zod, enforce current workflow state, and fail closed.
- For new maintainable projects, prefer one dedicated DAL for security-sensitive data access. Put `import 'server-only'` in DAL/auth/database modules, centralize authorization there, and return explicit minimal DTOs.
- Direct database queries in Server Components can be acceptable for Level 1 spikes, but increase the chance of inconsistent policy and accidental RSC/client serialization at higher levels.
- Treat React Taint as an optional tripwire when the project deliberately accepts the experimental React channel. Continue to minimize DTOs and guard server modules even when taint is enabled.
- Keep browser sessions in cookies set and deleted by trusted server code, such as an authentication library, Server Action, or Route Handler. Use `HttpOnly`, `Secure`, intentional `SameSite`, `Path`, and `Max-Age`/`Expires`. Never put bearer credentials in browser storage.
- Use Proxy only for optional optimistic redirects or coarse checks; perform secure checks near the data source.

## OWASP Top 10:2025 Next.js Coverage

Use this map to ensure a Next.js review covers every OWASP Top 10:2025 category. This table is an index, not a substitute for evidence.

| Category | Next.js evidence to inspect |
| -------- | --------------------------- |
| **A01 Broken Access Control** | DAL, Server Function/Action and Route Handler policy; object/tenant checks for dynamic route params; CSRF/CORS; paths/redirects; cache and SSRF boundaries; denial tests. |
| **A02 Security Misconfiguration** | `next.config`, environment and preview settings, cookies, CSP/headers, Proxy matchers, source maps, image/remote patterns, cloud/CDN permissions, errors. |
| **A03 Software Supply Chain Failures** | npm lockfile and transitive inventory, supported Next.js/React/Node versions, SCA/patch process, script/package registries, CI identities, SBOM/provenance. |
| **A04 Cryptographic Failures** | HTTPS/HSTS, session and OAuth keys, cookie protection, randomness, algorithms, provider certificate validation, key storage/rotation, sensitive-data caching. |
| **A05 Injection** | HTML/JS/MDX/CSS/URL sinks, SQL/NoSQL, commands, paths, headers, logs, templates, deserialization, and third-party script/data boundaries. |
| **A06 Insecure Design** | Server/client trust boundaries, business invariants, tenant/cache model, uploads, server fetches, quotas, failure states, abuse cases, threat model. |
| **A07 Authentication Failures** | Login/recovery/MFA, enumeration and automation controls, OAuth validation, session fixation/rotation/revocation, logout, audience/scope. |
| **A08 Software or Data Integrity Failures** | Client-controlled state, mass assignment, webhook signatures/replay, unsafe serialized data, third-party code/artifacts, CI/CD trust and promotion. |
| **A09 Security Logging and Alerting Failures** | Auth, access-control, validation, admin, data, CSP, and error events; redaction/encoding; monitoring, alert ownership, retention, tamper resistance. |
| **A10 Mishandling of Exceptional Conditions** | Action/handler and global error paths, fail-closed auth/downstreams, transaction rollback, stale state/races, idempotency, cleanup, limits, repeated-error alerts. |

## Shared Level 1-5 Controls

### Level 1 — Prototype Baseline

Level 1 is for disposable UI or flow spikes.

- Use mock/static data and mock auth only; do not connect to production secrets, production identity, or real sensitive data.
- Keep direct data fetching or simple local state acceptable only when the route is clearly a spike.
- Validate basic form shape for prototype interactions and render safe errors.
- Avoid `NEXT_PUBLIC_*` secrets and browser token storage even in prototypes.
- Document prototype status, mock data, missing authorization, and manual smoke checks.

### Level 2 — Real-Data Prototype Safety

Apply Level 1, then add real workflow safety.

- Use a maintained authentication library or provider integration where auth is needed.
- Set sessions from trusted server code using cookies with `HttpOnly`, `Secure`, intentional `SameSite`, `Path`, and expiry.
- Authenticate and authorize every Server Action and Route Handler that reads or mutates protected data.
- Validate all `FormData`, JSON, dynamic route params, query values, headers, and cookies on the server with a schema library such as Zod or equivalent.
- Pass explicit DTOs to Client Components; never pass full database/auth/provider objects, tokens, or internal authorization state.
- Use state-changing HTTP methods for mutations and deliberate CSRF/origin protection for cookie-authenticated mutations.
- Add a Playwright or integration check for the primary protected workflow and at least one denied path.

### Level 3 — Internally Testable Baseline Security

Apply Levels 1-2, then align with full layered architecture.

- Centralize security-sensitive data access in server-only modules or a DAL. Add `import 'server-only'` to DAL/auth/database and other sensitive modules.
- Repeat authorization close to the data source even when Proxy, layout, or UI already checked.
- Use `401` for missing/invalid authentication and `403` for insufficient permission where the app controls HTTP responses.
- Prevent mass assignment by allowlisting writable fields and rechecking current authoritative state before commit.
- Avoid shared/public caching for personalized data. Review static generation, revalidation, fetch caching, route output, streaming, and prefetching for user-data leakage.
- Return generic browser errors and avoid serializing stacks, internal endpoints, provider responses, tokens, or secrets.
- Log authentication, authorization, validation, privileged action, and unexpected-error events needed for investigation while redacting sensitive values.
- Test anonymous, forbidden, stale-session, cross-user, and cross-tenant requests at every action/handler.
- Verify client bundles, HTML, React payloads, logs, and analytics do not contain secrets or sensitive DTO fields.

### Level 4 — Pre-Production Hardening

Apply Levels 1-3, then add staging and browser hardening.

- Use short idle and absolute session lifetimes, rotation, server-side revocation, recent-auth checks, and a session-management view where appropriate.
- Require MFA for administrative and materially privileged users.
- Rate-limit and monitor login, registration, recovery, verification, Server Actions, Route Handlers, search, export, uploads, invitations, and expensive rendering/API paths.
- Deploy a Content Security Policy. Roll it out in report-only mode, remove violations, then enforce it.
- Set HSTS at the HTTPS edge after validation, `X-Content-Type-Options: nosniff`, a deliberate `Referrer-Policy`, a minimal `Permissions-Policy`, and frame protections.
- Restrict `next/image` remote patterns and any server-side fetch/proxy feature to intended schemes, hosts, ports, paths, response sizes, and redirect behavior.
- Centralize audit events for login, logout, session renewal/revocation, recovery, permission changes, denials, exports, sensitive reads, impersonation, admin actions, and security configuration changes.
- Run secret scanning, dependency/SCA scanning, static analysis, and security-focused tests in CI where available.
- Document staging deployment, rollback, key/session rotation, dependency patching, backup/restore, and incident-response procedures.

### Level 5 — Public Production Security

Apply Levels 1-4, then verify production readiness.

- Maintain a versioned threat model and abuse cases for browser compromise, identity/recovery, Server Actions, authorization, caches, tenants, third parties, supply chain, insiders, availability, and downstream APIs.
- Trace high-assurance requirements to OWASP ASVS where appropriate and cite versioned identifiers.
- Prefer a hardened identity provider and phishing-resistant MFA for privileged or high-risk access.
- Isolate administrative interfaces by origin, identity policy, session namespace, network/access gateway, and deployment where justified.
- Enforce strict CSP with supported nonces or hashes, minimize third-party code, eliminate unsafe dynamic HTML/script paths, and evaluate Trusted Types where the architecture supports it.
- Lock the origin to trusted edge/gateway traffic, authenticate service calls, restrict egress, and layer WAF, bot, adaptive rate-limit, and DDoS controls with tested degraded behavior.
- Generate an SBOM, verify provenance/signatures for critical dependencies and build artifacts, harden CI identities, pin deployment inputs, and enforce release separation of duties.
- Send tamper-resistant auth, policy, data, admin, edge, deployment, and audit-health events to a separately controlled monitoring/SIEM system.
- Exercise incident playbooks for identity/key compromise, malicious dependency or script, cross-tenant exposure, cache leak, data exfiltration, denial of service, and audit loss.
- Prove global revocation, clean rebuild, rollback, backup restoration, recovery objectives, and forensic preservation.

Level 5 cannot be established solely from a Next.js repository. Missing identity-provider, edge, cloud, CI, SIEM, incident exercise, and independent-test evidence must remain `unverified`.

## Common Next.js Failure Patterns

- A page hides controls or redirects in the client, but its Server Action or Route Handler has no authorization check.
- Proxy/middleware or a layout is the only authorization layer.
- `'use server'` is treated as access control.
- A Server Component or DAL passes a full user/database/auth object to a Client Component.
- Direct database calls are scattered across Server Components and Actions, bypassing consistent DAL authorization.
- A secret is prefixed `NEXT_PUBLIC_`, included in public env, logged during build, embedded in source maps, or returned by an action.
- JWT/access/refresh tokens live in local storage, session storage, browser-readable cookies, client state, query strings, or analytics.
- Cookie authentication lacks CSRF protection, or broad allowed origins make Server Action/Route Handler assumptions unsafe.
- A layout caches a stale role, a shared cache omits user/tenant identity, or statically generated output contains personalized data.
- `dangerouslySetInnerHTML`, user-controlled MDX/SVG, URL schemes, or third-party scripts create an XSS path.
- User-controlled redirects accept absolute or protocol-relative URLs.
- Server-side `fetch`, image optimization, webhooks, previews, or proxy routes accept arbitrary URLs and can reach internal/metadata services.
- Mutation uses GET, lacks origin/recent-auth checks, or trusts hidden form fields for user, role, price, tenant, or ownership.
- Dependencies or Next.js remain on a release with a relevant security advisory because upgrades are not owned or tested.
- An Action catches and suppresses an auth/downstream/write failure, commits partial work, retries a non-idempotent operation, trusts stale authorization, or fails open.

## Verification Guide

At minimum, add or run tests appropriate to the target level for:

- Anonymous, malformed, expired, revoked, stale-role, and logged-out sessions.
- Horizontal and vertical authorization across users, objects, tenants, Server Actions, Route Handlers, pages, and legacy API routes.
- Direct action invocation and tampered IDs, roles, prices, tenant values, redirect targets, and hidden form fields.
- Dynamic routes such as `app/[id]` exercised with another user's or tenant's valid identifier, malformed identifiers, and stale permissions.
- Client bundle, HTML, React payload, source map, error, log, and analytics leakage of secrets and sensitive DTO fields.
- DAL/DTO field allowlists and `server-only` import failures.
- CSRF and origin rejection for cookie-authenticated mutations; OAuth redirect, `state`, `nonce`, issuer, audience, and PKCE behavior where applicable.
- Stored, reflected, and DOM XSS sinks; rich HTML sanitization; CSP enforcement and production violations.
- Shared/private cache separation, authorization changes, logout, revalidation, static output, prefetch, streaming, and CDN behavior.
- Open redirects and unsafe URL schemes.
- SSRF through server fetches, images, previews, redirects, alternate IP forms, loopback/private/link-local/metadata hosts, and DNS behavior.
- Upload signature, size, filename, serving disposition, archive/parser, and scanning behavior.
- Rate-limit boundaries, enumeration resistance, session rotation/revocation, audit records, and alert signals.
- Invalid webhook signatures, stale/replayed events, unsafe serialized state, and tampered integrity-critical fields.
- Transaction rollback, duplicate/replayed mutations, concurrency/stale-state conflicts, cleanup, fail-closed identity/policy outages, exhausted resources, and repeated exceptional conditions.
- Production HTTPS, cookies, headers, origin lockdown, preview deployments, and missing/default secret startup behavior.

Use unit tests for schemas and policy, integration tests for actions/handlers and downstream APIs, browser tests for cookie/CSRF/XSS/cache behavior, and deployed checks for CSP, headers, edge controls, TLS, and origin isolation.

## Authoritative References

- [Next.js authentication guide](https://nextjs.org/docs/app/guides/authentication)
- [Next.js data security guide](https://nextjs.org/docs/app/guides/data-security)
- [Next.js React Taint configuration](https://nextjs.org/docs/app/api-reference/config/next-config-js/taint)
- [Next.js `use server` security considerations](https://nextjs.org/docs/app/api-reference/directives/use-server)
- [Next.js Content Security Policy guide](https://nextjs.org/docs/app/guides/content-security-policy)
- [Next.js environment variables guide](https://nextjs.org/docs/app/guides/environment-variables)
- [OWASP Top 10 — 2025 introduction](https://owasp.org/Top10/2025/0x00_2025-Introduction/)
- [OWASP Application Security Verification Standard](https://owasp.org/www-project-application-security-verification-standard/)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP Cross-Site Request Forgery Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP Cross Site Scripting Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [OWASP Content Security Policy Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)
- [OWASP Server-Side Request Forgery Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
