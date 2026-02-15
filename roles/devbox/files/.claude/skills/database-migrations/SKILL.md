---
name: database-migrations
description: >
  Database migration patterns across ORMs and tools. Triggers on: database migration, schema change, alembic, goose, prisma migrate, zero downtime.
---

# Database Migration Patterns

## Zero-Downtime Strategy

### Expand-Migrate-Contract

Three-phase pattern for schema changes:

**Phase 1: Expand** — Add new schema (backwards compatible)
```sql
-- Add new column (nullable, with default)
ALTER TABLE users ADD COLUMN email_v2 VARCHAR(255);
```

**Phase 2: Migrate** — Backfill data, dual-write
```sql
-- Backfill existing rows
UPDATE users SET email_v2 = email WHERE email_v2 IS NULL;

-- Application code: write to both columns
INSERT INTO users (email, email_v2) VALUES ('user@example.com', 'user@example.com');
```

**Phase 3: Contract** — Add constraints, drop old schema
```sql
-- Add constraint
ALTER TABLE users ALTER COLUMN email_v2 SET NOT NULL;

-- Drop old column
ALTER TABLE users DROP COLUMN email;

-- Rename new column
ALTER TABLE users RENAME COLUMN email_v2 TO email;
```

**Why**: Each phase is independently deployable and rollback-safe.

## Migration Tools by Ecosystem

### Go: goose

```bash
# Install
go install github.com/pressly/goose/v3/cmd/goose@latest

# Create migration
goose -dir migrations create add_users_table sql

# Run migrations
goose -dir migrations postgres "user=postgres dbname=mydb" up

# Rollback
goose -dir migrations postgres "user=postgres dbname=mydb" down
```

**Migration file** (`20240101120000_add_users_table.sql`):
```sql
-- +goose Up
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL
);

-- +goose Down
DROP TABLE users;
```

### Go: golang-migrate

```bash
# Install
go install -tags 'postgres' github.com/golang-migrate/migrate/v4/cmd/migrate@latest

# Create migration
migrate create -ext sql -dir migrations -seq add_users_table

# Run migrations
migrate -path migrations -database "postgres://user:pass@localhost/mydb?sslmode=disable" up

# Rollback
migrate -path migrations -database "postgres://user:pass@localhost/mydb?sslmode=disable" down 1
```

### Python: Alembic (SQLAlchemy)

```bash
# Install
pip install alembic

# Initialize
alembic init migrations

# Create migration (auto-generate from models)
alembic revision --autogenerate -m "add users table"

# Run migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

**Migration file**:
```python
def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False)
    )

def downgrade():
    op.drop_table('users')
```

### Python: Django Migrations

```bash
# Create migration
python manage.py makemigrations

# Run migrations
python manage.py migrate

# Rollback
python manage.py migrate myapp 0001  # Migrate to specific version
```

**Migration file**:
```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=255, null=True),
        ),
    ]
```

### TypeScript: Prisma Migrate

```bash
# Create migration
npx prisma migrate dev --name add_users_table

# Apply migrations (production)
npx prisma migrate deploy

# Reset database (development only)
npx prisma migrate reset
```

**Schema file** (`schema.prisma`):
```prisma
model User {
  id    Int    @id @default(autoincrement())
  email String @unique
}
```

### TypeScript: Drizzle Kit

```bash
# Generate migration from schema
npx drizzle-kit generate:pg

# Run migrations
npx drizzle-kit migrate

# Drop migration
npx drizzle-kit drop
```

**Schema file** (`schema.ts`):
```typescript
import { pgTable, serial, varchar } from 'drizzle-orm/pg-core';

export const users = pgTable('users', {
  id: serial('id').primaryKey(),
  email: varchar('email', { length: 255 }).notNull(),
});
```

## Common Patterns

### Add Column (Safe)

**Phase 1**: Add nullable column
```sql
ALTER TABLE users ADD COLUMN phone VARCHAR(20);
```

**Phase 2**: Backfill data
```sql
UPDATE users SET phone = '000-000-0000' WHERE phone IS NULL;
```

**Phase 3**: Add NOT NULL constraint
```sql
ALTER TABLE users ALTER COLUMN phone SET NOT NULL;
```

**Why safe**: Existing queries don't break (new column ignored until app updated).

### Rename Column (Safe)

**Phase 1**: Add new column, dual-write
```sql
ALTER TABLE users ADD COLUMN email_address VARCHAR(255);
UPDATE users SET email_address = email WHERE email_address IS NULL;
```

**Phase 2**: Update application code (read from `email_address`, write to both)
```python
# Old code
user.email = "new@example.com"

# Phase 2 code (dual-write)
user.email = "new@example.com"
user.email_address = "new@example.com"
```

**Phase 3**: Update application code (read from `email_address` only)
```python
# Phase 3 code
user.email_address = "new@example.com"
```

**Phase 4**: Drop old column
```sql
ALTER TABLE users DROP COLUMN email;
```

**Why safe**: No downtime, rollback at any phase.

### Add Index (Safe in PostgreSQL)

**Without CONCURRENTLY** (locks table):
```sql
CREATE INDEX idx_users_email ON users(email);  -- Table locked during creation
```

**With CONCURRENTLY** (no lock):
```sql
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);  -- No table lock
```

**Why**: `CONCURRENTLY` allows reads/writes during index creation (slower, but no downtime).

**Caveat**: Not transactional — if fails, leaves invalid index (must drop manually).

### Drop Column (Safe)

**Phase 1**: Remove column from application code (stop reading/writing)
```python
# Old code
user = User(name="Alice", email="alice@example.com", age=30)

