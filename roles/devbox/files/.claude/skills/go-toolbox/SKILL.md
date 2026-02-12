---
name: go-toolbox
description: >
  Recommended Go libraries and their patterns. Covers go-provider (DI/service
  locator), go-devtools (debug/type utilities), sqlc (SQL code generation),
  caarlos0/env (environment config), and stretchr/testify (assertions).
  Use when choosing libraries, setting up DI, generating database code, loading
  config from environment, or writing assertions.
  Triggers on: go-provider, service locator, dependency injection, go-devtools,
  sqlc, sql generation, caarlos0/env, environment variables, config loading,
  testify, assertion, recommended library, which library.
---

# Go Toolbox Reference

Recommended libraries and their idiomatic usage patterns.

---

## Decision Table: Problem → Library

| Problem | Library | Import |
|---------|---------|--------|
| Dependency injection / service locator | go-provider | `github.com/abrosimov/go-provider` |
| Debug utilities, type reflection | go-devtools | `github.com/abrosimov/go-devtools` |
| Type-safe DB queries from SQL | sqlc | `github.com/sqlc-dev/sqlc` (tool) |
| Environment variable config | caarlos0/env | `github.com/caarlos0/env/v11` |
| Test assertions & suites | testify | `github.com/stretchr/testify` |
| CLI flag parsing | kong | `github.com/alecthomas/kong` |

**See**: `go-cli` skill for Kong patterns. `go-testing` skill for testify patterns.

---

## DI / Service Locator — `abrosimov/go-provider`

Type-safe dependency injection using Go generics. Global singleton registry with lazy initialisation.

### Setup

```go
import "github.com/abrosimov/go-provider"

// Call once at startup, before goroutines
provider.Init(provider.Config{
    Logger:             logger,
    MailboxOutQueueCap: 10,
})
```

### Register & Resolve

```go
// Register a singleton (lazy — factory runs on first ValueOf)
provider.Provide(func() (*Database, error) {
    return sql.Open("postgres", connStr)
})

// Resolve (thread-safe, cached after first call)
db, err := provider.ValueOf[Database]()
```

### Multi-Value (Named Instances)

```go
provider.ProvideMultiValue(
    provider.NewDefaultValueCreator("stripe", func() (*HTTPClient, error) {
        return &HTTPClient{BaseURL: "https://api.stripe.com"}, nil
    }),
    provider.NewDefaultValueCreator("github", func() (*HTTPClient, error) {
        return &HTTPClient{BaseURL: "https://api.github.com"}, nil
    }),
)

client, err := provider.MultiValueOf[HTTPClient]("stripe")
```

### Guaranteed API (Error-Free)

For providers that cannot fail. Type must implement `IGuaranteeSafeBehaviour()`.

```go
type AppName struct{ Value string }
func (*AppName) IGuaranteeSafeBehaviour() {}

provider.ProvideGuaranteed[AppName, *AppName](func() *AppName {
    return &AppName{Value: "myapp"}
})

name := provider.GuaranteedValueOf[AppName, *AppName]()
```

### Change Notifications

Type must embed `*provider.ChangesNotifier`. Subscribers receive via channel.

```go
type AppConfig struct {
    *provider.ChangesNotifier
    Debug bool
}

// Subscribe: sub := provider.SubscribeTo[AppConfig]()
// Listen:    for range sub.GetChannel() { cfg, _ := provider.ValueOf[AppConfig]() }
```

### Futures (Async Resolution)

```go
future := provider.FutureOf[Config](logger)
cfg, err := future.Get(ctx)          // blocks until Provide[Config] is called
err := future.WaitFor(5 * time.Second) // or with timeout
```

### Introspection

```go
provider.DoesProvide[Config]()                             // bool
provider.DoesProvideMultiValue[HTTPClient]()                // bool
provider.DoesProvideNamedMultiValue[HTTPClient]("stripe")   // bool
provider.GetProvidedTypes()                                 // []string
```

### Testing

```go
func TestSomething(t *testing.T) {
    provider.ResetRegistry()  // clean state between tests
    provider.Provide(func() (*Config, error) {
        return &Config{Debug: true}, nil
    })
    // ...
}
```

### Error Sentinels

| Error | Cause |
|-------|-------|
| `ErrNoProviderForType` | `ValueOf` before `Provide` |
| `ErrProviderAlreadyExists` | Duplicate `Provide` |
| `ErrInterfaceTypeIsNotAllowed` | Interface types forbidden |
| `ErrDuplicateNamedValue` | Multi-value name collision |
| `ErrFutureWaitTimedOut` | Future exceeded timeout |
| `ErrValueIsNilAndNoError` | Provider returned nil without error |

### Key Constraints

- Interface types cannot be provided (generics enforce this)
- `Init()` must be called before any goroutines or provider operations
- Thread-safe via mutexes and `sync.Map`

---

## Dev Utilities — `abrosimov/go-devtools`

Small utility collection. Packages use `x` suffix to avoid stdlib name collisions.

### debugx — Runtime Introspection

