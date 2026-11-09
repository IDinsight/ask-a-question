# Android Testing And Dependencies

Use this reference when adding dependencies or tests for an Android app.

## Dependency Rules

- **Use the project's existing dependency-management approach.** Prefer version catalogs (`gradle/libs.versions.toml`) for new or catalog-based projects; do not introduce one solely for a single small dependency change. When a catalog exists, reference aliases from the build script rather than pasting version strings inline.
- Prefer the versions already in the catalog when available. If a new library is needed, choose a version compatible with the current Android Gradle Plugin, Kotlin, Compose BOM, and min SDK.
- **Prefer KSP for Room annotation processing in Kotlin projects.** Room 3.0 removes KAPT/annotation-processor support entirely, so KSP is the forward-compatible choice. Use KAPT only when the installed Room version or the project's existing toolchain requires it.
- Keep Compose library versions managed by the Compose BOM when possible.
- Do not paste stale dependency blocks into `build.gradle.kts`; adapt them to the version catalog.

**After adding or changing a dependency:**
1. Sync Gradle and resolve the dependency graph.
2. Compile the affected module.
3. Run lint and the module's relevant tests.
4. Check for duplicate JSON converters, incompatible compiler plugins, and unnecessary transitive libraries.

Likely dependency groups (check the project's established stack before adding a new one):

- Room: local entities, DAOs, migrations, pending sync queries.
- WorkManager: one-time and periodic sync work.
- Lifecycle Compose: lifecycle-aware state collection from ViewModels.
- Navigation Compose: app navigation if multiple screens are involved.
- Retrofit/OkHttp or another agreed HTTP client: API calls.
- Kotlin serialization, Moshi, or Gson: JSON mapping, matching the chosen HTTP client.
- DataStore: small durable preferences such as auth metadata or last sync timestamp.
- Hilt or another DI approach: wiring repositories, API clients, DAOs, and workers when construction becomes non-trivial.

---

## Test Setup

Use focused tests at the layer where the behavior lives.

### DAO / Room Tests (Instrumented)

Test query behavior with Room's in-memory database:

- Pending operations returned in correct order.
- Duplicate/uniqueness constraints are enforced.
- Transactions commit or roll back correctly.
- Foreign-key constraints are enforced.
- Updates and deletes produce the expected local state.
- Flow-backed queries emit new values after writes.
- Paging queries return the expected pages and ordering.
- Cancellation behaves correctly for long-running queries where relevant.

Also write **migration tests** using `MigrationTestHelper` to verify:

- Each migration runs without crashing.
- Exported schema files are committed and match the actual schema.
- Data in existing rows survives the migration intact.
- Indexes, constraints, and default values are correct after upgrade.

### Repository Tests (JVM Unit)

Test with a fake remote API and a fake or in-memory local data source:

- Successful remote response is persisted locally and exposed correctly.
- Transient network failure (configure the fake to throw `IOException`) leaves the local record in `PENDING` state and schedules sync.
- Server validation/conflict error marks the record `FAILED` or `CONFLICT` with a useful message.
- Offline write assigns a stable client ID, sets `PENDING`, and enqueues sync.

Verify fields, not just record presence: check sync status, idempotency key, operation type, and timestamps where the design defines them.

### Worker Tests (JVM Unit)

Use `TestListenableWorkerBuilder` to test the worker's internal logic directly:

- Successful upload produces `Result.success()` and marks the local record `SYNCED`.
- Transient network failure produces `Result.retry()` and leaves local data intact.
- Auth failure (401/403) produces `Result.failure()` and marks the record `FAILED`.
- Validation/conflict response produces `Result.failure()` and marks the record `FAILED` or `CONFLICT`.
- Malformed local payload produces `Result.failure()` without crashing.
- Max-attempt policy, if defined, produces `Result.failure()` and stops retrying.

Also test the **work-request configuration** separately:

- The request has the intended network constraint.
- Backoff policy is `EXPONENTIAL` (or matches the design).
- Unique-work name is set correctly where required.

Use `WorkManagerTestInitHelper` + `TestDriver` only for integration concerns (constraint satisfaction, chaining, periodic scheduling, unique-work replacement) — not for testing the worker's business logic.

### Idempotency Tests

- Processing the same outbox operation twice (e.g., worker restart after successful upload but before local acknowledgement) does not create a duplicate server record.
- The idempotency key is propagated from the local record through the API request.
- Concurrent workers cannot upload the same outbox entry twice (verify via atomic status update or locking).

### ViewModel Tests (JVM Unit)

Use coroutine test dispatchers and fake repositories:

- UI state transitions correctly for loading, success, error, and empty outcomes.
- Validation logic produces the expected state changes.
- Online/offline branches (fake repository throws or succeeds) update state correctly.
- Queued-sync states are reflected accurately.

### Compose UI Tests (Instrumented)

Test behavior and semantics, not the component tree. Use semantics-based finders and user-action APIs:

- Key user flows complete end-to-end (fill form, submit, confirm result).
- Loading, success, error, and empty states render the correct semantics and accessible content.
- Offline and pending-upload banners appear under the correct conditions.
- Enabled/disabled states are reflected accurately in semantics.
- Error messages are accessible: content descriptions, roles, and announcements are correct.
- Touch targets meet the 48dp minimum.
- Status changes that matter to screen-reader users are announced correctly.

---

## Offline Smoke Scenarios

*These six scenarios apply only to features that support offline reads, offline writes, or durable synchronization. Non-offline features do not need them.*

Manually verify before calling an offline/sync feature done:

1. Start online, load data, then go offline and confirm cached data remains usable.
2. Create or edit data offline and confirm it appears immediately as saved locally.
3. Kill and relaunch the app while data is pending and confirm the pending state survives.
4. Reconnect and confirm WorkManager uploads the pending operation once.
5. Simulate a transient server/network failure and confirm retry/backoff leaves local data intact.
6. Simulate a validation/conflict response and confirm the UI gives a useful retry or correction path.

---

## Common Test Patterns

Keep examples adapted to real class names. Replace placeholders like `AppDatabase`, `PendingSyncDao`, `AppRepository`, and `SyncWorker` with project code.

### Room DAO Test

```kotlin
@RunWith(AndroidJUnit4::class)
class PendingSyncDaoTest {
    private lateinit var db: AppDatabase
    private lateinit var dao: PendingSyncDao

    @Before
    fun setup() {
        db = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext(),
            AppDatabase::class.java
        )
        // allowMainThreadQueries is acceptable in isolated instrumented tests,
        // but should not appear in production code — it masks accidental main-thread DB access.
        .allowMainThreadQueries()
        .build()
        dao = db.pendingSyncDao()
    }

    @After
    fun teardown() {
        db.close()
    }

    @Test
    fun pendingOperationsAreReturnedOldestFirst() = runTest {
        dao.insert(operation(id = "newer", createdAt = 2))
        dao.insert(operation(id = "older", createdAt = 1))

        assertThat(dao.pending().first().map { it.id })
            .containsExactly("older", "newer")
            .inOrder()
    }
}
```

### Repository Offline Test

Configure the fake API to throw a network exception rather than using a Boolean flag — tests should assert the system's response to a concrete failure, not a connectivity state.

```kotlin
@Test
fun saveWhileOfflinePersistsPendingOperation() = runTest {
    // Fake throws to simulate a transient network failure, not a reachability flag.
    val remote = FakeAppApi { throw IOException("Simulated network failure") }
    val repository = AppRepository(local, remote, syncScheduler)

    repository.saveHouseholdDraft(draft)

    val saved = local.householdDrafts().first { it.id == draft.id }
    assertThat(saved.syncStatus).isEqualTo(SyncStatus.PENDING)
    assertThat(saved.idempotencyKey).isNotNull()
    assertThat(local.pendingSyncOperations()).hasSize(1)
    // syncScheduler.enqueued is the right assertion when the repository triggers scheduling
    // directly. For architectures where a coordinator handles scheduling, assert that
    // contract instead.
    assertThat(syncScheduler.enqueued).isTrue()
}
```

### Worker Unit Test — Transient Failure (Retry)

Use `TestListenableWorkerBuilder` to test worker logic directly. This is separate from WorkManager integration tests (chains, constraints, unique work).

```kotlin
@Test
fun transientNetworkFailureReturnsRetry() = runTest {
    val worker = TestListenableWorkerBuilder<SyncWorker>(context)
        .setWorkerFactory(
            TestWorkerFactory(
                api = FakeApi { throw IOException("Simulated failure") },
                local = local,
            )
        )
        .build()

    assertThat(worker.doWork()).isEqualTo(ListenableWorker.Result.retry())
    assertThat(local.pendingOperations()).isNotEmpty()
}
```

### Work-Request Configuration Test

Verify constraints and backoff policy on the request itself, independently of the worker logic. The exact `workSpec` inspection API may vary by WorkManager version — adapt to the installed `work-testing` API.

```kotlin
@Test
fun syncRequestRequiresNetworkAndUsesExponentialBackoff() {
    val request = buildSyncRequest()

    assertThat(request.workSpec.constraints.requiredNetworkType)
        .isEqualTo(NetworkType.CONNECTED)
    assertThat(request.workSpec.backoffPolicy)
        .isEqualTo(BackoffPolicy.EXPONENTIAL)
}
```

---

## Authoritative References

- [Android architecture guide](https://developer.android.com/topic/architecture)
- [Jetpack Compose](https://developer.android.com/compose)
- [Material Design 3 in Compose](https://developer.android.com/develop/ui/compose/designsystems/material3)
- [Compose BOM version mapping](https://developer.android.com/develop/ui/compose/bom/bom-mapping)
- [State and Jetpack Compose](https://developer.android.com/develop/ui/compose/state)
- [`collectAsStateWithLifecycle`](https://developer.android.com/reference/kotlin/androidx/lifecycle/compose/collectAsStateWithLifecycle.composable)
- [Accessibility in Jetpack Compose](https://developer.android.com/develop/ui/compose/accessibility)
- [Room 3.0 (KSP-only, removes KAPT)](https://developer.android.com/jetpack/androidx/releases/room3)
- [Migrate from KAPT to KSP](https://developer.android.com/build/migrate-to-ksp)
- [WorkManager — Getting started](https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started)
- [WorkManager — Testing worker implementation](https://developer.android.com/develop/background-work/background-tasks/testing/persistent/worker-impl)
- [SavedStateHandle guide](https://developer.android.com/topic/libraries/architecture/viewmodel/viewmodel-savedstate)
- [Dependency injection with Hilt](https://developer.android.com/training/dependency-injection/hilt-android)