# Phase 1 code (stop using age)
user = User(name="Alice", email="alice@example.com")
```

**Phase 2**: Deploy application (verify no errors)

**Phase 3**: Drop column
```sql
ALTER TABLE users DROP COLUMN age;
```

**Why safe**: Application doesn't reference column before drop (no errors on rollback).

## Dangerous Operations

### ALTER TABLE on Large Tables

**Problem**: Locks table during operation (no reads/writes).

```sql
-- Dangerous: locks table for minutes/hours
ALTER TABLE users ALTER COLUMN email TYPE TEXT;
```

**Solution**: Use shadow table pattern
```sql
-- 1. Create new table with desired schema
CREATE TABLE users_new (LIKE users INCLUDING ALL);
ALTER TABLE users_new ALTER COLUMN email TYPE TEXT;

-- 2. Copy data in batches (no lock)
INSERT INTO users_new SELECT * FROM users WHERE id BETWEEN 1 AND 100000;
-- Repeat for all rows

-- 3. Swap tables (brief lock)
BEGIN;
ALTER TABLE users RENAME TO users_old;
ALTER TABLE users_new RENAME TO users;
COMMIT;

-- 4. Drop old table
DROP TABLE users_old;
```

### Adding NOT NULL Without Default

**Dangerous**:
```sql
ALTER TABLE users ADD COLUMN phone VARCHAR(20) NOT NULL;  -- Fails if table not empty
```

**Safe**:
```sql
-- 1. Add nullable column with default
ALTER TABLE users ADD COLUMN phone VARCHAR(20) DEFAULT '000-000-0000';

-- 2. Backfill existing rows
UPDATE users SET phone = '000-000-0000' WHERE phone IS NULL;

-- 3. Add NOT NULL constraint
ALTER TABLE users ALTER COLUMN phone SET NOT NULL;

-- 4. Remove default (if not needed for future inserts)
ALTER TABLE users ALTER COLUMN phone DROP DEFAULT;
```

### Renaming Column Without Migration Period

**Dangerous**:
```sql
ALTER TABLE users RENAME COLUMN email TO email_address;  -- Breaks running application
```

**Safe**: Use expand-migrate-contract (see "Rename Column" above).

## Backfill Strategies

### Batch Processing

Large table → process in chunks (avoid long locks, memory issues).

```python
# Alembic migration
def upgrade():
    connection = op.get_bind()
    batch_size = 10000
    offset = 0

    while True:
        result = connection.execute(f"""
            UPDATE users
            SET email_v2 = email
            WHERE id IN (
                SELECT id FROM users
                WHERE email_v2 IS NULL
                LIMIT {batch_size}
            )
        """)

        if result.rowcount == 0:
            break

        offset += batch_size
```

**Why**: Commits in batches (avoids transaction timeout, allows progress monitoring).

### Dual-Write Period

Write to both old and new columns during migration.

```python
# Phase 1: Add new column
ALTER TABLE users ADD COLUMN status_v2 VARCHAR(20);

# Phase 2: Application writes to both
user.status = "active"
user.status_v2 = "active"  # Dual-write

# Phase 3: Backfill old rows
UPDATE users SET status_v2 = status WHERE status_v2 IS NULL;

# Phase 4: Application reads from new column only
if user.status_v2 == "active":
    ...

# Phase 5: Drop old column
ALTER TABLE users DROP COLUMN status;
```

### Background Jobs

Long-running backfill → run outside migration (avoid blocking deployment).

```python
# Migration: only add column
def upgrade():
    op.add_column('users', sa.Column('email_v2', sa.String(255)))

# Separate background job
def backfill_email_v2():
    batch_size = 10000
    while True:
        users = session.query(User).filter(User.email_v2.is_(None)).limit(batch_size).all()
        if not users:
            break

        for user in users:
            user.email_v2 = user.email
        session.commit()
```

**Why**: Deployment not blocked by backfill (can take hours/days for large tables).

## Testing Migrations

### Test Against Production Schema

```bash
# 1. Dump production schema (no data)
pg_dump --schema-only production_db > schema.sql

# 2. Restore to test database
psql test_db < schema.sql

# 3. Run migration
alembic upgrade head

# 4. Verify schema
pg_dump --schema-only test_db > schema_after.sql
diff schema.sql schema_after.sql
```

### Test Up and Down Migrations

```bash
# Test up migration
alembic upgrade head

# Test down migration (rollback)
alembic downgrade -1

# Verify idempotency (run twice)
alembic upgrade head
alembic downgrade -1
alembic upgrade head  # Should succeed
```

### Verify Data Integrity

```python
# Test migration with sample data
def test_migration():
    # 1. Insert test data
    user = User(email="test@example.com")
    session.add(user)
    session.commit()

    # 2. Run migration
    alembic.upgrade("head")

    # 3. Verify data preserved
    user = session.query(User).filter_by(email="test@example.com").first()
    assert user is not None
    assert user.email == "test@example.com"
```

## Best Practises

1. **Backwards compatible**: New migrations should not break running application
2. **Small changesets**: One logical change per migration (easier rollback)
3. **Test rollback**: Every migration should have a `down` function
4. **Separate data and schema**: Schema changes in migration, data backfill in background job
5. **Version control**: Migrations in git (never edit existing migrations)
6. **Production testing**: Test on copy of production schema before deploying
7. **Monitor**: Log migration start/end, track duration, alert on failures
