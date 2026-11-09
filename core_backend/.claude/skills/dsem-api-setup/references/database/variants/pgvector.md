---
name: database-pgvector
description: >
  pgvector extension setup by level. Loaded by api-setup alongside
  references/database/variants/postgres.md when the project needs vector
  similarity search. pgvector is always an add-on to PostgreSQL — load the
  PostgreSQL variant first. Each level builds on the previous.
---

# pgvector Reference

pgvector is a PostgreSQL extension for vector similarity search. Current version: 0.8.x. Requires PostgreSQL 13+. Load this file alongside `references/database/variants/postgres.md` — pgvector extends PostgreSQL, it does not replace it.

**When pgvector is appropriate:** semantic search, recommendation systems, RAG retrieval, image/audio similarity, classification, clustering, anomaly detection — any workload that needs nearest-neighbor search over dense or sparse embeddings stored alongside relational data.

**When pgvector is not appropriate:** primary key lookups, full-text keyword search (use `tsvector`), workloads that never query by similarity, datasets requiring more than 16,000 dimensions without binary quantization.

pgvector is relevant from Level 2 onwards. Do not introduce it at Level 1.

---

## Level 2 — extension, vector columns, and basic queries

**Installation.** The PostgreSQL Docker image does not include pgvector. Use the `pgvector/pgvector` image or install the extension in a custom Dockerfile:

```yaml
services:
  db:
    image: pgvector/pgvector:pg18
    # ... rest of config from postgres.md
```

Use the same image for the test database container.

**Extension creation.** Create the extension in a migration, not at application startup:

```python
# first Alembic migration — or prepend to the initial migration
op.execute("CREATE EXTENSION IF NOT EXISTS vector")
```

**Python dependency:**

```bash
uv add pgvector
```

**Environment variables** — add to `.env.example` alongside the PostgreSQL variables:

```
EMBEDDING_DIMENSIONS=1536
```

Set this to match the output dimensions of the embedding model in use (e.g. 1536 for `text-embedding-3-small`, 3072 for `text-embedding-3-large`, 768 for many open-source models). Reference it in models and index definitions — never hard-code dimensions.

**Model definition with SQLModel:**

```python
from pgvector.sqlalchemy import VECTOR
from sqlmodel import Field, SQLModel

class Document(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    content: str
    embedding: list[float] | None = Field(
        default=None,
        sa_type=VECTOR(settings.embedding_dimensions),
    )
```

Available column types:

| Type | Import | Use case |
|---|---|---|
| `VECTOR(n)` | `pgvector.sqlalchemy.VECTOR` | Standard full-precision vectors |
| `HALFVEC(n)` | `pgvector.sqlalchemy.HALFVEC` | Half-precision — halves storage and index memory |
| `BIT(n)` | `pgvector.sqlalchemy.BIT` | Binary vectors — smallest footprint |
| `SPARSEVEC(n)` | `pgvector.sqlalchemy.SPARSEVEC` | Sparse embeddings with many zero elements |

Default to `VECTOR`. Use `HALFVEC` when index memory is a constraint and minor precision loss is acceptable.

**Basic similarity query:**

```python
from sqlmodel import select

results = session.scalars(
    select(Document)
    .order_by(Document.embedding.cosine_distance(query_embedding))
    .limit(k)
).all()
```

Distance methods available on vector columns:

| Method | SQL operator | Use case |
|---|---|---|
| `.l2_distance(v)` | `<->` | Euclidean distance — default for unnormalized vectors |
| `.cosine_distance(v)` | `<=>` | Cosine distance — use for normalized or text embeddings |
| `.max_inner_product(v)` | `<#>` | Inner product — use for pre-normalized vectors when you want similarity, not distance |
| `.l1_distance(v)` | `<+>` | Manhattan distance |

For most text-embedding workloads, use `cosine_distance`.

