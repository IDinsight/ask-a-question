---
name: dsem-android
description: Use when creating, reviewing, or refactoring an Android app, especially Jetpack Compose screens, Material 3 UI patterns, API-backed data flows, offline save, Room/local cache, queued uploads, WorkManager sync, connectivity handling, ViewModels, repositories, and Android tests. Triggered explicitly via `/dsem android <prompt>`. When triggered, first read `.agents/skills/planner/SKILL.md` and use its routing, assumptions, sequence, and verification plan before this skill's steps.
---

# Android

Use this skill for Android work. Locate the Android app module first — it is commonly under `mobile/`, `app/`, or the repository root; inspect the top-level folders rather than assuming a fixed path. These skills target Jetpack Compose apps using Material 3. Treat the app as an existing application to evolve unless the project is clearly a blank scaffold.

A common product requirement for these apps is: use APIs when online, keep the app useful offline, save user work locally when offline, and upload/sync queued changes when connectivity returns. Apply the offline/sync guidance below only when the product actually needs it.

## Invocation

Triggered by `/dsem android <prompt>` or when the planner routes Android work here.

- **Mode** is inferred from the prompt: _build, add, implement, create, refactor_ → implement; _review, audit, assess, check_ → review.
- **Target level** (1–5) is confirmed before work begins.

## Important Notes

- The most important principle is **separation of concerns**: keep UI, data, API, and sync responsibilities distinct.
- The second most important principle is **unidirectional data flow**: the UI observes state and emits events, but does not call APIs, Room, or WorkManager directly.
- Do not use an Activity or composable as the sole owner of durable application
  data or screen-level business state. Keep ephemeral UI-element state close to
  the UI; hoist it only as high as required. Store screen-level state in an
  appropriate state holder and durable user data in persistent storage.
- For offline-first repositories, higher layers read application data from the
  local data source. Network responses are persisted locally before becoming
  observable UI state.
- The server may remain authoritative for server-owned fields, permissions,
  canonical identifiers, or conflict resolution. Define authority per field or
  entity rather than describing both the database and API as competing sources
  of truth.

## Level clarification prerequisite

Before applying this skill, confirm which level applies to the work. For **reviews**, identify and report the current level. For **implementation**, clarify what each level entails and agree on scope before starting. Level 1 requires the least effort; Level 5 the most. Testing is introduced at Level 3 and required from there up.

- **Level 1 — Mockup / proof-of-concept shell.** Static Compose screens wired together with basic navigation. No real data, no ViewModels, no backend. State may live directly in composables. The goal is to demonstrate a user flow or validate a UI concept quickly — not to ship working functionality.

