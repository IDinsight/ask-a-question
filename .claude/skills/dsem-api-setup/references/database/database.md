---
name: database
description: >
  Universal database principles for the api-setup skill. Loaded at Level 2+
  alongside the stack reference and a DB variant. Defines principles — the
  variant (postgres.md, mongodb.md) provides the concrete implementation.
  Apply only what the target level requires.
---

# Database Reference — Universal Principles

These rules apply regardless of stack, ORM, or database engine. Where a DB variant conflicts with this file, the variant wins.

---

## Naming convention

| Environment | Pattern | Example |
|---|---|---|
| Development | `{project_name}_dev` | `orders_api_dev` |
| Test | `{project_name}_test` | `orders_api_test` |
| Production | `{project_name}_prod` | `orders_api_prod` |

- Replace hyphens with underscores
- Never use generic names like `dev` or `test` — they collide on shared infrastructure
- Never share a database between environments

---

## Level 1 — naming only

At Level 1 there is no real database. Record the names above in `.env.example` as a placeholder. No connection configuration, no migrations.

---

## Level 2 — connectivity and migrations

**Environment configuration.** Two database URLs are always defined, even locally:

```
DATABASE_URL=<driver>://user:password@host/{project}_dev
TEST_DATABASE_URL=<driver>://user:password@host/{project}_test
```

- `.env.test` sets `DATABASE_URL` to the value of `TEST_DATABASE_URL` — the app needs no test-awareness
- Production URLs are never stored in any file in the repository — injected by the deployment platform

**Startup retry.** The application must not crash if the database is unreachable at startup. Container environments start the app before the DB is ready.

- Retry on startup with exponential backoff
- Log each retry at WARN level with elapsed time
- Exit non-zero only after a configurable timeout

```
DB_CONNECT_RETRIES=5
DB_CONNECT_RETRY_INTERVAL_SECONDS=2
```

Do not rely on `depends_on` in Docker Compose — it waits for the container, not the database.

**Migration tool.** Set up the migration tool specified in the stack reference.

- Schema changes always go through migrations — never `create_all()`, `syncIndexes()`, or auto-sync on startup
- Create an initial empty migration to verify the toolchain works before writing any models
- Migration files are committed alongside the code change that requires them

**Test database lifecycle.** The test database is fully isolated from dev.

- Migrations run to `head` at the start of each test run, not on app startup
- Two acceptable isolation strategies (pick one per project): transaction rollback per test (fastest) or truncate between tests
- Never substitute SQLite for PostgreSQL or MongoDB in tests — schema dialects differ and give false confidence

---

## Level 3 — constraints and indexes

- All NOT NULL, unique, and foreign key constraints are reviewed and enforced at the database level, not only in application code
- Indexes are added for every column used in a WHERE, JOIN, or ORDER BY in production queries
- Destructive migrations (drop column, drop table, drop index) are never run automatically — present the command to the user and require manual execution after a backup
- Explicit transaction ownership: each write operation that spans multiple tables is wrapped in a transaction at the service/repository level

---

## Level 4 — production pool and observability

**Connection pooling.** Never rely on ORM or driver defaults — they are sized for demos.

| Setting | Principle |
|---|---|
| Min pool size | Handle baseline traffic from a cold start |
| Max pool size | `floor(db_max_connections / app_instances) - 2` |
| Connection recycle | Recycle after 30 minutes to prevent staleness |
| Pre-ping / validate | Test a connection before use — drops stale silently |
| Acquire timeout | Fail fast when pool is exhausted |

The `- 2` reserves connections for migrations, admin tools, and monitoring. PostgreSQL default `max_connections` is 100; with 2 instances: `floor(100 / 2) - 2 = 48` max pool per instance.

```
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=1800
DB_POOL_TIMEOUT=30
```

**Slow query logging.** Every query exceeding a configurable threshold is logged at WARN level with query and duration.

```
DB_SLOW_QUERY_MS=500
```

**Pool exhaustion.** Log pool exhaustion events at ERROR level.

**Database errors.** Never leak raw driver error messages to API responses. Catch at the service/repository layer; let the global error handler produce the 500.

**Health check.** The `/health` route must execute a real query on every call, not test TCP connectivity only:

- SQL: `SELECT 1`
- MongoDB: `db.command("ping")`
- Redis: `PING`

Return 503 if the check fails. Do not cache the result.

---

## Level 5 — isolation and secrets management

**Schema isolation.** Use a dedicated application schema rather than the database default (`public` for PostgreSQL, root for others). Grant only the minimum privileges required.

**Secrets.** Database credentials come from a secrets manager (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault) — not from environment variables injected at deploy time. Rotate credentials on a defined schedule.

**Connection security.** Require TLS or mTLS for all database connections. Restrict network access to VPC-only where possible.

**Backup and recovery.** Backups run on a tested schedule. Restoration has been demonstrated, not just assumed to work.
