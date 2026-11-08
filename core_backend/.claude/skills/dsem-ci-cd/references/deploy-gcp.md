# Deployment — Google Cloud Platform

Deployment patterns for GCP, focused on Cloud Run as the primary compute target. Load this reference after the main CI/CD skill has confirmed GCP as the deployment target.

## Overview

The standard GCP deployment flow from GitHub Actions:

1. Authenticate with GCP using Workload Identity Federation (preferred) or a service account key.
2. Build a container image and push it to Artifact Registry (or GCR).
3. Deploy the image to Cloud Run.
4. Run a health check against the deployed service.

Workload Identity Federation is the preferred auth method — it avoids storing long-lived service account keys as GitHub secrets.

## Secrets Required

### Workload Identity Federation (preferred)

| Secret/Variable | Purpose |
|---|---|
| `GCP_PROJECT_ID` | GCP project ID |
| `WIF_PROVIDER` | Workload Identity Provider resource name (e.g., `projects/123/locations/global/workloadIdentityPools/github/providers/github-actions`) |
| `WIF_SERVICE_ACCOUNT` | Service account email (e.g., `deploy@project-id.iam.gserviceaccount.com`) |

### Service account key (fallback)

| Secret | Purpose |
|---|---|
| `GCP_PROJECT_ID` | GCP project ID |
| `GCP_SA_KEY` | Base64-encoded service account key JSON |

Use service account keys only when Workload Identity Federation cannot be configured (e.g., the GCP org restricts WIF). Rotate keys regularly and scope the service account to the minimum required permissions.

---

## Authentication

### Workload Identity Federation

```yaml
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
```

One-time setup in GCP:

1. Create a Workload Identity Pool and Provider linked to the GitHub OIDC issuer.
2. Grant the provider's principal set the `roles/iam.workloadIdentityUser` role on the deploy service account.
3. Grant the service account the minimum roles: `roles/run.developer`, `roles/artifactregistry.writer`, and `roles/iam.serviceAccountUser`.

The `google-github-actions/auth` action documentation has the full setup steps.

### Service account key

```yaml
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
```

---

## Build and Push Container Image

### Using Cloud Build (remote build)

```yaml
      - uses: google-github-actions/setup-gcloud@v2

      - name: Build and push
        run: |
          gcloud builds submit \
            --tag ${{ vars.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/app/${{ github.event.repository.name }}:${{ github.sha }} \
            --project ${{ secrets.GCP_PROJECT_ID }}
```

Cloud Build runs the Docker build on GCP infrastructure. Useful when the build requires GCP-internal resources or when GitHub runners are too slow.

### Using Docker (local build)

```yaml
      - name: Configure Docker for Artifact Registry
        run: gcloud auth configure-docker ${{ vars.GCP_REGION }}-docker.pkg.dev --quiet

      - name: Build and push
        run: |
          IMAGE="${{ vars.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/app/${{ github.event.repository.name }}:${{ github.sha }}"
          docker build -t "$IMAGE" .
          docker push "$IMAGE"
```

---

## Deploy to Cloud Run

### Staging deployment (Level 3+)

```yaml
name: Deploy Staging
on:
  push:
    branches: [main]

permissions:
  contents: read
  id-token: write

concurrency:
  group: deploy-staging
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    environment: staging
    steps:
      - uses: actions/checkout@v4

      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}

      - uses: google-github-actions/setup-gcloud@v2

      - name: Build and push
        run: |
          gcloud builds submit \
            --tag ${{ vars.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/app/${{ github.event.repository.name }}:${{ github.sha }} \
            --project ${{ secrets.GCP_PROJECT_ID }}

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy ${{ github.event.repository.name }} \
            --image ${{ vars.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/app/${{ github.event.repository.name }}:${{ github.sha }} \
            --region ${{ vars.GCP_REGION }} \
            --platform managed \
            --project ${{ secrets.GCP_PROJECT_ID }}

      - name: Health check
        run: |
          SERVICE_URL=$(gcloud run services describe ${{ github.event.repository.name }} \
            --region ${{ vars.GCP_REGION }} \
            --project ${{ secrets.GCP_PROJECT_ID }} \
            --format 'value(status.url)')
          for i in $(seq 1 12); do
            STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/health" 2>/dev/null || echo "000")
            if [ "$STATUS" = "200" ]; then
              echo "Health check passed: $SERVICE_URL"
              exit 0
            fi
            echo "Attempt $i: got $STATUS, waiting..."
            sleep 10
          done
          echo "Health check failed after 2 minutes"
          exit 1
```

### Production deployment (Level 4+)