**Alembic migration.** pgvector column types work with Alembic autogenerate. Ensure the migration imports `pgvector.sqlalchemy` so Alembic recognises the custom types:

```python
# migrations/env.py — add near the top
import pgvector.sqlalchemy  # noqa: F401 — registers types with SQLAlchemy
```

---

## Level 3 — indexes, filtered queries, and test isolation

Without an index, pgvector performs exact (brute-force) nearest-neighbor search — correct but slow past a few thousand rows. Add an approximate nearest-neighbor (ANN) index once the table has data.

### Index selection

| Index | Build speed | Query speed | Recall | Memory | When to use |
|---|---|---|---|---|---|
| HNSW | Slower | Faster | Higher at same speed | Higher | Default choice — better speed-recall tradeoff |
| IVFFlat | Faster | Slower | Lower without tuning | Lower | Very large datasets where build time matters |

Default to **HNSW** unless build time on a multi-million row table is prohibitive.

**HNSW index via SQLAlchemy:**

```python
from sqlalchemy import Index

embedding_index = Index(
    "ix_document_embedding_hnsw",
    Document.embedding,
    postgresql_using="hnsw",
    postgresql_with={"m": 16, "ef_construction": 64},
    postgresql_ops={"embedding": "vector_cosine_ops"},
)
```

Operator class must match the distance function used in queries:

| Distance function | Operator class |
|---|---|
| L2 (`l2_distance`) | `vector_l2_ops` |
| Cosine (`cosine_distance`) | `vector_cosine_ops` |
| Inner product (`max_inner_product`) | `vector_ip_ops` |
| L1 (`l1_distance`) | `vector_l1_ops` |

Using the wrong operator class means the index is ignored — the query falls back to sequential scan.

**HNSW parameters:**

| Parameter | Default | Effect |
|---|---|---|
| `m` | 16 | Max connections per node. Higher = better recall, more memory, slower build |
| `ef_construction` | 64 | Candidate list size during build. Higher = better recall, slower build |

Build the index after loading initial data — building on an empty table then inserting is significantly slower.

**Query-time tuning:**

```sql
SET hnsw.ef_search = 100;  -- default 40; higher = better recall, slower query
```

In application code, set per-session or per-query:

```python
session.execute(text("SET hnsw.ef_search = 100"))
```

**IVFFlat index** (when HNSW build time is unacceptable):

```python
ivfflat_index = Index(
    "ix_document_embedding_ivfflat",
    Document.embedding,
    postgresql_using="ivfflat",
    postgresql_with={"lists": 100},
    postgresql_ops={"embedding": "vector_cosine_ops"},
)
```

| Parameter | Guideline |
|---|---|
| `lists` | `rows / 1000` for < 1M rows; `√rows` for > 1M rows |
| `ivfflat.probes` | Start with `√lists`; tune for recall |

IVFFlat requires the table to have data before creating the index. Creating on an empty table produces a useless index.

**Filtered similarity queries.** Combine WHERE clauses with ORDER BY distance:

```python
results = session.scalars(
    select(Document)
    .where(Document.category_id == category_id)
    .order_by(Document.embedding.cosine_distance(query_embedding))
    .limit(k)
).all()
```

For filtered queries, add a composite index or enable iterative scan:

```sql
SET hnsw.iterative_scan = relaxed;
```

**Dimension limits with indexes:**

| Index type | `VECTOR` max dims | `HALFVEC` max dims | `BIT` max dims |
|---|---|---|---|
| HNSW | 2,000 | 4,000 | 64,000 |
| IVFFlat | 2,000 | 4,000 | 64,000 |

If your embedding model exceeds 2,000 dimensions, use `HALFVEC` for indexing or apply binary quantization.

**Test isolation.** Vector data follows the same transaction-rollback pattern from `postgres.md`. No special handling needed — pgvector columns participate in normal PostgreSQL transactions.

Ensure the test database also has the `vector` extension. The migration that creates it (`CREATE EXTENSION IF NOT EXISTS vector`) must run against the test database as part of the `run_migrations` fixture.