- **Level 2 — Structured UI layer.** Multiple screens with clear UI-layer boundaries per the [Android architecture guidelines](https://developer.android.com/topic/architecture). ViewModels own screen state exposed as `StateFlow`; composables observe and emit events only. Navigation graph is well-defined and may include nested graphs. No data layer yet — data is stubbed or hardcoded, but the presentation layer is production-shaped.

- **Level 3 — Full-featured online POC (internal testing target).** All screens are implemented end-to-end with a full data layer: repository, remote data source, and API client. The app is online-only; the remote API is the source of truth. UDF is enforced throughout. Loading, success, error, and empty states are handled explicitly. Navigation is complete including deep links where needed. The app covers all intended features and is ready for internal user testing — functional but allowed to have rough edges. **Tests are required from this level forward**: ViewModel, repository, and key UI flow tests.

- **Level 4 — Offline-capable app.** Builds on Level 3. Adds a local data source (Room), an outbox for queued mutations, and WorkManager-based background sync. The API remains the source of truth; local storage is the read source. A domain layer sits between the UI and data layers when warranted. All sync paths — success, retry, failure, conflict — are handled and surfaced in the UI.

- **Level 5 — Production-ready.** Builds on Level 4. Security configuration is applied (certificate pinning, secrets management, ProGuard/R8 rules, exported component review). The app meets release quality: no debug flags in production builds, crash reporting and analytics wired up, accessibility requirements met, performance baselines verified. Ready for external testing (e.g. UAT, beta) and store deployment.

## Planner Prerequisite

Before applying this skill, read `.agents/skills/planner/SKILL.md` and run the planner pass first. Use it to confirm affected layers, blocking questions, non-blocking assumptions, task order, additional skills or references, and verification expectations. Then follow this skill for Android-specific implementation details.

If the planner routes part of the work to another skill, load that skill before editing files in that area.

## First Checks

- Inspect the module's `build.gradle.kts` (e.g. `app/build.gradle.kts`), the version catalog (e.g. `gradle/libs.versions.toml`), and existing packages before adding dependencies or folders.
- Read the project's API contract (e.g. an OpenAPI spec such as `api/api-spec.yml`, if one exists) before implementing network calls, request/response models, auth, pagination, or error handling.
- For Compose UI, layout, navigation surface, or Material component work, always read `references/compose-material-ui.md` and check the linked official Android Compose and Material 3 docs when network is available. Treat the official docs as newer than the local summary.
- For any new Material component, verify the current `androidx.compose.material3` or Material 3 adaptive dependency exposed by the module's version catalog before using it. If a dependency/version change is needed, read `references/testing-and-deps.md` first.
- Preserve existing Compose and Material 3 patterns in the app's existing package root (e.g. `app/src/main/java/<package>/`).
- Add only the architecture needed for the requested feature, but keep UI, data, API, and sync responsibilities separated from the start.

## Architecture & Presentation Layer Boundaries

Use this default flow (full offline-first stack — omit layers not required by the feature):

```text
Compose Material 3 UI (State & Intents Only)
  -> ViewModel with StateFlow (Owns UI State & Logic)
  -> Repository/use case
  -> Local data source: Room/cache/outbox    [offline-first only]
  -> Remote data source: API client
  -> Sync worker: WorkManager                [offline-first only]
```

For read-only or non-persistent features, the data layer may be just a repository wrapping an API client.

### Core Architecture Rules

- **Composables render state and emit events only.** They do not call APIs, Room, or WorkManager directly.
- **ViewModels handle user actions that involve business logic or screen-level state.** They call repositories. UI-only state (focus, expansion, scroll position, animation) may remain in the composable or a plain state holder.
- **Repositories expose data and mutation operations and coordinate their data sources.** They may request synchronization through an injected scheduler. For complex multi-entity workflows, place synchronization policy in a dedicated coordinator or domain component rather than expanding every repository indefinitely.
- **For offline-first data flows, local storage is the read source of truth.** Different repositories may have different authority models — define authority per repository type, not globally.
- **API calls are opportunistic:** always persist locally first, then attempt immediate network sync as an optimization. Correctness depends on the operation result, not connectivity status.

### Strict Unidirectional Data Flow (UDF)

- **One Cohesive State Model Per Screen:** Expose a single UI-state model per screen or navigation destination. Use a `data class` when multiple conditions can coexist; use a sealed hierarchy only when states are genuinely mutually exclusive.

- **State Collection:** Prefer `collectAsStateWithLifecycle()` from `androidx.lifecycle.compose` when collecting `Flow` in Android Compose UI to ensure lifecycle-aware collection. (Not applicable in Previews, tests, or non-Android Compose targets.)
- **Screen State is Multi-Dimensional:** Model `UiState` as a flat `data class` with independent fields — not a sealed interface with mutually exclusive variants. A sealed root type forces the UI into exactly one state at a time; a data class lets orthogonal concerns be true simultaneously. A real screen may need to show cached content, a refresh spinner, an offline banner, a pending-upload count, and a non-blocking error all at once:

  ```kotlin
  data class ScreenUiState(
      val content: ScreenContent? = null,  // null = initial load not yet complete
      val isLoading: Boolean = false,       // true during initial load or hard refresh
      val isRefreshing: Boolean = false,    // true during background / pull-to-refresh
      val isOffline: Boolean = false,
      val pendingUploads: Int = 0,
      val transientError: String? = null,
  )
  ```

  The ViewModel exposes a single `StateFlow<ScreenUiState>` and UDF is fully preserved — the composable still only reads state and emits events. For transient messages, the composable notifies the ViewModel when the message has been shown (e.g., `onErrorDismissed()`); the ViewModel owns the state update.

- **Nested Sealed Class for Mutually Exclusive Content Phases Only:** Use a sealed class when variants are genuinely mutually exclusive, such as the initial page-load arc, and embed it as a field on the outer data class rather than making it the root type:

  ```kotlin
  sealed interface ContentPhase {
      object Loading : ContentPhase
      data class Ready(val data: ScreenContent) : ContentPhase
      data class Empty(val reason: EmptyReason) : ContentPhase
  }

  data class ScreenUiState(
      val contentPhase: ContentPhase = ContentPhase.Loading,
      val isRefreshing: Boolean = false,
      val isOffline: Boolean = false,
      val pendingUploads: Int = 0,
      val transientError: String? = null,
  )
  ```

  Prefer a data class when conditions can coexist. A sealed root is appropriate only when the entire screen is genuinely in one of several mutually exclusive modes (e.g., a full-screen auth flow: `Unauthenticated | Authenticated | Locked`). The common failure mode is using a sealed root for a content screen and discovering you need to represent a refresh failure alongside cached content — that requires a data class.

- **UI Events — Prefer Direct ViewModel Calls:** For most screens, composables call ViewModel methods directly and receive individual typed lambdas per action. The ViewModel processes the action immediately and reflects the result as a state update. Google recommends this as the default; a single-funnel sealed event class adds indirection without benefit for typical CRUD screens.

  ```kotlin
  // Default: individual typed lambdas, direct ViewModel calls
  @Composable
  fun SearchScreen(
      uiState: SearchUiState,
      onQueryChanged: (String) -> Unit,
      onSubmit: () -> Unit,
      onRetry: () -> Unit,
  )
  ```

  Typed action objects (a sealed `UiIntent` class) are appropriate when the screen has a genuine state machine, a reducer pattern, complex multi-step event chains, or a need for event replay or logging. Use them when the indirection is earning its keep — not as a default structure.

---

## Online And Offline Data Flow

For user-created or editable records:

- Generate a stable client ID before saving.
- Save locally first with a sync state such as `PENDING`, `SYNCING`, `SYNCED`, `FAILED`, or `CONFLICT`.
- If online, attempt immediate upload after the local save or enqueue one-time sync work.
- If offline or the network call fails transiently, keep the local record pending and retry later.
- If the server rejects the payload, mark the record `FAILED` or `CONFLICT` with a useful error instead of deleting local data.
- Use idempotency keys for create/commit/upload flows so retries do not duplicate records.

For server-owned/reference data:

- Fetch from the API when online and cache the result locally.
- Render cached data offline with clear stale/offline state where it matters.
- Do not block navigation or form entry just because refresh failed.

## Sync Model

Prefer an outbox for queued mutations once more than one entity or operation must sync:

```text
SyncOperation(
  id,
  entityType,
  entityId,
  operation,
  payloadJson,      // or omit and re-read from normalized local data at execution time
  status,
  attempts,
  idempotencyKey,
  lastError,
  createdAt,
  updatedAt
)
```

Two valid outbox designs: (a) serialize the full request payload into `payloadJson` at write time — predictable, survives local edits to the entity but requires migration if the schema changes; (b) store only entity IDs and re-read current state at sync time — simpler to maintain but must handle the case where the entity was deleted or edited before the worker runs. Choose based on whether mutation ordering and payload immutability matter for the feature.

Use WorkManager for deferrable work that must survive process or device restarts (background sync, periodic refresh, deferred uploads). Immediate network calls triggered by user actions fire directly; WorkManager is the recovery path if the app dies mid-flight.

- Enqueue one-time sync after local writes with a connected-network constraint.
- Use unique work names so repeated saves do not pile up duplicate sync jobs.
- Use exponential backoff for transient network/server failures.
- Add periodic sync only when the product needs background catch-up.
- Keep sync idempotent and safe to resume after app kill, reboot, or partial failure.

Do not use raw services, timers, or manual polling for normal deferrable sync. Foreground services are heavily restricted on modern Android and require a declared, valid foreground service type. Refer to current platform guidance before using one — the allowed types and restrictions change across API levels.

## Package Shape

Use this shape when adding real app layers, adjusting names to match existing code:

```text
data/local       Room entities, DAOs, database, local mappers
data/remote      API interfaces/clients, DTOs, auth headers
data/sync        WorkManager workers, outbox processor, connectivity monitor
data/repository  Repository implementations
domain/model     App/domain models when DTO/entity separation helps
ui/<feature>     Compose screens, ViewModels, UI state, UI events
ui/components    Shared Material 3 components
ui/theme         Color, typography, shapes, app theme
```

Avoid premature layers for tiny features, but never put data access or network calls directly in composables.

## Compose And Material 3 UI

Treat Material 3 and Android Compose documentation as the source of truth for UI. For UI work, read `references/compose-material-ui.md`; it covers official docs to check, component selection, layout/adaptive behavior, theming, accessibility, and review checks.

When docs, memory, and this skill disagree, use this priority:

1. Current official Android Compose docs and Material 3 component guidance.
2. Components and versions actually available through the app's Gradle catalog/BOM.
3. Existing app patterns already established in this project.
4. This skill reference as a durable local summary.

Core rules:

- Use `androidx.compose.material3` components before custom controls, and choose component variants by Material role, emphasis, state, and surface.
- Prefer stable Material 3 APIs. If the best current component is experimental or requires a new Material 3 adaptive artifact, add the smallest compatible dependency and make the opt-in explicit.
- Use `Scaffold` for app structure and consume its padding correctly.
- Keep the shared app theme authoritative: `MaterialTheme.colorScheme`, `MaterialTheme.typography`, and `MaterialTheme.shapes`.
- Use lazy containers for unbounded lists and stable keys for changing lists. For apps targeting tablets, foldables, or large screens, use adaptive layouts instead of stretched phone layouts.
- Provide minimum 48dp touch targets, meaningful semantics/content descriptions, and readable contrast in light, dark, and dynamic color themes.
- Use short, purposeful Material/Compose motion for state changes; avoid decorative animation.
- Add or update Compose previews for meaningful screen states when UI structure or component choice changes.

### Resilient Forms, Status, And Offline Copy

- **Form State:** Validate inline and preserve in-progress values across process death. For forms with significant user investment (multi-step flows, long text entry, file attachments), auto-save drafts to local storage.
- **SavedStateHandle:** Use for navigation arguments and small UI state variables; use Room for durable drafts and submitted business objects.
- **Calm Offline UI:** Show a highly polished, contextual offline/pending indicator. Use clear, explicit micro-copy like _"Saved on this device"_ or _"Will sync when online"_. Surface sync errors with a clear, tactile retry path.
- **Empty & Error States:** Provide clear content, an accessible visual hierarchy, and a recovery path. Follow the app's existing design system rather than a fixed template — avoid raw unstyled text, but do not mandate a specific layout, icon treatment, or button count.
- **Accessibility:** Support minimum 48dp touch targets, clear labels/content descriptions for visual elements, readable high-contrast ratios, and ensure status updates do not rely entirely on color coding.

---

## API Integration

- Keep request/response DTOs aligned with the project's API contract/spec.
- Map DTOs to local/domain models instead of passing network models through the UI.
- Handle auth, refresh, 401/403, validation errors, rate limits, and correlation IDs consistently.
- Use bounded pagination and deterministic sorting/filtering for list screens.
- Never log bearer tokens, OTPs, documents, or sensitive PII.

## Dependencies And Tests

Read `references/testing-and-deps.md` when adding Room, WorkManager, networking, lifecycle, navigation, DI, or tests.

Test priorities:

- ViewModel tests for UI state, validation, online/offline branches, and queued-sync states.
- Repository tests with fake remote API and local test database.
- DAO tests for inserts, pending queries, conflict/error states, and pagination/filtering.
- Worker tests for success, retry, failure, and idempotency.
- Compose UI tests for key flows, offline banners, disabled/loading states, and Material 3 semantics.
- Manual smoke tests: create/edit offline, kill the app, relaunch, reconnect, verify upload and final server/local state.

## Review Checklist

- API calls and database writes are completely decoupled from composables.
- UI collects state using `collectAsStateWithLifecycle()` (or equivalent lifecycle-aware collection).
- _(Offline-capable features)_ User writes are captured locally in the cache/outbox before firing network operations.
- _(Offline-capable features)_ Offline mode preserves current tasks seamlessly and surfaces pending items explicitly.
- _(Offline-capable features)_ WorkManager handles retryable background sync using exponential backoff.
- Screen designs use current Material 3 components, app theme tokens, container surfaces, and adaptive layout patterns from `references/compose-material-ui.md`.
- Request/response DTOs conform to the project's API contract/spec; domain and UI models are mapped separately and may differ intentionally.
- Tests validate correct handling of loading, success, error, and queued states.
- After any dependency or API surface change, run the project's build and relevant lint/test tasks to verify compatibility.
