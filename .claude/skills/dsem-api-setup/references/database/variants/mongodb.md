---
name: database-mongodb
description: >
  MongoDB-specific setup by level. Loaded by api-setup alongside
  references/database/database.md when the primary database is MongoDB.
  Each level builds on the previous. Apply only what the target level requires.
---

# MongoDB Reference

MongoDB 8 is the current stable release (8.3 as of mid-2026). MongoDB 7.0 remains supported. Read alongside `references/database/database.md`.

> **Driver note:** Motor is deprecated as of May 2025. Use the native PyMongo Async API (`AsyncMongoClient` from `pymongo`). Beanie already uses `AsyncMongoClient` under the hood — no breaking change if you only interact via Beanie, but update any direct Motor imports.

---

## Level 1 — naming only

MongoDB creates databases on first write — no creation command needed. Document the names in `.env.example` as placeholders:

```
MONGODB_DB_NAME={project_name}_dev
TEST_MONGODB_DB_NAME={project_name}_test
```

---

## Level 2 — connectivity and driver setup

**Docker Compose:**

```yaml
services:
  db:
    image: mongo:8
    environment:
      MONGO_INITDB_ROOT_USERNAME: root
      MONGO_INITDB_ROOT_PASSWORD: root
    volumes:
      - mongo_data:/data/db
    ports:
      - "27017:27017"
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 5s
      timeout: 5s
      retries: 5

  db-test:
    image: mongo:8
    environment:
      MONGO_INITDB_ROOT_USERNAME: root
      MONGO_INITDB_ROOT_PASSWORD: root
    ports:
      - "27018:27017"
    # no volume — ephemeral

volumes:
  mongo_data:
```

**Environment variables** — add to `.env.example`:

```
MONGODB_URL=mongodb://root:root@localhost:27017
MONGODB_DB_NAME={project_name}_dev
TEST_MONGODB_URL=mongodb://root:root@localhost:27018
TEST_MONGODB_DB_NAME={project_name}_test
DB_CONNECT_RETRIES=5
DB_CONNECT_RETRY_INTERVAL_SECONDS=2
```

**Driver.** Use PyMongo Async + Beanie (ODM) for Python. Motor is deprecated (EOL May 2026) — `AsyncMongoClient` is the official replacement and Beanie already uses it under the hood:

```bash
uv add pymongo beanie
```

**Connection with startup retry:**

```python
# utils/database.py
from pymongo import AsyncMongoClient

async def connect_with_retry(retries: int = 5, interval: float = 2.0):
    for attempt in range(1, retries + 1):
        try:
            client = AsyncMongoClient(settings.mongodb_url)
            await client.admin.command("ping")
            await init_beanie(
                database=client[settings.mongodb_db_name],
                document_models=all_document_models,
            )
            return
        except Exception as exc:
            logger.warning("MongoDB not ready (%d/%d): %s", attempt, retries, exc)
            if attempt == retries:
                raise
            await asyncio.sleep(interval * attempt)
```

Wire into the application lifespan — connect on startup, close on shutdown.

**Document model pattern:**

```python
class Order(Document):
    customer_id: Indexed(str)
    status: Indexed(str) = "pending"

    class Settings:
        name = "orders"
        indexes = [[("customer_id", 1), ("status", 1)]]
```

Register all document models in a list passed to `init_beanie`.

**Schema migrations.** MongoDB has no Alembic equivalent:

- Additive changes (new optional fields, new collections): safe to deploy with no script
- Renames or removals: write a migration script in `migrations/`; run manually before deploying
- Never use `auto_create_indexes=True` in production

---

## Level 3 — indexes and test isolation

**Indexes.** Review all `Indexed()` fields and compound `Settings.indexes` entries. Ensure indexes exist for every field used in queries. Dropping an index on a large collection takes time — schedule in a maintenance window.

**Test isolation** — collection truncation per test:

```python
# tests/conftest.py
@pytest.fixture(scope="session", autouse=True)
async def init_test_db():
    from pymongo import AsyncMongoClient
    client = AsyncMongoClient(settings.test_mongodb_url)
    await init_beanie(
        database=client[settings.test_mongodb_db_name],
        document_models=all_document_models,
    )
    yield
    await client.drop_database(settings.test_mongodb_db_name)
    client.close()

@pytest.fixture(autouse=True)
async def clean_collections():
    yield
    from pymongo import AsyncMongoClient
    client = AsyncMongoClient(settings.test_mongodb_url)
    db = client[settings.test_mongodb_db_name]
    for name in await db.list_collection_names():
        await db[name].delete_many({})
    client.close()
```

MongoDB does not support cross-document transaction rollback without a replica set. Use collection truncation unless you configure a local replica set.

---

## Level 4 — production pool and observability

**Connection pool configuration:**

```
DB_MIN_POOL_SIZE=5
DB_MAX_POOL_SIZE=20
DB_CONNECT_TIMEOUT_MS=5000
DB_SERVER_SELECTION_TIMEOUT_MS=5000
DB_SLOW_QUERY_MS=500
```

Add to `.env.example`. Pass to `AsyncMongoClient`:

```python
from pymongo import AsyncMongoClient

client = AsyncMongoClient(
    settings.mongodb_url,
    minPoolSize=settings.db_min_pool_size,
    maxPoolSize=settings.db_max_pool_size,
    connectTimeoutMS=settings.db_connect_timeout_ms,
    serverSelectionTimeoutMS=settings.db_server_selection_timeout_ms,
)
```

**Slow query detection.** MongoDB's `explain()` and server-side slow query log (`slowOpThresholdMs` in `mongod.conf`) are the primary tools. Log warnings in the application for operations that exceed `DB_SLOW_QUERY_MS` where measurable.

**Health check:**

```python
@app.get("/health")
async def health():
    try:
        await get_client().admin.command("ping")
        db_status = "ok"
    except Exception:
        db_status = "unreachable"
    ok = db_status == "ok"
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ok" if ok else "degraded", "checks": {"database": db_status}},
    )
```

---

## Level 5 — auth, TLS, and least privilege

**Authentication.** Create a dedicated application user with `readWrite` on the app database only — not the admin database:

```javascript
// run in mongosh as admin
db.createUser({
  user: "{app_user}",
  pwd: "{strong_password}",
  roles: [{ role: "readWrite", db: "{project_name}_prod" }]
})
```

Update the connection string to use the app user instead of root.

**TLS.** Require TLS for all connections:

```
MONGODB_URL=mongodb://{user}:{pass}@host:27017/?tls=true&tlsCAFile=/path/to/ca.pem
```

**Replica set.** Use a replica set connection string in production — not a single-node URL. Single-node deployments have no automatic failover.

**Backups.** Automated backups via `mongodump` or Atlas Backup on a daily schedule, with a tested restoration procedure.

---

## Authoritative References

- [MongoDB documentation](https://www.mongodb.com/docs/manual/)
- [MongoDB release notes](https://www.mongodb.com/docs/manual/release-notes/)
- [PyMongo AsyncMongoClient](https://pymongo.readthedocs.io/en/latest/api/pymongo/asynchronous/mongo_client.html)
- [Motor deprecation — migration to PyMongo Async](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/)
- [Beanie ODM documentation](https://beanie-odm.dev/)
- [Motor documentation (deprecated, EOL May 2026)](https://motor.readthedocs.io/en/stable/)
