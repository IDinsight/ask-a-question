---
name: api-skill-fastapi
description: >
  FastAPI implementation patterns for adding features to an existing project.
  Covers model, schema, router, service, and repository patterns with level-aware
  notes. Read alongside SKILL.md. For folder structure per level, see
  api-setup/references/stacks/fastapi.md.
---

# FastAPI Reference

Patterns for adding a feature to a FastAPI project (SQLModel, pydantic-settings, Alembic, JWT auth, loguru structured logging, rate limiting, pytest, `uv`). Match existing project conventions exactly.

Run every command with `uv run` (e.g. `uv run pytest`, `uv run alembic ...`).

**Folder structure by level** is documented in `api-setup/references/stacks/fastapi.md`. Match the existing project's level — do not reorganise the folder structure as part of a feature addition.

**Logging at Level 3+:** Use `from loguru import logger` — not stdlib `logging`. Log key transformations (state changes, business decisions) and errors with context. Request logging is handled by middleware; feature code logs business-relevant events only.

---

## Model Pattern

`SQLModel` with `table=True`. Primary key is `int | None` defaulting to `None`. Set an explicit `__tablename__`. Index foreign keys and any column used in a `WHERE` or `JOIN`.

```python
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel

class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: int | None = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="users.id", index=True)
    status: str = Field(default="pending", index=True)
    delivery_address: str = Field(max_length=500)
    total: float = Field(default=0.0, ge=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
```

**Register for Alembic in `app/models.py` after creating the file:**

```python
from app.orders.model import Order  # noqa: F401
from app.users.model import User  # noqa: F401
```

Alembic autogenerate only detects models imported in `app/models.py`. Each feature's `model.py` defines its tables; `app/models.py` re-imports them all in one place.

---

## Migrations (Alembic)

Schema changes go through Alembic — never `create_all()`, never manual `ALTER`.

```bash
uv run alembic revision --autogenerate -m "create orders table"
```

Always review the generated file under `migrations/versions/` before applying. Autogenerate can miss renames (seen as drop+add), server defaults, and enum changes.

Before applying, notify the user per SKILL.md step 2. Apply with:

```bash
uv run alembic upgrade head
```

If the migration drops a column or table, do not run it automatically — hand the user the command with a backup step.

---

## Schema Pattern

Base / Create / Update / Read separation with Pydantic v2.

```python
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

class OrderBase(BaseModel):
    customer_id: int
    delivery_address: str = Field(max_length=500)
    status: str = "pending"

class OrderCreate(OrderBase):
    pass

class OrderUpdate(BaseModel):
    delivery_address: str | None = Field(default=None, max_length=500)
    status: str | None = None

class OrderRead(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    total: float
    created_at: datetime
```

- `OrderCreate` — request body for POST.
- `OrderUpdate` — every field optional for partial updates (PATCH/PUT).
- `OrderRead` — the `response_model`; always includes `id`. Use `ConfigDict(from_attributes=True)`, not the v1 `class Config`.
- Never expose sensitive fields (passwords, tokens, internal flags) in a Read schema.

---

## Router Pattern

`APIRouter` with `prefix` and `tags`. Handlers stay thin: inject dependencies, call the service, translate `None`/`False` into the correct HTTP error.

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.utils.database import get_session
from app.dependencies.auth import get_admin_user, get_current_user
from app.users.model import User
from app.orders.schema import OrderCreate, OrderRead, OrderUpdate
from app.orders.service import (
    create_order, delete_order, get_order, list_orders, update_order,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=list[OrderRead])
