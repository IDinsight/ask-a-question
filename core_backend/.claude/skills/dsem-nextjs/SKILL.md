---
name: dsem-nextjs
description: >
  Use when creating, reviewing, or refactoring a Next.js application — App Router
  routes, file conventions, server/client component boundaries, data fetching,
  Server Actions, shadcn/ui components, and frontend tests. Operates across two
  controls: mode (review or implement) and target level (1–5, from UI spike to
  public production). Triggered explicitly via `/dsem nextjs <prompt>`.
  When triggered, first read `.agents/skills/planner/SKILL.md`.
---

# Next.js Skill

This skill applies to Next.js App Router projects. It is framework-specific — routing, file conventions, and server/client boundaries are defined here. The planner skill handles task sequencing and cross-skill routing.

This skill operates on two independent controls: **operating mode** (review or implement) and **target level** (1–5). Confirm both before doing any work.

## Invocation

Triggered by `/dsem nextjs <prompt>` or when the planner routes Next.js work here.

- **Mode** is inferred from the prompt: _build, add, implement, create, scaffold_ → implement; _review, audit, assess, check_ → review.
- **Target level** (1–5) is confirmed before work begins.

## Planner Prerequisite

Before applying this skill, read `.agents/skills/planner/SKILL.md` and run the planner pass first.

If the planner routes part of the work to another skill, load that skill before editing files in that area.

## Level Clarification Prerequisite

For **reviews**: identify and report the current level. For **implementation**: confirm the target level before starting. Do not implement above the selected level.

Levels are **paired with `api-setup` and `api-skill`** — a Level 3 API warrants a Level 3 Next.js app. When an API skill level is known, default to the same level here unless the user specifies otherwise.

**Level 1 — UI spike.** Route renders. Mock or static data only. No real auth or backend dependency. Primary interaction works. Smoke tests only. Goal: validate routing, layout, and interaction concept as fast as possible. Label as a disposable prototype not suitable for shared use.
_Pairs with: Level 1 API spike._

**Level 2 — Connected prototype.** Real backend via typed API functions, basic auth integration. All states: loading, empty, error, not-found. Happy-path Server Action with `revalidatePath`. One Playwright E2E test. Goal: validate the primary user workflow with real data. Suitable for demos and early product validation.
_Pairs with: Level 2 database-backed prototype._

**Level 3 — Internally testable UI (sweet spot).** Full server/client API split with `server-only` guard. Auth check in every Server Action. `proxy.ts` for cross-cutting redirects if needed. All state variants including `forbidden.tsx` and `unauthorized.tsx` where auth requires them. Vitest for components; Playwright for critical flows. CI: lint, type-check, tests, production build. Keyboard navigation verified for primary flows. Setup and architecture documented. Goal: maintainable UI suitable for internal testing. Most projects should target this level.
_Pairs with: Level 3 internally testable service._

**Level 4 — Operationally mature pre-production UI.** Feature modules (`features/[feature]/`) when complexity warrants them. Performance budgets and bundle analysis. `instrumentation.ts` / `instrumentation-client.ts` for observability. Client error tracking with source maps. Accessibility audit (automated + manual keyboard + screen-reader for critical flows). Staging deployment reproducible. Goal: ready for staging and controlled external user testing.
_Pairs with: Level 4 pre-production API._

**Level 5 — Public production UI.** Builds on Level 4. Adds: measurable Core Web Vitals objectives with field data, synthetic journey monitoring, privacy-safe analytics and consent management, frontend security review (CSP, CORS, session expiry, sensitive data masking), defined browser support policy, SLIs/SLOs, operational runbooks, and SEO where the app is public-facing.
_Pairs with: Level 5 public production API._

## Operating Mode

### Review mode

Use when the user asks to assess, audit, evaluate, or recommend improvements.

1. Inspect the project structure, component files, API access patterns, mutations, and tests.
2. Do not create or modify files.
3. Determine current maturity across: routing structure, data fetching, mutation strategy, state handling, security controls, testing coverage.
4. Compare against the target level.
5. Report: inferred current level, evidence, gaps, prioritised path to target level, and what is optional vs. necessary.

