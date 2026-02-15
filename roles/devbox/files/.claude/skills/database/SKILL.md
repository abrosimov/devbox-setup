---
name: database
description: >
  Database patterns for Go and Python. Covers sqlx, pgx, SQLAlchemy, connection pooling,
  transactions, migrations, repository pattern, and testing with databases.
  Triggers on: database, SQL, query, sqlx, pgx, SQLAlchemy, migration, transaction,
  repository, connection pool, ORM, schema, index.
---

# Database Patterns

Database interaction patterns for Go and Python.

---

## Go Database Patterns

### Library Choice

| Library | When | Why |
|---------|------|-----|
| **pgx** | PostgreSQL only | Best PostgreSQL driver, native types, COPY support |
| **sqlx** | Multiple databases | Extends `database/sql`, struct scanning, named params |
| **database/sql** | Simple needs | Stdlib, no dependency, sufficient for basic CRUD |

### Connection Pool Configuration

```go
db, err := pgxpool.New(ctx, connString)
if err != nil {
    return fmt.Errorf("creating pool: %w", err)
}

config := db.Config()
config.MaxConns = 25                        // Max total connections
config.MinConns = 5                         // Keep warm connections
config.MaxConnLifetime = 30 * time.Minute   // Rotate connections
config.MaxConnIdleTime = 5 * time.Minute    // Close idle connections
config.HealthCheckPeriod = 30 * time.Second
```

### Repository Pattern

```go
type UserRepository struct {
    db *pgxpool.Pool
}

func NewUserRepository(db *pgxpool.Pool) *UserRepository {
    return &UserRepository{db: db}
}

func (r *UserRepository) GetByID(ctx context.Context, id uuid.UUID) (*User, error) {
    var user User
    err := r.db.QueryRow(ctx,
        `SELECT id, email, name, created_at FROM users WHERE id = $1`, id,
    ).Scan(&user.ID, &user.Email, &user.Name, &user.CreatedAt)
    if errors.Is(err, pgx.ErrNoRows) {
        return nil, ErrNotFound
    }
    if err != nil {
        return nil, fmt.Errorf("querying user %s: %w", id, err)
    }
    return &user, nil
}
```

### Transactions

```go
func (r *OrderRepository) CreateWithItems(ctx context.Context, order Order, items []Item) error {
    tx, err := r.db.Begin(ctx)
    if err != nil {
        return fmt.Errorf("beginning transaction: %w", err)
    }
    defer tx.Rollback(ctx) // No-op if committed

    _, err = tx.Exec(ctx, `INSERT INTO orders (id, user_id) VALUES ($1, $2)`, order.ID, order.UserID)
    if err != nil {
        return fmt.Errorf("inserting order: %w", err)
    }

    for _, item := range items {
        _, err = tx.Exec(ctx, `INSERT INTO order_items (order_id, product_id, qty) VALUES ($1, $2, $3)`,
            order.ID, item.ProductID, item.Quantity)
        if err != nil {
            return fmt.Errorf("inserting item: %w", err)
        }
    }

    if err := tx.Commit(ctx); err != nil {
        return fmt.Errorf("committing transaction: %w", err)
    }
    return nil
}
```

---

## Python Database Patterns

### SQLAlchemy (ORM)

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

### Repository Pattern (Python)

```python
class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self._session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self._session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

    def create(self, user: User) -> User:
        self._session.add(user)
        self._session.flush()  # Get ID without committing
        return user
```

### Async (asyncpg / async SQLAlchemy)

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine("postgresql+asyncpg://...", pool_size=20, max_overflow=10)

async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
```

---

## Migration Patterns

| Tool | Language | Notes |
|------|----------|-------|
| **goose** | Go | SQL or Go migrations, up/down support |
| **golang-migrate** | Go | SQL migrations, multiple database drivers |
| **alembic** | Python | SQLAlchemy integration, auto-generation |
| **Django migrations** | Python | Built-in, model-driven |
| **dbmate** | Any | Language-agnostic, SQL-only |

**Rules:**
- Every schema change gets a migration (never modify DB manually)
- Migrations must be backward-compatible (expand before code, contract after)
- Always test migrations against production-like data volume
- No stored procedures, no triggers — all logic in application code

### Migration Naming Convention

Migrations follow the expand-and-contract pattern with a standard naming scheme:

```
{global_seq}_{scope}_{phase}_{description}.sql
```

| Component | Description | Example |
|-----------|-------------|---------|
| `global_seq` | 3-digit auto-incrementing across ALL migrations | `001`, `002` |
| `scope` | Jira ticket or short feature name | `PROJ-123`, `user_auth` |
| `phase` | Migration phase | `expand`, `backfill`, `validate`, `contract` |
| `description` | snake_case action | `add_currency_column` |

### Migration Phases

| Phase | What It Does | Safe to Run | Rollback |
|-------|-------------|-------------|----------|
| **expand** | ADD column, CREATE table, CREATE index CONCURRENTLY | Before code deploy | DROP column/table |
| **backfill** | Populate new columns from existing data | Before code deploy | Idempotent re-run |
| **validate** | Add NOT NULL, constraints, verify data | Before code deploy | DROP constraint |
| **contract** | DROP old column, DROP old table, rename | **After code deploy** | Restore from backup |

**Deploy gate**: There is always a code deployment between `validate` and `contract` phases.

### Working with schema_design.md

When a `schema_design.md` exists in the project directory (`{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/`):

1. **Read it first** — It contains the database designer's approved schema, migration phases, and deploy ordering
2. **Follow the deploy gates** — Never run contract migrations before the application code is deployed
3. **Match migration filenames** — Use the naming convention from the schema design
4. **Respect the phase ordering** — expand → backfill → validate → [CODE DEPLOY] → contract

---

## Testing with Databases

### testcontainers (Both Languages)

```go
// Go
container, err := postgres.Run(ctx, "postgres:16-alpine")
connStr, _ := container.ConnectionString(ctx)
// Use connStr for test database
defer container.Terminate(ctx)
```

```python
# Python
from testcontainers.postgres import PostgresContainer

with PostgresContainer("postgres:16-alpine") as pg:
    engine = create_engine(pg.get_connection_url())
    # Run tests against real PostgreSQL
```

### Test Transaction Pattern

```python
@pytest.fixture
def db_session(engine):
    """Each test runs in a transaction that gets rolled back."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()
```

---

## Common Pitfalls

| Pitfall | Problem | Fix |
|---------|---------|-----|
| N+1 queries | O(N) queries instead of O(1) | JOIN or batch fetch |
| Missing indexes | Full table scan | Add index on WHERE/JOIN columns |
| Connection leaks | Pool exhaustion | Always close/return connections |
| Long transactions | Lock contention | Minimise transaction scope |
| String concatenation for SQL | SQL injection | Parameterised queries always |
| ORM for bulk operations | Slow, memory-heavy | Raw SQL for bulk insert/update |

> **See also:** `transaction-safety` for isolation levels, savepoints, optimistic locking, and the cardinal rule of no network calls inside transactions. `distributed-transactions` for outbox pattern, idempotent consumers, and saga patterns.