def read_orders(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return list_orders(session, offset=offset, limit=limit)


@router.get("/{order_id}", response_model=OrderRead)
def read_order(
    order_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    order = get_order(session, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_new_order(
    order_in: OrderCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    order = create_order(session, order_in)
    if order is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order already exists")
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_order(
    order_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_admin_user),
):
    if not delete_order(session, order_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
```

**Pagination** — every list endpoint uses bounded `offset`/`limit` with `le`. Never return an unbounded collection, including filtered endpoints.

**Auth dependencies** (from `app/dependencies/auth.py`):
- `Depends(get_current_user)` — any authenticated user.
- `Depends(get_admin_user)` — admin only.

**Register in `app/main.py`:**
```python
from app.orders.router import router as order_router
app.include_router(order_router)
```

To rate-limit a route, add `@limiter.limit("N/minute")` and `request: Request` to the signature.

For a fixed value set on a query param, use `Literal` or an `enum` — FastAPI validates and returns 422 automatically.

---

## Service Pattern

Plain functions holding all business logic. `session: Session` is always first. Return the object on success, `None` when not found or on conflict, `bool` for deletes.

```python
from sqlmodel import Session, select

from app.orders.model import Order
from app.orders.schema import OrderCreate, OrderUpdate


def list_orders(session: Session, offset: int = 0, limit: int = 50) -> list[Order]:
    return list(session.exec(select(Order).order_by(Order.id).offset(offset).limit(limit)).all())


def get_order(session: Session, order_id: int) -> Order | None:
    return session.get(Order, order_id)


def create_order(session: Session, order_in: OrderCreate) -> Order | None:
    order = Order.model_validate(order_in)
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


def update_order(session: Session, order_id: int, order_in: OrderUpdate) -> Order | None:
    order = session.get(Order, order_id)
    if order is None:
        return None
    for field, value in order_in.model_dump(exclude_unset=True).items():
        setattr(order, field, value)
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


def delete_order(session: Session, order_id: int) -> bool:
    order = session.get(Order, order_id)
    if order is None:
        return False
    session.delete(order)
    session.commit()
    return True
```

- Use `Model.model_validate(schema_in)` — `from_orm` is deprecated in Pydantic v2.
- Use `model_dump(exclude_unset=True)` for partial updates — not `.dict()`.
- Enforce uniqueness/invariants before inserting; do not rely solely on database constraint errors.
- Never raise `HTTPException` in a service. Return `None` or `False`; the router translates these into HTTP errors.
- Bulk create/update must be a single transaction — use `session.add_all()` and commit once. Never loop over individual service calls that each commit.

---

## Repository Layer (Level 4–5 only)

**Do not add a repository.** At Levels 1–3, query logic belongs inline in the service. A repository earns its place only when a service is genuinely cluttered — long multi-clause selects, the same query reused across multiple services, or query logic obscuring business rules. A simple single-table filter used once does not qualify, even at Level 4. Always ask the user before introducing one (see SKILL.md step 6).

When justified, repository functions live in `app/<feature>/repository.py`, take `session: Session` first, and contain **no business rules**. The service imports the repository; the router never touches it.

```python
# app/orders/repository.py — only the queries that earned extraction
from sqlmodel import Session, select
from app.orders.model import Order

def get_active_for_customer(session: Session, customer_id: int) -> Order | None:
    return session.exec(
        select(Order).where(Order.customer_id == customer_id, Order.status != "cancelled")
    ).first()

def save(session: Session, order: Order) -> Order:
    session.add(order)
    session.commit()
    session.refresh(order)
    return order
```

```python
# app/orders/service.py — business logic only, delegates data access
from app.orders import repository as order_repo

def create_order(session: Session, order_in: OrderCreate) -> Order | None:
    if order_repo.get_active_for_customer(session, order_in.customer_id):
        return None  # router maps to 409
    return order_repo.save(session, Order.model_validate(order_in))
```

---

## Response and Error Conventions

Native FastAPI responses — no custom `{ success, data, error }` wrapper.

| Scenario | Pattern |
|---|---|
| Successful GET | Return object/list; FastAPI serialises via `response_model` |
| Successful POST | Return created object with `status_code=201` |
| Successful DELETE | Return nothing with `status_code=204` |
| Not found | `raise HTTPException(status_code=404, detail="X not found")` |
| Validation error | FastAPI raises 422 automatically for schema violations |
| Business conflict | `raise HTTPException(status_code=409, detail="...")` |
| Unauthorized | `raise HTTPException(status_code=401, ...)` (in dependency) |
| Forbidden | `raise HTTPException(status_code=403, ...)` (in `get_admin_user`) |

DELETE must return 204 with no body. Never return 200 with `{"message": "..."}` for a delete.

---

## Testing

`pytest` with `fastapi.testclient.TestClient`. Use the project's existing `session` and `client` fixtures. Tests must use `TEST_DATABASE_URL` — do not introduce SQLite when the project uses PostgreSQL.

Add to `tests/conftest.py` when feature tests need an authenticated user:

```python
from app.utils.security import hash_password
from app.users.model import User

@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client, session):
    def _make(email="user@test.com", password="password123", admin=False):
        user = User(email=email, hashed_password=hash_password(password), is_admin=admin)
        session.add(user)
        session.commit()
        token = client.post(
            "/auth/login", data={"username": email, "password": password}
        ).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return _make
```

### Integration tests (Level 4+)

Cover every status code the feature can return. One test per scenario — do not combine multiple assertions about different outcomes in a single test.

```python
# tests/test_orders.py

# --- Happy path ---

def test_create_order_success(client, auth_headers):
    response = client.post(
        "/orders/",
        json={"customer_id": 1, "delivery_address": "123 Main St"},
        headers=auth_headers(),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["customer_id"] == 1
    assert "id" in data


def test_list_orders_success(client, auth_headers):
    headers = auth_headers()
    client.post("/orders/", json={"customer_id": 1, "delivery_address": "A"}, headers=headers)
    client.post("/orders/", json={"customer_id": 2, "delivery_address": "B"}, headers=headers)
    response = client.get("/orders/", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_order_success(client, auth_headers):
    headers = auth_headers()
    order_id = client.post(
        "/orders/", json={"customer_id": 1, "delivery_address": "A"}, headers=headers
    ).json()["id"]
    response = client.get(f"/orders/{order_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == order_id


def test_delete_order_success(client, auth_headers):
    headers = auth_headers(admin=True)
    order_id = client.post(
        "/orders/", json={"customer_id": 1, "delivery_address": "A"}, headers=headers
    ).json()["id"]
    assert client.delete(f"/orders/{order_id}", headers=headers).status_code == 204


# --- Validation (422) ---

def test_create_order_missing_required_field(client, auth_headers):
    response = client.post("/orders/", json={}, headers=auth_headers())
    assert response.status_code == 422


# --- Business conflict (409) ---

def test_create_order_duplicate_conflict(client, auth_headers):
    headers = auth_headers()
    client.post("/orders/", json={"customer_id": 1, "delivery_address": "A"}, headers=headers)
    response = client.post(
        "/orders/", json={"customer_id": 1, "delivery_address": "B"}, headers=headers
    )
    assert response.status_code == 409


# --- Not found (404) ---

def test_get_order_not_found(client, auth_headers):
    assert client.get("/orders/999", headers=auth_headers()).status_code == 404


def test_delete_order_not_found(client, auth_headers):
    assert client.delete("/orders/999", headers=auth_headers(admin=True)).status_code == 404


# --- Auth (401) and forbidden (403) ---

def test_create_order_unauthenticated(client):
    response = client.post("/orders/", json={"customer_id": 1, "delivery_address": "A"})
    assert response.status_code == 401


def test_delete_order_forbidden_non_admin(client, auth_headers):
    assert client.delete("/orders/1", headers=auth_headers(admin=False)).status_code == 403


# --- Pagination ---

def test_list_orders_respects_limit(client, auth_headers):
    headers = auth_headers()
    for i in range(5):
        client.post("/orders/", json={"customer_id": i + 1, "delivery_address": "A"}, headers=headers)
    response = client.get("/orders/?limit=2", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 2
```

### Service unit tests (Level 3+)

Test business logic independently from HTTP. Call service functions directly with a `session` fixture — no `TestClient`, no auth headers.

```python
# tests/test_order_service.py
from app.orders.model import Order
from app.orders.schema import OrderCreate, OrderUpdate
from app.orders.service import create_order, get_order, update_order, delete_order, list_orders


def test_create_order(session):
    order = create_order(session, OrderCreate(customer_id=1, delivery_address="123 Main St"))
    assert order is not None
    assert order.id is not None
    assert order.status == "pending"


def test_create_order_conflict_returns_none(session):
    create_order(session, OrderCreate(customer_id=1, delivery_address="A"))
    result = create_order(session, OrderCreate(customer_id=1, delivery_address="B"))
    assert result is None


def test_get_order_returns_none_when_missing(session):
    assert get_order(session, 999) is None


def test_update_order_partial(session):
    order = create_order(session, OrderCreate(customer_id=1, delivery_address="Old"))
    updated = update_order(session, order.id, OrderUpdate(delivery_address="New"))
    assert updated.delivery_address == "New"
    assert updated.status == "pending"


def test_delete_order_returns_false_when_missing(session):
    assert delete_order(session, 999) is False


def test_list_orders_respects_bounds(session):
    for i in range(5):
        create_order(session, OrderCreate(customer_id=i + 1, delivery_address="A"))
    assert len(list_orders(session, offset=0, limit=2)) == 2
    assert len(list_orders(session, offset=4, limit=10)) == 1
```

Test naming: `test_<action>_<resource>_<scenario>`. Run with `uv run pytest -v`.

---

## Quality Gate

```bash
uv run pytest -v
uv run ruff check .
uv run mypy app
```

Also check before reporting done:
- `session.get(Model, id)` for primary-key lookups (uses the identity cache)
- `order_by()`, `where()`, `offset()`, `limit()` at the query level — never sort or slice in Python after fetching
- No N+1 patterns — for related data on list results use a join or `selectinload`, not a per-item helper called in a loop
- Filter on indexed columns; add `index=True` to FK columns and columns used in `WHERE`

---

## Authoritative References

- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [FastAPI — Dependency injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [FastAPI — Security tutorial](https://fastapi.tiangolo.com/tutorial/security/)
- [FastAPI — SQL databases (SQLModel)](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [SQLModel documentation](https://sqlmodel.tiangolo.com/)
- [Pydantic v2 documentation](https://docs.pydantic.dev/latest/)
- [Pydantic v2 migration guide](https://docs.pydantic.dev/latest/migration/) — `model_validate`, `model_dump`, `ConfigDict(from_attributes=True)`
- [Alembic documentation](https://alembic.sqlalchemy.org/)
- [PyJWT documentation](https://pyjwt.readthedocs.io/)
- [pwdlib documentation](https://frankie567.github.io/pwdlib/)
- [Loguru documentation](https://loguru.readthedocs.io/)
- [slowapi documentation](https://slowapi.readthedocs.io/)
- [uv documentation](https://docs.astral.sh/uv/)
