---
name: database-redis
description: >
  Redis setup by level. Loaded by api-setup only when Redis is explicitly
  selected during pre-flight. Redis is always optional — the application must
  function correctly without it. Each level builds on the previous.
---

# Redis Reference

Redis is an optional infrastructure add-on. Load this file only when the user confirms they need it. The application must start and serve all non-cached routes correctly even if Redis is unreachable.

**When Redis is appropriate:** response caching, rate limit counters, session storage (when stateless JWT is insufficient), distributed locks, lightweight pub/sub.

**When Redis is not appropriate:** primary database, critical job queue (use a durable queue instead), substitute for database indexes.

Redis is only relevant from Level 3 onwards. Do not introduce it at Level 1 or 2.

---

## Level 3 — basic caching

**Docker Compose:**

```yaml
services:
  redis:
    image: redis:8-alpine
    command: redis-server --save 60 1 --loglevel warning
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  redis_data:
```

**Environment variables** — add to `.env.example`:

```
REDIS_URL=redis://localhost:6379/0
REDIS_TTL_SECONDS=300
REDIS_CONNECT_TIMEOUT_SECONDS=2
REDIS_SOCKET_TIMEOUT_SECONDS=1
```

**Connection** — Redis failure must not prevent app startup:

```bash
uv add redis
```

```python
# utils/cache.py
_pool = aioredis.ConnectionPool.from_url(
    settings.redis_url,
    socket_connect_timeout=settings.redis_connect_timeout_seconds,
    socket_timeout=settings.redis_socket_timeout_seconds,
    decode_responses=True,
)

def get_redis():
    return aioredis.Redis(connection_pool=_pool)
```

In the application lifespan, attempt a ping but catch and log the failure — do not raise:

```python
try:
    await get_redis().ping()
except Exception as exc:
    logger.warning("Redis unavailable at startup — caching disabled: %s", exc)
```

**Cache helper.** All cache operations must have a timeout and a fallback to the primary data source. Never let a Redis error reach the API response.

```python
async def get_cached(key: str, fetch, ttl: int | None = None):
    r = get_redis()
    ttl = ttl or settings.redis_ttl_seconds
    try:
        raw = await r.get(key)
        if raw is not None:
            return json.loads(raw)
    except RedisError as exc:
        logger.warning("Redis GET %s failed: %s", key, exc)

    value = await fetch()

    try:
        await r.setex(key, ttl, json.dumps(value))
    except RedisError as exc:
        logger.warning("Redis SET %s failed: %s", key, exc)

    return value

async def invalidate(key: str) -> None:
    try:
        await get_redis().delete(key)
    except RedisError as exc:
        logger.warning("Redis DELETE %s failed: %s", key, exc)
```

**All cache helpers are async** — any route or service calling them must be `async def`.

**Health check.** Redis unreachable returns `"degraded"`, not `"error"`. Return 200 for degraded (Redis down, primary DB up); return 503 only when the primary database is unreachable.

```python
try:
    await get_redis().ping()
    checks["redis"] = "ok"
except RedisError:
    checks["redis"] = "unreachable"
    status = "degraded"
```

**Test isolation.** Use Redis database 1 for tests and flush between runs:

```
# .env.test
REDIS_URL=redis://localhost:6379/1
```

```python
@pytest.fixture(autouse=True)
def flush_test_cache():
    yield
    redis.Redis.from_url("redis://localhost:6379/1").flushdb()
```

Alternatively, patch `get_redis` to raise `RedisError` in unit tests and verify the fallback path works without a real Redis instance.

---

## Level 4 — key hygiene and TTL policy

**Key naming convention:**

```
{resource}:{id}                   # single record
{resource}:list:{hash_of_params}  # paginated list
{user_id}:{resource}:{id}         # user-scoped record
v1:{resource}:{id}                # versioned (when format may change)
```

Rules:
- Always namespace by resource — never bare IDs
- Set TTLs based on data change frequency — do not use a single global TTL
- Invalidate on write — never serve stale data past the write event

**Cache hit/miss monitoring.** Expose hit/miss ratio from Redis `INFO STATS` in your metrics pipeline.

---

## Level 5 — hardening

- `AUTH` — set `requirepass` or use ACL rules; update the connection URL to `redis://:password@host:6379/0`
- **TLS** — use the `rediss://` scheme for encrypted connections
- **Eviction policy** — set `maxmemory-policy allkeys-lru` for a pure cache; configure `maxmemory` to a safe ceiling
- **Persistence** — disable for a pure cache (`save ""`); enable AOF if cache data must survive restarts
- **High availability** — Sentinel or Redis Cluster for production; not database numbers across environments
- **Separate instances** — one Redis instance per environment in production, not database index isolation

---

## Authoritative References

- [Redis documentation](https://redis.io/docs/latest/)
- [Redis 8.0 release notes](https://redis.io/docs/latest/operate/oss_and_stack/stack-with-enterprise/release-notes/redisce/redisos-8.0-release-notes/)
- [redis-py (Python client) documentation](https://redis.readthedocs.io/en/stable/)