```yaml
name: Deploy Production
on:
  workflow_dispatch:
  release:
    types: [published]

permissions:
  contents: read
  id-token: write

concurrency:
  group: deploy-production
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    environment: production
    steps:
      - uses: actions/checkout@v4

      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}

      - uses: google-github-actions/setup-gcloud@v2

      - name: Build and push
        run: |
          gcloud builds submit \
            --tag ${{ vars.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/app/${{ github.event.repository.name }}:${{ github.sha }} \
            --project ${{ secrets.GCP_PROJECT_ID }}

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy ${{ github.event.repository.name }} \
            --image ${{ vars.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/app/${{ github.event.repository.name }}:${{ github.sha }} \
            --region ${{ vars.GCP_REGION }} \
            --platform managed \
            --project ${{ secrets.GCP_PROJECT_ID }} \
            --no-traffic

      - name: Verify new revision
        run: |
          SERVICE_URL=$(gcloud run services describe ${{ github.event.repository.name }} \
            --region ${{ vars.GCP_REGION }} \
            --project ${{ secrets.GCP_PROJECT_ID }} \
            --format 'value(status.url)')
          # Test the new revision directly using its tag
          REVISION_URL=$(gcloud run revisions list \
            --service ${{ github.event.repository.name }} \
            --region ${{ vars.GCP_REGION }} \
            --project ${{ secrets.GCP_PROJECT_ID }} \
            --sort-by '~metadata.creationTimestamp' \
            --limit 1 \
            --format 'value(status.url)')
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$REVISION_URL/health" 2>/dev/null || echo "000")
          if [ "$STATUS" != "200" ]; then
            echo "New revision health check failed: $STATUS"
            exit 1
          fi

      - name: Route traffic to new revision
        run: |
          gcloud run services update-traffic ${{ github.event.repository.name }} \
            --region ${{ vars.GCP_REGION }} \
            --project ${{ secrets.GCP_PROJECT_ID }} \
            --to-latest

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

The `--no-traffic` + traffic split pattern deploys the new revision without routing traffic to it, verifies it, then shifts traffic. This enables zero-downtime deployments.

---

## Rollback (Level 5)

Cloud Run keeps previous revisions. To roll back, route traffic to the previous revision:

```yaml
      - name: Rollback on failure
        if: failure()
        run: |
          PREV_REVISION=$(gcloud run revisions list \
            --service ${{ github.event.repository.name }} \
            --region ${{ vars.GCP_REGION }} \
            --project ${{ secrets.GCP_PROJECT_ID }} \
            --sort-by '~metadata.creationTimestamp' \
            --limit 2 \
            --format 'value(metadata.name)' | tail -1)
          gcloud run services update-traffic ${{ github.event.repository.name }} \
            --region ${{ vars.GCP_REGION }} \
            --project ${{ secrets.GCP_PROJECT_ID }} \
            --to-revisions "$PREV_REVISION=100"
          echo "Rolled back to revision: $PREV_REVISION"
```

---

## Other GCP Targets

### App Engine

Replace the Cloud Run deploy step:

```yaml
      - name: Deploy to App Engine
        run: gcloud app deploy app.yaml --project ${{ secrets.GCP_PROJECT_ID }} --quiet
```

App Engine deployments are slower (2–5 minutes) and don't support the `--no-traffic` canary pattern as cleanly. Use `--no-promote` and `gcloud app services set-traffic` for traffic splitting.

### GKE (Google Kubernetes Engine)

GKE deployments use `kubectl` and are significantly more complex. The typical flow:

1. Authenticate with `google-github-actions/auth`.
2. Get GKE credentials: `gcloud container clusters get-credentials`.
3. Update the image in the Kubernetes manifest or Helm chart.
4. Apply with `kubectl apply` or `helm upgrade`.
5. Wait for rollout: `kubectl rollout status`.

GKE deployments are outside the scope of this reference's standard patterns. Consult the project's Kubernetes documentation.

---

## Gotchas

- **Workload Identity Federation setup.** WIF requires one-time setup in GCP (pool, provider, IAM bindings). If the auth step fails with "Unable to generate access token," the WIF configuration is incomplete. Check the pool/provider resource names and the IAM binding on the service account.
- **Artifact Registry vs Container Registry.** GCR (`gcr.io`) is legacy. New projects should use Artifact Registry (`<region>-docker.pkg.dev`). The auth and push commands differ slightly.
- **Cloud Build timeout.** Cloud Build has a default timeout of 10 minutes. Large Docker builds may exceed this. Set `--timeout=20m` on `gcloud builds submit` if needed.
- **Cloud Run cold starts.** Cloud Run scales to zero by default. The first request after idle incurs a cold start (1–10 seconds depending on the image size and startup time). Set `--min-instances=1` for production services that need consistent latency.
- **`--no-traffic` requires `--allow-unauthenticated` or IAM.** If the service requires authentication, the health check step must use an identity token. Add `--set-env-vars` to bypass auth for the health endpoint, or use `gcloud run services proxy` for the check.
- **`id-token: write` permission.** Workload Identity Federation requires the `id-token: write` permission in the workflow. Without it, the auth step silently falls back to looking for a credentials JSON and fails.

---

## Authoritative References

- [Google Cloud — Cloud Run documentation](https://cloud.google.com/run/docs)
- [Google Cloud — Artifact Registry](https://cloud.google.com/artifact-registry/docs)
- [Google Cloud — Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [google-github-actions/auth](https://github.com/google-github-actions/auth)
- [google-github-actions/setup-gcloud](https://github.com/google-github-actions/setup-gcloud)
- [GitHub Actions — OpenID Connect for cloud deployments](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [GitHub Actions workflow syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
