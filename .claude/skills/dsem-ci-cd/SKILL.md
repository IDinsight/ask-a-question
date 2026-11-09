---
name: dsem-ci-cd
description: >
  Use when creating, reviewing, modifying, or troubleshooting CI/CD pipelines,
  GitHub Actions workflows, automated testing in CI, deployment automation,
  environment promotion, branch protection, caching, secret management in
  pipelines, or any work that touches `.github/workflows/`. Also trigger when the
  user asks to "set up CI," "add a deploy step," "fix the pipeline," "add linting
  to CI," or references pipeline failures and flaky CI runs. Operates across two
  controls: mode (review or implement) and target level (1–5). Triggered
  explicitly via `/dsem ci-cd <prompt>`. When triggered, first read
  `.agents/skills/planner/SKILL.md` and use its routing, assumptions, sequence,
  and verification plan before this skill's steps.
---

# CI/CD

Build and maintain continuous integration and deployment pipelines that match the project's maturity level. This skill defines what each pipeline level must contain, then delegates stack-specific syntax and deployment mechanics to reference files.

## Invocation

Triggered by `/dsem ci-cd <prompt>` or when the planner routes CI/CD work here.

- **Mode** is inferred from the prompt: _set up, add, create, fix, configure, migrate, optimize_ → implement; _review, audit, check, assess, evaluate_ → review.
- **Target level** (1–5) is confirmed before work begins.

## Planner Prerequisite

Before applying this skill, read `.agents/skills/planner/SKILL.md` and run the planner pass first. Use it to confirm operating mode, target level, affected layers, blocking questions, assumptions, task order, additional skills or references, and verification expectations.

If the planner routes part of the work to another skill (e.g., security scanning → security skill, deployment docs → documentation skill), load that skill before editing files in that area.

---

## Level Clarification Prerequisite

This skill operates on two independent controls: **operating mode** (`review` or `implement`) and **target level** (`1`–`5`). Use the same target level as API, Android, Next.js, security, and documentation unless the user explicitly overrides it.

For **reviews**: identify and report the current CI/CD level with evidence. Compare it to the target level and do not mutate files.

For **implementation**: confirm the target level before starting. Implement no more than the selected target level, and list higher-level capabilities as deferred.

---

## Pipeline Levels — What Each Level Contains

Levels are cumulative. A Level 3 pipeline includes everything from Levels 1 and 2.

### Level 1 — Smoke CI

A single pipeline that catches obviously broken code before merge.

**Required jobs:**

| Job      | Purpose                                  |
| -------- | ---------------------------------------- |
| **Lint** | Code style and formatting checks         |
| **Test** | Run the test suite with default settings |

**Triggers:** push to default branch, pull requests targeting default branch.

No deployment. No caching. No environment variables beyond what the test suite needs. A failing pipeline blocks nothing — it's informational only.

### Level 2 — Verified Builds

The pipeline proves the artifact can be produced and enforces PR quality gates.

**Required jobs (in addition to Level 1):**

| Job            | Purpose                                    |
| -------------- | ------------------------------------------ |
| **Type check** | Static type analysis (mypy, tsc, etc.)     |
| **Build**      | Compile or bundle the application artifact |

**Pipeline requirements:**

- Dependency install caching to reduce run time.
- Basic environment configuration via repository secrets where needed.
- PR status checks enforced — PRs cannot merge without a green pipeline.
- Test coverage reported (not gated).

### Level 3 — Quality-Gated CI with Staging Deploy

Every merge to the default branch produces a tested, scanned, deployable artifact and pushes it to a staging environment.

**Required jobs (in addition to Level 2):**

| Job                          | Purpose                                                 |
| ---------------------------- | ------------------------------------------------------- |
| **Security scan**            | Dependency vulnerability audit                          |
| **Deploy to staging**        | Automated staging deployment on merge to default branch |
| **Post-deploy health check** | Verify the staging deployment is healthy                |

**Pipeline requirements:**

- Branch protection rules require all CI checks to pass.
- Code coverage threshold enforced (fail the pipeline if below threshold).
- Workflow permissions scoped to the minimum required (`permissions:` block).
- Concurrency control to cancel superseded CI runs on the same branch.
- Matrix builds where multiple runtimes or versions matter.
- Workflow files themselves are linted/validated.

### Level 4 — Operationally Mature Pipelines

The pipeline is a reliable, observable promotion system with human checkpoints before production.

**Required jobs (in addition to Level 3):**