```go
import "github.com/abrosimov/go-devtools/debugx"

name := debugx.GetCurrentFunc()   // "pkg.FuncName:42"
caller := debugx.GetCalleeFunc()  // caller's function name + line
trace := debugx.GetStackTrace()   // formatted goroutine stack trace
```

### typesx — Type Reflection

```go
import "github.com/abrosimov/go-devtools/typesx"

typesx.IsInterface[MyInterface]()                  // true
typesx.HasPtrFieldOfType[MyStruct, Database]()     // true if *Database field exists
typesx.GetTypeFQN[MyStruct]()                      // "github.com/me/pkg.MyStruct"
```

### typesx.TypedSyncMap — Generic sync.Map

```go
m := typesx.NewTypedSyncMap[string, *Connection]()

m.Store("db1", conn)
conn, ok := m.Load("db1")
m.Delete("db1")
m.Range(func(key string, value *Connection) bool {
    return true // continue
})
m.Clear()
```

### bgworker — Background Jobs

```go
import "github.com/abrosimov/go-devtools/bgworker"

// Implement the Job interface
type CleanupJob struct{}
func (j *CleanupJob) Name() string                { return "cleanup" }
func (j *CleanupJob) Run(ctx context.Context)     { /* ... */ }
func (j *CleanupJob) RepeatEvery() time.Duration  { return 5 * time.Minute }
func (j *CleanupJob) Ctx() context.Context        { return context.Background() }

runner := bgworker.NewJobsRunner()
runner.AddJob(&CleanupJob{})
runner.Run(ctx)   // starts goroutine, checks jobs every second
runner.Stop(ctx)  // signals shutdown
```

---

## Database — `sqlc`

Write SQL, generate type-safe Go code. Supports PostgreSQL, MySQL, SQLite.

### Workflow

```
1. Write schema.sql       → CREATE TABLE ...
2. Write query.sql         → annotated SQL queries
3. Run: sqlc generate      → produces Go code
4. Use generated code      → queries.GetUser(ctx, id)
```

### Configuration (sqlc.yaml v2)

```yaml
version: "2"
sql:
  - engine: "postgresql"
    schema: "db/schema.sql"
    queries: "db/queries/"
    gen:
      go:
        package: "db"
        out: "internal/db"
        sql_package: "pgx/v5"
        emit_json_tags: true
        emit_interface: true
        emit_empty_slices: true
```

Key `gen.go` options:

| Option | Default | Purpose |
|--------|---------|---------|
| `sql_package` | `database/sql` | Driver: `pgx/v5`, `pgx/v4`, `database/sql` |
| `emit_interface` | false | Generate `Querier` interface (for mocking) |
| `emit_empty_slices` | false | Return `[]T{}` not `nil` for `:many` |
| `emit_json_tags` | false | JSON tags on model structs |

### Query Annotations

```sql
-- name: GetUser :one
SELECT * FROM users WHERE id = $1 LIMIT 1;

-- name: ListUsers :many
SELECT * FROM users ORDER BY name;

-- name: CreateUser :one
INSERT INTO users (name, email) VALUES ($1, $2) RETURNING *;

-- name: UpdateUser :exec
UPDATE users SET name = $2 WHERE id = $1;
```

| Annotation | Returns | Use Case |
|-----------|---------|----------|
| `:one` | `(Model, error)` | Single row |
| `:many` | `([]Model, error)` | Multiple rows |
| `:exec` | `error` | No return value |
| `:execrows` | `(int64, error)` | Affected row count |
| `:copyfrom` | `(int64, error)` | Bulk insert (COPY) |
| `:batchone` / `:batchmany` / `:batchexec` | Batch | pgx batch operations |

### Generated Usage

```go
conn, _ := pgx.Connect(ctx, connStr)
queries := db.New(conn)

user, err := queries.GetUser(ctx, userID)
users, err := queries.ListUsers(ctx)
created, err := queries.CreateUser(ctx, db.CreateUserParams{
    Name:  "Alice",
    Email: "alice@example.com",
})
```

### Transactions

```go
tx, err := conn.Begin(ctx)
if err != nil {
    return fmt.Errorf("begin tx: %w", err)
}
defer tx.Rollback(ctx)

qtx := queries.WithTx(tx)
user, err := qtx.CreateUser(ctx, params)
if err != nil {
    return fmt.Errorf("create user: %w", err)
}

return tx.Commit(ctx)
```

### Advanced Query Features

```sql
-- Named parameters: sqlc.arg(name)
-- name: UpdateUserName :exec
UPDATE users SET name = sqlc.arg(new_name) WHERE id = sqlc.arg(user_id);

-- Nullable parameters: sqlc.narg() → generates sql.NullString
-- name: PatchUser :exec
UPDATE users SET name = coalesce(sqlc.narg('name'), name) WHERE id = sqlc.arg('id');

-- Struct embedding for JOINs: sqlc.embed()
-- name: UserWithOrders :many
SELECT sqlc.embed(users), sqlc.embed(orders)
FROM users JOIN orders ON orders.user_id = users.id;
```

### Type Overrides (in sqlc.yaml under `gen.go`)

```yaml
overrides:
  - db_type: "uuid"
    go_type: { import: "github.com/google/uuid", type: "UUID" }
  - column: "users.bio"
    go_type: "string"
```

