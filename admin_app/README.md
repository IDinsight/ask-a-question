# Project management

## Sign in

- we need to use google auth sign in tied to backend, not frontend

## Sidebar: API work

The sidebar's badges ("Question answering", "Urgency detection") and the
"Workspace usage" meters come from `GET /workspace/current-workspace/usage`
(`useWorkspaceUsageQuery`). A `null` quota means unlimited and renders as `∞`.
Content and urgency rule mutations invalidate that query; it also refetches
every minute to keep "API calls today" current.

Still open:

- **"Need more? Contact us" link.** Needs a real destination (support email or
  form); currently `#contact`.