| Job                      | Purpose                                                                |
| ------------------------ | ---------------------------------------------------------------------- |
| **Deploy to production** | Production deployment with approval gate                               |
| **Notify on failure**    | Slack/email notification when the pipeline fails on the default branch |

**Pipeline requirements:**

- Deployment approval gates for production (required reviewers).
- Environment promotion path: staging → production.
- Build artifact versioning and tagging (SHA or semantic version).
- Parallel job optimization — no unnecessary sequential bottlenecks.
- Reusable workflow extraction for patterns shared across repositories.
- Secret scanning on every push.
- SAST (static analysis security testing) on pull requests.

### Level 5 — Production-Grade Delivery

The pipeline is the production release system with full accountability and recovery.

**Required jobs (in addition to Level 4):**

| Job                        | Purpose                                                |
| -------------------------- | ------------------------------------------------------ |
| **Post-deploy smoke test** | Automated smoke test against the production deployment |
| **Rollback**               | Automated rollback when post-deploy health checks fail |

**Pipeline requirements:**

- Zero-downtime deployment orchestration.
- Pipeline audit trail (who approved, when, what SHA deployed).
- License scanning and SBOM generation on release builds.
- Infrastructure-as-code validation in the pipeline.
- Pipeline SLIs tracked: median duration, failure rate, MTTR.
- Disaster-recovery pipeline (restore from backup, deploy from known-good state).
- All third-party actions pinned to full commit SHAs.
- Dependabot or Renovate configured for automated dependency and action updates.

---

## Operating Mode

### Review mode

1. **Inventory pipelines.** List all workflow files under `.github/workflows/` (or equivalent CI config). Note triggers, jobs, steps, and target branches.
2. **Detect level.** Assess the current CI/CD level by comparing what's present against the level definitions above. Evidence-based — what's implemented, what's absent, what's configured but broken.
3. **Assess structure.** For each workflow:
   - Trigger correctness: does it run on the right events and branches?
   - Job dependencies: are jobs ordered correctly? Are there unnecessary sequential bottlenecks?
   - Caching: are dependency installs cached? Are cache keys correct (include lockfile hash)?
   - Secrets: are secrets used safely? Are any hardcoded values that should be secrets?
   - Security: is dependency auditing present? Secret scanning? SAST?
   - Deployment: does the deploy step target the right environment? Are there approval gates where needed?
   - Notifications: are failures surfaced to the team?
   - Permissions: are workflow permissions scoped minimally?
4. **Assess reliability.** Check for:
   - Flaky tests (pass locally, fail in CI).
   - Timeout issues (missing or overly generous).
   - Race conditions in parallel jobs.
   - Cache invalidation problems.
   - Version pinning gaps (unpinned actions, floating runtime versions).
5. **Report.** State the detected level, list gaps marked blocking or advisory, order recommendations by impact. Include the specific file and line for each finding.

### Implement mode

Follow steps 0–7 below.

---

## 0. Codebase Discovery and User Confirmation

Before writing any pipeline configuration, scan the codebase and confirm scope with the user.

### Detect stacks

Inspect the repository root and subdirectories for stack signals:

| Signal                                                       | Stack detected |
| ------------------------------------------------------------ | -------------- |
| `pyproject.toml` with `fastapi` or `django`                  | Python API     |
| `requirements.txt` with `fastapi` or `django`                | Python API     |
| `package.json` with `next`                                   | Next.js        |
| `build.gradle.kts` or `settings.gradle` with Android plugins | Android        |

In a monorepo, each subdirectory may contain a different stack. List all detected stacks with their paths.

### Ask the user

Present the detected stacks and ask two questions:

1. **Which stacks need a CI/CD pipeline?** List detected stacks and let the user confirm, remove, or add. For monorepos, ask whether each stack gets its own workflow or they share one.

2. **Where will this be deployed?** Present the deployment options:
   - **Railway** — most common. Web apps, APIs, background workers.
   - **Google Cloud Platform** — Cloud Run, App Engine, GKE.
   - **AWS** — ECS, Lambda, Elastic Beanstalk.
   - **No deployment yet** — CI only, no deploy step.

Do not proceed until both answers are confirmed.

### Load references

Based on the answers, load the appropriate reference files:

| Stack                       | Reference                                                                    |
| --------------------------- | ---------------------------------------------------------------------------- |
| Python API (GitHub Actions) | [references/github-actions-python.md](references/github-actions-python.md)   |
| Next.js (GitHub Actions)    | [references/github-actions-nextjs.md](references/github-actions-nextjs.md)   |
| Android (GitHub Actions)    | [references/github-actions-android.md](references/github-actions-android.md) |