### Best Practices

- Use `pgx/v5` for PostgreSQL
- Set `emit_interface: true` for testability (mock the Querier)
- Set `emit_empty_slices: true` to avoid nil slices in JSON
- Run `sqlc generate` in CI, verify with `git diff --exit-code`
- Use `sqlc vet` to lint queries

---

## Environment Config — `caarlos0/env/v11`

Declarative environment variable loading with struct tags.

### Core API

```go
import "github.com/caarlos0/env/v11"

// Generic — preferred (no pointer, no pre-declaration)
cfg, err := env.ParseAs[Config]()

// With options
cfg, err := env.ParseAsWithOptions[Config](env.Options{
    Prefix: "APP_",
})

// Panic on error (init-time only)
cfg := env.Must(env.ParseAs[Config]())
```

### Struct Tags

```go
type Config struct {
    Host    string        `env:"HOST"                   envDefault:"localhost"`
    Port    int           `env:"PORT"                   envDefault:"8080"`
    Secret  string        `env:"SECRET,required"`
    Name    string        `env:"NAME,notEmpty"`
    DBUrl   string        `env:"DB_URL,expand"`         // expands ${HOST}:${PORT}
    Cert    string        `env:"TLS_CERT,file"`         // reads file at path
    Token   string        `env:"TOKEN,unset"`           // clears env after read
    DB      DatabaseConfig `envPrefix:"DB_"`             // nested struct prefix
}

type DatabaseConfig struct {
    Host string `env:"HOST" envDefault:"localhost"`
    Port int    `env:"PORT" envDefault:"5432"`
}
// Resolves to DB_HOST, DB_PORT
```

- **`env:"VAR"`** — bind to env var
- **`envDefault:"val"`** — default if unset
- **`envPrefix:"PFX_"`** — prefix nested struct fields
- **`envSeparator:";"`** — slice delimiter (default `,`)
- **`,required`** — error if missing
- **`,notEmpty`** — error if empty string
- **`,expand`** — expand `${VAR}` references
- **`,file`** — read file content from path
- **`,unset`** — clear env var after read

### Options

```go
env.Options{
    Environment:           map[string]string{...},  // override os.Environ (testing)
    Prefix:                "APP_",                   // global prefix
    RequiredIfNoDef:       true,                     // require all unless envDefault set
    UseFieldNameByDefault: true,                     // HOST from struct field Host
    FuncMap:               map[reflect.Type]env.ParserFunc{...},
}
```

### Testing

```go
cfg, err := env.ParseAsWithOptions[Config](env.Options{
    Environment: map[string]string{
        "HOST":   "localhost",
        "PORT":   "9090",
        "SECRET": "test-secret",
    },
})
require.NoError(t, err)
assert.Equal(t, 9090, cfg.Port)
```

### BAD vs GOOD

```go
// BAD — manual os.Getenv + strconv
port, _ := strconv.Atoi(os.Getenv("PORT"))
if port == 0 { port = 8080 }

// GOOD — declarative, validated, typed
type Config struct {
    Port int `env:"PORT" envDefault:"8080"`
}
cfg, err := env.ParseAs[Config]()
```

```go
// BAD — env loading scattered across codebase
func NewDB() *DB {
    host := os.Getenv("DB_HOST")
    // ...
}
func NewCache() *Cache {
    addr := os.Getenv("CACHE_ADDR")
    // ...
}

// GOOD — single config struct, parsed once
type Config struct {
    DB    DBConfig    `envPrefix:"DB_"`
    Cache CacheConfig `envPrefix:"CACHE_"`
}
cfg, err := env.ParseAs[Config]()
```

---

## Testing — `stretchr/testify`

Always use testify for assertions. `require` stops on failure (for setup), `assert` continues (for verification).

```go
func TestCreateUser(t *testing.T) {
    db := setupTestDB(t)
    require.NotNil(t, db)                   // setup — stop if nil

    user, err := db.CreateUser(ctx, params)
    require.NoError(t, err)                 // setup — stop if error

    assert.Equal(t, "Alice", user.Name)     // verify — continue on failure
    assert.NotEmpty(t, user.ID)
}
```

**See**: `go-testing` skill for table-driven tests, suites, and mocking with mockery.

---

## Quick Reference: All Libraries

| Library | Primary Function | One-Liner |
|---------|-----------------|-----------|
| `go-provider` | `provider.ValueOf[T]()` | Type-safe lazy singleton DI |
| `go-devtools/debugx` | `debugx.GetCurrentFunc()` | Runtime function/line introspection |
| `go-devtools/typesx` | `typesx.NewTypedSyncMap[K,V]()` | Generic sync.Map + type utilities |
| `go-devtools/bgworker` | `bgworker.NewJobsRunner()` | Background job scheduling |
| `sqlc` | `sqlc generate` | SQL → type-safe Go code |
| `caarlos0/env` | `env.ParseAs[Config]()` | Declarative env var loading |
| `testify` | `require.NoError(t, err)` | Test assertions (see `go-testing`) |
| `kong` | `kong.Parse(&cli)` | CLI parsing (see `go-cli`) |
