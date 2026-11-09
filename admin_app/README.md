# Project management

## Sign in

- we need to use google auth sign in tied to backend, not frontend

## Sidebar: API work

The new app sidebar (`src/app/(protected)/_components/AppSidebar.tsx`) is UI only for now. The
numbers below are hard-coded in `PLACEHOLDER_COUNTS` / `PLACEHOLDER_USAGE` and
need backend support before they can be wired up.

- **Content card count** for the current workspace (badge on "Question answering"
  and the "Content cards" meter). `GET /content/` returns the full list today; a
  lightweight count endpoint (or a `total` in the list response) would avoid
  fetching every card just to count them.
- **Urgency rule count** for the current workspace (badge on "Urgency detection").
  Same as above for `GET /urgency-rules/`.
- **Content quota** for the meter's denominator. Already returned as
  `content_quota` by `GET /workspace/current-workspace`; just needs wiring.
- **API calls used today.** Not exposed anywhere. The backend tracks remaining
  calls in Redis (`remaining-calls:{workspace_name}`, see
  `core_backend/app/auth/dependencies.py`) but no endpoint returns it. Add one
  (e.g. `GET /workspace/current-workspace/usage`) returning
  `{ api_calls_used_today, api_daily_quota, content_cards_used, content_quota }`.
  Note that a missing Redis key means no calls yet today, and a `null` quota
  means unlimited, so the UI needs to handle both.
- **"Need more? Contact us" link.** Needs a real destination (support email or
  form); currently `#contact`.