| Deployment target | Reference                                                    |
| ----------------- | ------------------------------------------------------------ |
| Railway           | [references/deploy-railway.md](references/deploy-railway.md) |
| GCP               | [references/deploy-gcp.md](references/deploy-gcp.md)         |

Load only the references that apply. If a stack or deployment target has no reference file, inform the user and ask whether to proceed by matching existing conventions or wait for a reference to be added.

---

## 1. Pipeline Requirements

With stacks and deployment targets confirmed, determine:

- What events should trigger each workflow? (push, pull_request, release, schedule, manual)
- Which branches? (default branch, feature branches, release branches)
- What checks must pass at the confirmed target level? (refer to the level definitions above)
- Are there environment-specific secrets or configuration?
- Does the project use a monorepo structure requiring path filters?

For existing pipelines, read the current workflow files before proposing changes. Preserve working patterns; fix what's broken; add what's missing for the target level.

---

## 2. Workflow Structure

Organize workflows by concern. A single workflow file is acceptable at Level 1–2. At Level 3+, split by purpose.

Recommended separation:

| Workflow                | Trigger                    | Purpose                       | Level |
| ----------------------- | -------------------------- | ----------------------------- | ----- |
| `ci.yml`                | `push`, `pull_request`     | Lint, type-check, test, build | 1+    |
| `deploy-staging.yml`    | `push` to default branch   | Deploy to staging             | 3+    |
| `deploy-production.yml` | `release` or manual        | Deploy to production          | 4+    |
| `security.yml`          | `schedule`, `pull_request` | Dependency audit, SAST        | 3+    |

For monorepos with multiple stacks, use path filters to trigger only the relevant workflow:

```yaml
on:
  push:
    paths:
      - "apps/api/**"
      - "packages/shared/**"
```

Within each workflow, order jobs by dependency. Jobs that don't depend on each other run in parallel. Use explicit dependency declarations (e.g., `needs:`) for real dependencies only.

---

## 3. Job Implementation Principles

These apply regardless of CI platform or stack. Stack-specific syntax is in the reference files.