Do not assign a level based on folder names alone. Require evidence that the relevant behavior works.

### Implement mode

Use when the user asks to create, scaffold, add, or upgrade a Next.js project or feature.

1. Determine whether this is a new project or an upgrade of an existing one.
2. For an existing project: infer the current level first.
3. Confirm only blocking questions before implementation.
4. Preserve established project conventions when they are technically sound.
5. Implement no more than the selected target level.
6. Verify each gate before continuing.
7. Report all changes, unresolved blockers, and intentionally deferred higher-level capabilities.

## Pre-flight

Confirm the following in a single message before doing anything.

**Always required:** operating mode, target level.

**Implement mode only:** whether this is a new project or an existing one being upgraded.

Present a summary and wait for explicit confirmation.

## File Conventions

### Route-segment convention files

Any of these files are valid inside `app/[feature]/`:

| File               | Purpose                                                                      |
| ------------------ | ---------------------------------------------------------------------------- |
| `page.tsx`         | Public route UI                                                              |
| `layout.tsx`       | Shared UI wrapper for the segment and its children                           |
| `loading.tsx`      | Suspense fallback; wraps `page.tsx` in a `<Suspense>` boundary automatically |
| `error.tsx`        | Error boundary UI for recoverable errors; must be a Client Component         |
| `global-error.tsx` | Root-level error boundary; wraps the root `layout.tsx`                       |
| `not-found.tsx`    | UI rendered when `notFound()` is called                                      |
| `forbidden.tsx`    | UI rendered when `forbidden()` is called (403)                               |
| `unauthorized.tsx` | UI rendered when `unauthorized()` is called (401, experimental v15.1+)       |
| `template.tsx`     | Re-rendered layout; creates a new instance on every navigation               |
| `default.tsx`      | Fallback page for parallel route slots                                       |
| `route.ts`         | API endpoint (Route Handler)                                                 |

### Routing organization conventions

| Convention                               | Effect                                                                                   |
| ---------------------------------------- | ---------------------------------------------------------------------------------------- |
| `[segment]`                              | Dynamic route param                                                                      |
| `[...segment]` / `[[...segment]]`        | Catch-all / optional catch-all                                                           |
| `(group)`                                | Route group — organizes segments without affecting the URL                               |
| `_folder`                                | Private folder — opted out of routing; safe for colocating non-route files inside `app/` |
| `@slot`                                  | Parallel route named slot                                                                |
| `(.)folder`, `(..)folder`, `(...)folder` | Intercepting routes for modal patterns                                                   |

### Top-level files

| File                                    | Purpose                                                                                                                                                                                                    |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `proxy.ts`                              | Request proxy — replaces the deprecated `middleware.ts` (v16+). Used for auth redirects, rewrites, and header manipulation before routes render. Migrate: `npx @next/codemod@canary middleware-to-proxy .` |
| `instrumentation.ts`                    | Server-side OpenTelemetry and monitoring setup (Level 4+)                                                                                                                                                  |
| `instrumentation-client.ts`             | Client-side monitoring and Web Vitals reporting (Level 4+)                                                                                                                                                 |
| `next.config.js`                        | Framework configuration                                                                                                                                                                                    |
| `.env`, `.env.local`, `.env.production` | Environment variables                                                                                                                                                                                      |

### Structural guidelines

- Prefer placing feature implementation outside `app/` to keep route segments focused.
- Deliberate colocation inside `app/[feature]/` is allowed — a route is only publicly accessible when `page.tsx` or `route.ts` exists. Use `_folder` prefix for non-route files colocated inside `app/`.
- Use `(group)` to share layouts or organize sections without changing URLs.
- `proxy.ts` runs before routes render. Auth checks in `proxy.ts` are not a substitute for auth inside Server Actions — Server Functions are invokable as direct POST requests.

The default layout for a feature at Level 2–3:

```text
app/
  [feature]/
    page.tsx          # thin async Server Component
    loading.tsx       # route-level Suspense fallback
    error.tsx         # route-level error boundary
    not-found.tsx     # 404 boundary

components/
  ui/                 # shadcn primitives only
  [feature]/          # feature wrappers and child components

lib/
  api/
    server.ts         # server-only data access (Level 3+)
    client.ts         # browser-safe data access
  actions.ts          # Server Actions

proxy.ts              # cross-cutting redirects/rewrites (if needed)
```

## App Route Files

`app/[feature]/page.tsx` should stay small. Prefer it as an async Server Component.

Responsibilities:

- Define route-level metadata when needed.
- Fetch initial data for the route (server-side, Level 2+).
- Render the feature wrapper from `components/[feature]/`.
- Avoid business logic and large JSX trees.

Example (Level 2+):

```tsx
import { listHouseholds } from "@/lib/api/server";
import { HouseholdsPage } from "@/components/households/households-page";

export default async function Page() {
  const households = await listHouseholds();
  return <HouseholdsPage initialHouseholds={households} />;
}
```

`app/[feature]/layout.tsx` is optional. Use it for nested route chrome, metadata boundaries, or shared feature-level layout. Do not use it as a general component folder substitute.

## Feature Components

Use `components/[feature]/` (Level 1–3) or `features/[feature]/components/` (Level 4+ when complexity warrants) for feature UI:

```text
components/households/
  households-page.tsx       # client wrapper or main feature composition
  households-table.tsx      # presentational child component
  household-filters.tsx
  household-form.tsx
  households-empty-state.tsx
```

Rules:

- Use a feature wrapper when a screen needs client state, effects, mutations, filtering, or event coordination.
- Add `"use client"` only to components that use hooks, browser APIs, or client-side events.
- Keep child components presentational: receive data and callbacks through props.
- Keep shared primitives in `components/ui/`; keep domain-specific components in `components/[feature]/`.
- Import shadcn components from `@/components/ui/...`, not by copying their internals.

## Data Access

### Server — `lib/api/server.ts` (Level 3+)

```ts
import "server-only";
```

- Start every server API file with `import 'server-only'` — this hard-fails at build time if the file is ever imported on the client.
- Safe to use: private env vars, ORM clients, `cookies()`, `headers()`, privileged credentials.
- Call from Server Components (preferred) or Server Actions.

### Client — `lib/api/client.ts`

- Only `NEXT_PUBLIC_` env vars for the base URL. No server secrets.
- Use SWR or React Query for client-side fetching — not bare `useEffect` + `useState`.
- Raw `useEffect` fetching has no deduplication, stale-data handling, or built-in cache. Use it only as a last resort and document why.

### Level 1 (spike only)

A single `lib/api.ts` is acceptable at Level 1 where the distinction between server and browser execution is not yet relevant.

## Mutations

- Use Server Actions (`'use server'`) for create, update, and delete operations.
- Every Server Action must verify authentication and authorization before operating on data. `proxy.ts` checks alone are insufficient.
- Use `useActionState` for pending state and validation errors in client-facing forms.
- Use `useOptimistic` only when the latency justifies the complexity.
- Call `revalidatePath('/route')` or `revalidateTag('tag')` after each mutation to update the cache.
- Keep action files in `lib/actions.ts` or `lib/actions/` — not colocated inside route files.

Example:

```ts
// lib/actions.ts
"use server";
import { auth } from "@/lib/auth";
import { revalidatePath } from "next/cache";

export async function createHousehold(formData: FormData) {
  const session = await auth();
  if (!session?.user) throw new Error("Unauthorized");

  // mutate data ...
  revalidatePath("/households");
}
```

## State Handling

Every data-driven feature must handle all relevant states. Never leave a loading path as a blank screen.

