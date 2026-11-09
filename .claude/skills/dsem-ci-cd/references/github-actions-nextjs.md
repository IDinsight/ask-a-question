# GitHub Actions — Next.js

GitHub Actions workflow patterns for Next.js applications. Load this reference after the main CI/CD skill has confirmed the stack and target level.

## Runtime Setup

Detect the package manager from the lockfile: `pnpm-lock.yaml` → pnpm, `package-lock.json` → npm, `bun.lockb` → bun, `yarn.lock` → yarn.

### pnpm (preferred)

```yaml
- uses: actions/checkout@v4
- uses: pnpm/action-setup@v4
- uses: actions/setup-node@v4
  with:
    node-version-file: '.nvmrc'
    cache: 'pnpm'
- run: pnpm install --frozen-lockfile
```

### npm

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-node@v4
  with:
    node-version-file: '.nvmrc'
    cache: 'npm'
- run: npm ci
```

`npm ci` (not `npm install`) respects the lockfile exactly and is faster. `npm install` may update the lockfile, causing non-reproducible builds.

---

## Level 1 — Lint + Test

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: '.nvmrc'
          cache: 'pnpm'
      - run: pnpm install --frozen-lockfile
      - run: pnpm lint

  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: '.nvmrc'
          cache: 'pnpm'
      - run: pnpm install --frozen-lockfile
      - run: pnpm test
```

---

## Level 2 — Add Type Check + Build

```yaml
  type-check:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: '.nvmrc'
          cache: 'pnpm'
      - run: pnpm install --frozen-lockfile
      - run: pnpm type-check

  build:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: [lint, type-check, test]
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: '.nvmrc'
          cache: 'pnpm'
      - run: pnpm install --frozen-lockfile
      - run: pnpm build
```

If the project doesn't have a `type-check` script, add one to `package.json`:

```json
{
  "scripts": {
    "type-check": "tsc --noEmit"
  }
}
```

### Next.js build cache (Level 2+)

Cache the Next.js build output to speed up subsequent builds:

```yaml
      - uses: actions/cache@v4
        with:
          path: .next/cache
          key: nextjs-${{ runner.os }}-${{ hashFiles('**/pnpm-lock.yaml') }}-${{ hashFiles('**/*.ts', '**/*.tsx') }}
          restore-keys: |
            nextjs-${{ runner.os }}-${{ hashFiles('**/pnpm-lock.yaml') }}-
```

---

## Level 3 — Security Scan + Coverage

### Test with coverage

```yaml
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: '.nvmrc'
          cache: 'pnpm'
      - run: pnpm install --frozen-lockfile
      - run: pnpm test -- --coverage
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage-report
          path: coverage/
          retention-days: 7
```

### Security scanning

```yaml
  security:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: '.nvmrc'
          cache: 'pnpm'
      - run: pnpm install --frozen-lockfile
      - run: pnpm audit --audit-level=high
```

### Concurrency and permissions (Level 3+)

Add these at the top of every workflow:

```yaml
permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

---

## Level 4 — SAST + Notifications

### Static analysis with Semgrep

Add Semgrep for comprehensive static analysis of TypeScript/JavaScript code:

```yaml
  sast:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: returntocorp/semgrep-action@v1
        with:
          generateSarif: true
          config: >
            p/owasp-top-ten
            p/security-audit
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: semgrep.sarif
```

Semgrep checks for security vulnerabilities, code quality issues, and OWASP Top 10 patterns. Use `config` to select rulesets (e.g., `p/owasp-top-ten` for web vulnerabilities). Results upload to GitHub's Security tab via SARIF format. See [Semgrep CI integration](https://docs.semgrep.dev/deployment/add-semgrep-to-ci/).

### Slack notification on failure

```yaml
  notify:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    needs: [lint, type-check, test, build, sast]
    if: failure() && github.ref == 'refs/heads/main'
    steps:
      - uses: slackapi/slack-github-action@v2
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK_URL }}
          webhook-type: incoming-webhook
          payload: |
            {
              "text": "Next.js CI failed on main: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
            }
```

---

## Level 5 — Pin Actions + Dependabot

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

---

## E2E Testing (Optional)

When the project uses Playwright for end-to-end tests:

```yaml
  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    needs: [build]
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: '.nvmrc'
          cache: 'pnpm'
      - run: pnpm install --frozen-lockfile
      - run: pnpm exec playwright install --with-deps chromium
      - run: pnpm build
      - run: pnpm exec playwright test
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 7
```

---

## Environment Variables

Next.js has two categories of env vars:

- **Build-time** (`NEXT_PUBLIC_*`): Baked into the client bundle during `pnpm build`. Set these as `env:` in the build job.
- **Runtime** (`SERVER_*`, `DATABASE_URL`, etc.): Available only on the server. Set these in the deployment environment, not in CI.

```yaml
  build:
    runs-on: ubuntu-latest
    env:
      NEXT_PUBLIC_API_URL: ${{ vars.NEXT_PUBLIC_API_URL }}
    steps:
      # ...
      - run: pnpm build
```

---

## Common Pitfalls

- **`npm install` instead of `npm ci`.** `npm ci` deletes `node_modules` and installs from the lockfile. `npm install` may update the lockfile.
- **Missing `--frozen-lockfile`.** The pnpm equivalent of `npm ci`. Without it, pnpm may install different versions.
- **Caching `node_modules` directly.** Cache the package manager's store, not `node_modules`. The `setup-node` action handles this with `cache: 'npm'` or `cache: 'pnpm'`.
- **`NEXT_PUBLIC_*` vars not available at build time.** These are inlined during the build step. If set only in the deployment environment, they'll be `undefined` in the client bundle. Set them in the build job's `env:` block.
- **Playwright browser not installed.** `playwright install --with-deps chromium` installs both the browser binary and its OS dependencies. Without `--with-deps`, the browser may fail to launch in CI.

---

## Authoritative References

- [GitHub Actions workflow syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [actions/setup-node](https://github.com/actions/setup-node)
- [pnpm/action-setup](https://github.com/pnpm/action-setup)
- [actions/cache](https://github.com/actions/cache)
- [Semgrep CI integration](https://docs.semgrep.dev/deployment/add-semgrep-to-ci/)
- [Dependabot configuration](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/keeping-your-actions-up-to-date-with-dependabot)
- [Next.js documentation](https://nextjs.org/docs)
- [Playwright documentation](https://playwright.dev/)