**Action/plugin version pinning.** Never use `@latest` or `@master`. Pinning to a full commit SHA is the most secure approach and is the only way to use an action as an immutable release. Major version tags (e.g., `@v3`) are acceptable at Level 1–2 for convenience, but Level 3+ must use full commit SHAs. See [GitHub Actions security: Using third-party actions](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions#using-third-party-actions).

**Caching (Level 2+).** Cache dependency installs using the lockfile hash as the cache key. See [GitHub Actions workflow syntax: cache](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions). Do not cache build outputs unless the build is genuinely slow (>2 min).

**Timeouts.** Set a timeout on every job. Defaults: 15 min for test jobs, 10 min for lint/build, 30 min for deployment. Adjust based on observed run times.

**Permissions (Level 3+).** Scope pipeline permissions to the minimum required using the `permissions` block. Default to `read-only` and add write permissions only where each job needs them. See [GitHub Actions security: Use GITHUB_TOKEN](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#modifying-the-permissions-for-the-github_token).

**Concurrency.** Cancel superseded runs on the same branch for CI jobs. Do not cancel deployment jobs — a cancelled deploy can leave infrastructure in a partial state.

---

## 4. Testing in CI

Run the same test command that developers run locally. Do not create a separate "CI test" configuration unless the CI environment genuinely requires different settings (e.g., a database service container).

**Service containers.** When tests need a database, use the CI platform's service container support rather than mocking. Pin the service image version.

**Coverage (Level 3+).** Generate a coverage report and either post it as a PR comment or upload it as a build artifact. Gate on a coverage threshold only if the project has established one.

**Flaky test handling.** Do not add automatic retries for flaky tests — that hides problems. If a test is intermittently failing in CI, investigate the root cause (timing, resource contention, missing cleanup).

---

## 5. Security Scanning (Level 3+)

Add security scanning appropriate to the stack. For guidance, see [GitHub Actions security: Using actions in workflows](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions#using-third-party-actions).

| Check                      | When                          | Level | Tool                                                       |
| -------------------------- | ----------------------------- | ----- | ---------------------------------------------------------- |
| Dependency vulnerabilities | Every PR and scheduled weekly | 3+    | `actions/dependency-check` or native package manager audit |
| Secret scanning            | Every push                    | 4+    | GitHub secret scanning (native)                            |
| SAST (static analysis)     | Every PR                      | 4+    | CodeQL or language-specific SAST                           |
| License compliance         | Release builds                | 5     | SBOM tools                                                 |
| SBOM generation            | Release builds                | 5     | syft or cyclonedx                                          |

Do not add scanning tools that produce noise the team will ignore. Start with dependency auditing; add SAST and secret scanning at Level 4 when the team has capacity to triage findings.

Configure automated dependency update tooling:

- **Dependabot** (GitHub native): Automatically opens PRs to update actions and dependencies. Supports all package managers. See [Keeping actions up to date with Dependabot](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/keeping-your-actions-up-to-date-with-dependabot).
- **Renovate** (open source): Alternative with more configuration options.

At Level 4+, consider using OpenID Connect (OIDC) for cloud authentication instead of long-lived credentials. See [Security hardening: OpenID Connect](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect).

---

## 6. Environment and Secrets Management

**Secrets.** Never hardcode credentials, API keys, or tokens in workflow files. Use the CI platform's secret storage and the `secrets` context (e.g., `${{ secrets.RAILWAY_TOKEN }}`). Name secrets consistently: `<SERVICE>_<PURPOSE>` (e.g., `RAILWAY_TOKEN`, `GCP_SERVICE_ACCOUNT_KEY`, `SLACK_WEBHOOK_URL`). For details, see [Using secrets in GitHub Actions](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions).

**Environment variables.** Use environment scoping to separate variables per deployment target (staging vs production). For non-secret configuration, set variables at the job level, not the step level, unless scoping is needed.

**Secret rotation.** At Level 4+, document which secrets exist, who owns them, and when they were last rotated. At Level 5, integrate with a secrets manager rather than storing long-lived credentials in the CI platform.

---

## 7. Quality Gate

Before reporting done, verify:

- **All workflow files are valid.** Lint or validate the pipeline configuration.
- **All referenced secrets exist** in the repository/environment settings (or are documented as required setup steps).
- **All action/plugin versions are pinned** appropriately for the target level (major version tags at Level 1–2, full commit SHAs at Level 3+).
- **Permissions are scoped** to the minimum required (Level 3+).
- **Timeouts are set** on all jobs.
- **Caching uses lockfile hashes** as keys (Level 2+).
- **Branch protection rules** require the CI status checks (Level 2+).
- **The pipeline runs successfully** on the current branch. Push a test commit or trigger a manual run and verify all jobs pass.
- **No sensitive values** are logged, echoed, or exposed in job outputs.

---

## Handoff

Summarize:

- Workflow files created or modified, and what each does.
- Trigger events and target branches.
- Secrets required (name, purpose, where to obtain — never the value).
- Branch protection rules to configure (if not automated).
- Deployment targets and promotion path.
- Deferred items required at the next level.
- Known limitations or manual steps the team must handle.

---

## Gotchas

- **`pull_request` vs `pull_request_target` (GitHub Actions).** Use `pull_request` for CI checks. `pull_request_target` runs in the context of the base branch and has write access to secrets — use it only for labeling or comment workflows, never for running untrusted PR code. See [GitHub Actions security: Mitigating risks of untrusted code checkout](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions#mitigating-the-risks-of-untrusted-code-checkout).
- **Concurrency and deployment.** Cancelling in-progress runs is safe for CI checks but dangerous for deployments. Use separate concurrency groups for CI and deploy, and disable cancellation on deploy workflows.
- **Composite actions vs reusable workflows (GitHub Actions).** Composite actions run in the caller's job (shared runner, shared env). Reusable workflows run as a separate job. Use reusable workflows when you need isolation; use composite actions when you need shared state. See [Reusing workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows).
- **Matrix builds and failure isolation.** By default, matrix builds cancel all other jobs when one fails. Disable fast-fail when you need to see which specific combinations fail.
- **Cache size limits.** CI platform caches have size limits. Large monorepos or projects with multiple lockfiles may hit this. Monitor cache usage and evict stale caches.
- **Forked PR permissions.** Forked PRs typically get a read-only `GITHUB_TOKEN` and no access to secrets (with the exception of `GITHUB_TOKEN`). Workflows that need write access on forked PRs must use platform-specific mechanisms with careful input sanitization. See [GitHub Actions security: script injection attacks](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions#good-practices-for-mitigating-script-injection-attacks).