| State               | Convention                                                                               |
| ------------------- | ---------------------------------------------------------------------------------------- |
| Loading             | `loading.tsx` for full route; `<Suspense fallback={<Skeleton />}>` for partial streaming |
| Empty               | Empty-state component in `components/[feature]/` — never a silent blank                  |
| Error (recoverable) | `error.tsx` with a reset button; must be a Client Component                              |
| Not found           | `not-found.tsx` + `notFound()` called from Server Components                             |
| Forbidden           | `forbidden.tsx` + `forbidden()` (Level 3+ where auth is present)                         |
| Unauthorized        | `unauthorized.tsx` + `unauthorized()` (experimental, Level 3+)                           |

## Security

- Auth check inside every Server Action — `proxy.ts` is not a substitute.
- Use `import 'server-only'` to prevent server modules from entering client bundles (Level 3+).
- Never put secrets or PII in `NEXT_PUBLIC_` env vars — they are included in the client bundle.
- Verify `proxy.ts` matcher coverage after any Server Action refactor — moving a Server Function to a different route can silently remove proxy coverage.

## shadcn and UI

- Treat `components/ui/` as the shadcn-owned primitive layer.
- Do not put feature-specific behavior or domain vocabulary in `components/ui/`.
- Compose feature-specific wrappers around shadcn primitives in `components/[feature]/`.
- Keep design tokens and Tailwind classes consistent with the existing project conventions.

## Testing

**Tooling split:**

- **Vitest + React Testing Library:** synchronous Server Components, Client Components, utility functions, `lib/api/client.ts`, Server Action business logic in isolation.
- **Playwright:** async Server Components, full route rendering with real data, critical mutations. Next.js docs explicitly state that Vitest and Jest do not support `async` Server Components.
- **`unstable_doesProxyMatch`** (experimental, v15.1+): unit-test `proxy.ts` matcher logic.

Read `references/testing-patterns.md` for patterns and examples.

## Step Routing by Level

Implement only steps at or below the target level. Defer the rest and list them in the handoff.

| Step                                                        | Min level |
| ----------------------------------------------------------- | --------- |
| Thin `page.tsx` + feature wrapper                           | 1         |
| Mock / static data                                          | 1         |
| Smoke tests (route renders, primary action works)           | 1         |
| Real backend, typed API functions                           | 2         |
| Basic auth integration                                      | 2         |
| Loading, empty, error, not-found states                     | 2         |
| Happy-path Server Action + `revalidatePath`                 | 2         |
| `useActionState` for pending state and validation errors    | 2         |
| One happy-path Playwright E2E test                          | 2         |
| Server/client API split + `server-only` guard               | 3         |
| Auth check in every Server Action                           | 3         |
| `proxy.ts` for cross-cutting redirects (if needed)          | 3         |
| `forbidden.tsx` / `unauthorized.tsx` (if auth is present)   | 3         |
| Vitest unit + integration tests                             | 3         |
| Playwright for all critical user flows                      | 3         |
| CI: lint, type-check, tests, production build               | 3         |
| Keyboard navigation verified for primary flows              | 3         |
| Setup and architecture documented                           | 3         |
| Feature modules (`features/[feature]/`) when warranted      | 4         |
| Performance budget + bundle analysis                        | 4         |
| `instrumentation.ts` / `instrumentation-client.ts`          | 4         |
| Client error tracking + source maps                         | 4         |
| Accessibility audit (automated + keyboard + screen-reader)  | 4         |
| Staging deployment reproducible                             | 4         |
| Core Web Vitals with field data, synthetic monitoring       | 5         |
| Privacy analytics + consent management                      | 5         |
| Frontend security review (CSP, CORS, session, data masking) | 5         |
| SLIs/SLOs, operational runbooks, release dashboard          | 5         |
| SEO metadata, sitemap, robots (public apps only)            | 5         |

## Review Checklist (review mode)

For each dimension, determine current maturity and compare to the target level.

**Routing and structure:** Are the correct convention files present for this level? Is `middleware.ts` migrated to `proxy.ts`? Are private folders used for colocated non-route files?

**Data fetching:** Is async Server Component fetching used as the primary pattern (Level 2+)? Is the server/client API split present and guarded with `server-only` (Level 3+)?

