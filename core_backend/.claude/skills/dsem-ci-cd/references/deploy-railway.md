# Deployment — Railway

Deployment patterns for Railway. Load this reference after the main CI/CD skill has confirmed Railway as the deployment target.

Railway supports automatic deployments from GitHub by default (connect a repo and it deploys on push). This reference covers the **GitHub Actions-driven** approach, which gives more control over when and how deployments happen — useful when the pipeline must gate deployment on CI checks passing.

## Overview

Railway provides two deployment mechanisms from CI:

1. **Railway CLI (`railway up`)** — pushes code to Railway, which builds and deploys it using Nixpacks or a Dockerfile. Simpler, works for most projects.
2. **Docker image push** — build the image in CI, push it to a registry, and tell Railway to use it. More control over the build, useful when the CI build differs from Railway's default.

Default to the CLI approach unless the project has a specific reason to manage its own Docker builds.

## Secrets Required

| Secret | Purpose |
|---|---|
| `RAILWAY_TOKEN` | Railway API token for the CLI. Generate from Railway dashboard → Account Settings → Tokens. Use a project-scoped token, not a personal account token. |

Optional:

| Variable | Purpose |
|---|---|
| `RAILWAY_SERVICE` | Service name within the Railway project (for multi-service projects). |

---

## Deploy with Railway CLI

### Staging deployment (Level 3+)

```yaml
name: Deploy Staging
on:
  push:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: deploy-staging
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    environment: staging
    steps:
      - uses: actions/checkout@v4

      - name: Install Railway CLI
        run: npm install -g @railway/cli

      - name: Deploy to staging
        run: railway up --detach
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}

      - name: Health check
        run: |
          STAGING_URL="${{ vars.STAGING_URL }}"
          for i in $(seq 1 12); do
            STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$STAGING_URL/health" 2>/dev/null || echo "000")
            if [ "$STATUS" = "200" ]; then
              echo "Health check passed"
              exit 0
            fi
            echo "Attempt $i: got $STATUS, waiting..."
            sleep 10
          done
          echo "Health check failed after 2 minutes"
          exit 1
```

`--detach` returns immediately after uploading the code. Railway builds and deploys asynchronously. The health check polls until the new deployment is live.

### Production deployment (Level 4+)

```yaml
name: Deploy Production
on:
  workflow_dispatch:
  release:
    types: [published]

permissions:
  contents: read

concurrency:
  group: deploy-production
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Install Railway CLI
        run: npm install -g @railway/cli

      - name: Deploy to production
        run: railway up --detach
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_PRODUCTION_TOKEN }}

      - name: Health check
        run: |
          PROD_URL="${{ vars.PRODUCTION_URL }}"
          for i in $(seq 1 12); do
            STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$PROD_URL/health" 2>/dev/null || echo "000")
            if [ "$STATUS" = "200" ]; then
              echo "Health check passed"
              exit 0
            fi
            echo "Attempt $i: got $STATUS, waiting..."
            sleep 10
          done
          echo "Health check failed after 2 minutes"
          exit 1

      - name: Notify on failure
        if: failure()
        uses: slackapi/slack-github-action@v2
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK_URL }}
          webhook-type: incoming-webhook
          payload: |
            {
              "text": "Production deploy FAILED: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
            }
```

Use separate Railway tokens for staging and production. Each token is scoped to a specific Railway environment/project.

### Multi-service projects

When a Railway project has multiple services (e.g., API + worker + cron), specify the service name:

```yaml
      - name: Deploy API
        run: railway up --detach --service api
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}

      - name: Deploy Worker
        run: railway up --detach --service worker
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

---

## Environment Variables in Railway

Railway manages environment variables through its dashboard and CLI. CI workflows should not set Railway env vars — they are configured once in the Railway dashboard and persist across deployments.

If a deployment requires a new env var:

1. Document it in the handoff (name, purpose, where to obtain the value).
2. The team sets it in Railway's dashboard before deploying.
3. The health check will catch a deployment that fails due to a missing env var.

---

## Rollback (Level 5)

Railway keeps previous deployments. To roll back:

```yaml
      - name: Rollback on health check failure
        if: failure()
        run: railway rollback
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

`railway rollback` redeploys the previous successful deployment. This is a fast operation — Railway doesn't rebuild, it restores the previous container.

---

## Gotchas

- **Railway's automatic deploys vs CI-driven deploys.** If the Railway project is connected to GitHub with automatic deploys enabled, pushing to the branch triggers both Railway's built-in deploy AND the GitHub Actions deploy. Disable Railway's automatic deploys in the project settings when using CI-driven deployments.
- **`railway up` without `--detach`.** Without `--detach`, the command streams build logs and blocks until the deployment completes. This is useful for debugging but adds 2–5 minutes to the pipeline. Use `--detach` in CI and rely on the health check to verify.
- **Health check timing.** Railway deployments take 30–120 seconds after `railway up --detach` returns. The health check must poll long enough. 12 attempts × 10 seconds = 2 minutes is a reasonable default.
- **Token scope.** A personal Railway token has access to all projects. Generate project-scoped tokens from the Railway dashboard for CI use. This limits blast radius if the token leaks.
- **Railway sleep mode.** Free-tier and some paid-tier Railway services sleep after inactivity. The first health check request may hit a cold start. Account for this in the health check timeout.

---

## Authoritative References

- [Railway documentation](https://docs.railway.com/)
- [Railway CLI reference](https://docs.railway.com/reference/cli-api)
- [Railway — Deployments](https://docs.railway.com/overview/the-basics#deployments)
- [GitHub Actions workflow syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