---

## Level 4 — production tuning and observability

**Build performance.** HNSW index builds are CPU- and memory-intensive:

```sql
SET maintenance_work_mem = '2GB';
SET max_parallel_maintenance_workers = 4;
```

Set these before building large indexes. The index build fits the graph in `maintenance_work_mem` — if the graph exceeds it, build time increases significantly.

**Half-precision indexing.** Index full-precision vectors as half-precision to halve index memory without changing the stored data:

```python
from pgvector.sqlalchemy import HALFVEC
from sqlalchemy.sql import func

halfvec_index = Index(
    "ix_document_embedding_halfvec_hnsw",
    func.cast(Document.embedding, HALFVEC(settings.embedding_dimensions)).label("embedding"),
    postgresql_using="hnsw",
    postgresql_with={"m": 16, "ef_construction": 64},
    postgresql_ops={"embedding": "halfvec_cosine_ops"},
)
```

Queries must cast to the same type for the index to be used:

```python
results = session.scalars(
    select(Document)
    .order_by(
        func.cast(Document.embedding, HALFVEC(settings.embedding_dimensions))
        .cosine_distance(query_embedding)
    )
    .limit(k)
).all()
```

**Binary quantization.** For very high-dimensional vectors or extreme memory constraints, quantize to binary and re-rank:

```sql
CREATE INDEX ON documents USING hnsw (
    (binary_quantize(embedding)::bit(1536)) bit_hamming_ops
);
```

Use a two-pass query: retrieve top-N candidates via Hamming distance on the binary index, then re-rank by exact cosine distance.

**Monitoring.** Track these metrics:

- Index size: `SELECT pg_size_pretty(pg_relation_size('ix_document_embedding_hnsw'))`
- Table size vs index size ratio — the vector index often exceeds the table
- Query latency at the application layer for similarity search endpoints
- Recall — periodically compare ANN results against exact brute-force on a sample set

**Health check.** The standard PostgreSQL health check from `postgres.md` (`SELECT 1`) covers pgvector — no separate check needed. If similarity search is a critical path, add a lightweight canary query to the health check:

```python
session.execute(text("SELECT '[1,2,3]'::vector <-> '[4,5,6]'::vector"))
```

This confirms the extension is loaded and functional.

**Connection pooling.** Same rules as `postgres.md`. No pgvector-specific pool configuration.

---

## Level 5 — hardening

**Extension versioning.** Pin the pgvector extension version in production. Upgrading requires:

```sql
ALTER EXTENSION vector UPDATE TO '0.8.5';
```

Test the upgrade against a copy of production data before applying. Index format changes between major versions may require a reindex.

**Reindexing.** After a pgvector version upgrade or significant parameter tuning, rebuild indexes:

```sql
REINDEX INDEX CONCURRENTLY ix_document_embedding_hnsw;
```

Use `CONCURRENTLY` to avoid locking the table during reindex. Schedule during low-traffic periods.

**Resource isolation.** Embedding generation and similarity search can be CPU-intensive. On shared infrastructure, consider a read replica dedicated to vector search workloads to avoid impact on transactional queries.

**Backup and recovery.** pgvector data is included in standard PostgreSQL backups — `pg_dump` and `pg_basebackup` capture vector columns and indexes. No additional backup tooling required, but verify that restore includes `CREATE EXTENSION vector` before table restoration.

---

## Authoritative References

- [pgvector — GitHub repository and documentation](https://github.com/pgvector/pgvector)
- [pgvector-python — Python client (SQLAlchemy, SQLModel, psycopg, asyncpg)](https://github.com/pgvector/pgvector-python)
- [PostgreSQL documentation — CREATE EXTENSION](https://www.postgresql.org/docs/current/sql-createextension.html)
- [HNSW algorithm paper — Malkov & Yashunin, 2018](https://arxiv.org/abs/1603.09320)