**Mutations:** Do Server Actions verify auth before operating? Is `revalidatePath` or `revalidateTag` called after mutations? Is pending state surfaced in the UI?

**State handling:** Are all required states handled for the level? (loading, empty, error, not-found at L2+; forbidden/unauthorized at L3+ where auth is present)

**Security:** Is `server-only` guarding server API modules (L3+)? Are `NEXT_PUBLIC_` vars free of secrets? Has `proxy.ts` matcher coverage been verified?

**Testing:** Is the Vitest/Playwright split applied correctly? Are async Server Components tested via Playwright, not Vitest?

**Performance and observability:** Are `instrumentation.ts` and `instrumentation-client.ts` present (L4+)?

**Accessibility:** Are primary interactive elements accessible? Does keyboard navigation work for primary flows (L3+)?

## Verification Gates

Run the gate for the target level before reporting done.

**Level 1:** Dev server starts. Target route renders. Primary interaction works. No production-readiness claim is made.

**Level 2:** Real backend data renders. Main mutation succeeds and revalidates. Loading, empty, and common error states are visible. Playwright happy-path test passes.

**Level 3:** CI passes (lint, type-check, Vitest, Playwright, production build). Server/client boundary is guarded with `server-only`. Auth check present in every Server Action. All state variants exist for any route that can fail. Keyboard navigation works for primary flows. Another engineer can run the project from documentation.

**Level 4:** Staging deployment is reproducible. Observability signals reach their destinations. Accessibility verification passes (automated + manual keyboard + screen-reader). Performance budgets pass. Critical journeys pass in supported browsers.

**Level 5:** Field Web Vitals data is being collected. Synthetic monitoring is active. Security and privacy controls have been reviewed. Operational ownership is assigned and runbooks are documented.

## Handoff (implement mode)

Summarise:

- Routes and components added or changed
- API split decisions (why a function is in server vs. client)
- Auth strategy and where it is enforced
- Any spec or design deviations and the reason
- User actions required (env vars, `proxy.ts` migration if `middleware.ts` was present, CI configuration)
- **Deferred items:** everything required at the next level that was not implemented, with a one-line note on what it adds

## Authoritative References

- [Next.js documentation](https://nextjs.org/docs)
- [Next.js — File conventions](https://nextjs.org/docs/app/api-reference/file-conventions)
- [Next.js — `proxy.ts` (replaces middleware.ts in v16+)](https://nextjs.org/docs/app/api-reference/file-conventions/proxy)
- [Next.js — Getting started with proxy](https://nextjs.org/docs/app/getting-started/proxy)
- [Next.js — `forbidden()` function](https://nextjs.org/docs/app/api-reference/functions/forbidden)
- [Next.js — `unauthorized()` function](https://nextjs.org/docs/app/api-reference/functions/unauthorized)
- [Next.js — Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components)
- [Next.js — Server Actions and Mutations](https://nextjs.org/docs/app/guides/server-actions)
- [Next.js — Mutating Data](https://nextjs.org/docs/app/getting-started/mutating-data)
- [Next.js — Authentication guide](https://nextjs.org/docs/app/guides/authentication)
- [Next.js — Data Security](https://nextjs.org/docs/app/guides/data-security)
- [Next.js — Content Security Policy](https://nextjs.org/docs/app/guides/content-security-policy)
- [Next.js — Environment Variables](https://nextjs.org/docs/app/guides/environment-variables)
- [Next.js — Testing with Vitest](https://nextjs.org/docs/app/guides/testing/vitest) — documents that Vitest does not support async Server Components
- [Next.js — Testing with Playwright](https://nextjs.org/docs/app/guides/testing/playwright)
- [React `useActionState`](https://react.dev/reference/react/useActionState)
- [`server-only` npm package](https://www.npmjs.com/package/server-only) — build-time guard against server code in client bundles
- [shadcn/ui documentation](https://ui.shadcn.com/docs)
- [Vitest documentation](https://vitest.dev/)
- [Playwright documentation](https://playwright.dev/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
