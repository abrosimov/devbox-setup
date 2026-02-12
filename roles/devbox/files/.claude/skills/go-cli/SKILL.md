---
name: go-cli
description: >
  Go CLI tool development with the Kong library. Use when building CLI applications,
  parsing flags, defining subcommands, writing CLI project structure, or testing
  CLI tools. Triggers on: CLI, command line, kong, subcommand, flag parsing,
  positional argument, CLI testing, CLI project structure.
---

# Go CLI Reference

CLI tool development patterns using [Kong](https://github.com/alecthomas/kong).

---

## Decision Tree: Do You Need Kong?

```
Building a CLI tool?
├─ Yes, with subcommands → Kong
├─ Yes, simple (1-2 flags) → stdlib flag package
├─ No, it's an HTTP service → not Kong
└─ No, it's a library → not Kong
```

---

## Project Structure

```
cmd/app/main.go              # kong.Parse, CLI struct, version flag
internal/cmd/globals.go      # Globals struct (shared flags)
internal/cmd/serve.go        # ServeCommand with Run()
internal/cmd/migrate.go      # MigrateCommand with Run()
```

### main.go — Entry Point

```go
package main

import (
    "fmt"
    "os"

    "github.com/alecthomas/kong"

    "myapp/internal/cmd"
)

var version = "dev"

type VersionFlag string

func (v VersionFlag) Decode(_ *kong.DecodeContext) error { return nil }
func (v VersionFlag) IsBool() bool                       { return true }
func (v VersionFlag) BeforeApply(app *kong.Kong, vars kong.Vars) error {
    fmt.Println(vars["version"])
    app.Exit(0)
    return nil
}

type CLI struct {
    cmd.Globals

    Serve   cmd.ServeCommand   `cmd:"" help:"Start the server"`
    Migrate cmd.MigrateCommand `cmd:"" help:"Run database migrations"`
    Version VersionFlag        `help:"Print version" short:"v" name:"version"`
}

func main() {
    cli := CLI{Version: VersionFlag(version)}
    ctx := kong.Parse(&cli,
        kong.Name("myapp"),
        kong.Description("My application"),
        kong.UsageOnError(),
        kong.ConfigureHelp(kong.HelpOptions{Compact: true}),
        kong.DefaultEnvars("MYAPP"),
        kong.Vars{"version": version},
    )
    err := ctx.Run(&cli.Globals)
    ctx.FatalIfErrorf(err)
}
```

### globals.go — Shared Flags

```go
package cmd

type Globals struct {
    Debug  bool   `help:"Enable debug logging" short:"d" env:"DEBUG"`
    Format string `help:"Output format" default:"console" enum:"console,json"`
}
```

### Command Files — One per File

```go
package cmd

import "fmt"

type ServeCommand struct {
    Addr string `help:"Listen address" default:":8080" env:"ADDR"`
}

func (c *ServeCommand) Run(g *Globals) error {
    fmt.Printf("serving on %s (debug=%v)\n", c.Addr, g.Debug)
    return nil
}
```

---

## Kong Grammar: Struct Tags

### Core Tags

| Tag | Purpose | Example |
|-----|---------|---------|
| `cmd:""` | Field is a subcommand | `Serve ServeCmd \`cmd:""\`` |
| `arg:""` | Positional argument (required by default) | `File string \`arg:""\`` |
| `help:"text"` | Help text | `help:"Listen address"` |
| `default:"val"` | Default value | `default:":8080"` |
| `env:"VAR"` | Bind to env var | `env:"PORT"` |
| `short:"f"` | Short flag | `short:"p"` |
| `required:""` | Must be provided | `required:""` |
| `optional:""` | Positional arg not required | `optional:""` |
| `enum:"a,b,c"` | Restrict valid values | `enum:"json,yaml,toml"` |
| `name:"x"` | Override flag/command name | `name:"output-dir"` |
| `hidden:""` | Hide from help | `hidden:""` |
| `aliases:"a,b"` | Alternative names | `aliases:"ls,list"` |

### Constraint Tags

| Tag | Purpose | Example |
|-----|---------|---------|
| `xor:"group"` | Mutually exclusive flags | `xor:"output"` |
| `and:"group"` | Interdependent flags (all or none) | `and:"auth"` |
| `negatable:""` | Boolean `--no-flag` support | `negatable:""` |

### Collection Tags

| Tag | Purpose | Default |
|-----|---------|---------|
| `sep:","` | Slice separator | `,` |
| `mapsep:"="` | Map key=value separator | `=` |

### Struct Tags

| Tag | Purpose | Example |
|-----|---------|---------|
| `prefix:"db-"` | Prefix embedded struct flags | `prefix:"db-"` |
| `embed:""` | Include fields inline | `embed:""` |
| `group:"name"` | Logical help grouping | `group:"Database"` |

### Display Tags

| Tag | Purpose | Example |
|-----|---------|---------|
| `placeholder:"FILE"` | Help placeholder text | `placeholder:"FILE"` |
| `passthrough:""` | Stop parsing, capture rest | `passthrough:""` |

---

## Command Pattern

Every leaf command implements `Run(...) error`. Parameters are injected via `kong.Bind`.

### Basic

```go
type EchoCommand struct {
    Text string `arg:"" help:"Text to echo"`
}

func (c *EchoCommand) Run(g *Globals) error {
    fmt.Println(c.Text)
    return nil
}
```

### With Dependency Injection

```go
// main.go — bind dependencies
ctx := kong.Parse(&cli,
    kong.Bind(&cli.Globals),
    kong.BindTo(db, (*Database)(nil)),     // bind concrete to interface
)

// command — receives injected dependencies
type ImportCommand struct {
    File string `arg:"" type:"existingfile"`
}

func (c *ImportCommand) Run(g *Globals, db Database) error {
    return db.Import(c.File)
}
```

### Nested Subcommands

```go
type CLI struct {
    DB DBCommand `cmd:"" help:"Database operations"`
}

type DBCommand struct {
    Migrate MigrateCommand `cmd:"" help:"Run migrations"`
    Seed    SeedCommand    `cmd:"" help:"Seed test data"`
}

// Usage: myapp db migrate
// Usage: myapp db seed
```

### Default Command

```go
type CLI struct {
    Serve ServeCommand `cmd:"" default:"1" help:"Start server"`
    Init  InitCommand  `cmd:"" help:"Initialise config"`
}

// `myapp` (no args) → runs Serve
// `myapp init` → runs Init
```

---

## Hooks & Lifecycle

Execution order: `BeforeReset` → `BeforeResolve` → `BeforeApply` → `AfterApply` → `Run`

Hooks are called on any node in the parse tree that implements them.

### AfterApply — Post-Parse Setup

```go
type Globals struct {
    Debug  bool   `help:"Enable debug" short:"d"`
    Format string `help:"Output format" default:"console" enum:"console,json"`
    Logger zerolog.Logger `kong:"-"` // excluded from parsing
}

func (g *Globals) AfterApply() error {
    level := zerolog.InfoLevel
    if g.Debug {
        level = zerolog.DebugLevel
    }
    g.Logger = zerolog.New(os.Stderr).Level(level).With().Timestamp().Logger()
    return nil
}
```

### BeforeApply — Pre-Parse Actions (Version Flag)

```go
type VersionFlag string

func (v VersionFlag) Decode(_ *kong.DecodeContext) error { return nil }
func (v VersionFlag) IsBool() bool                       { return true }
func (v VersionFlag) BeforeApply(app *kong.Kong, vars kong.Vars) error {
    fmt.Println(vars["version"])
    app.Exit(0)
    return nil
}
```

### Global Hooks via Options

```go
kong.Parse(&cli,
    kong.WithBeforeApply(func(ctx *kong.Context) error {
        // runs before any node-level hooks
        return nil
    }),
)
```

---

## Configuration Loading

### Environment Variables

```go
// Per-flag binding
type Config struct {
    Port int `env:"PORT" default:"8080"`
}

// Auto-bind all flags: FLAG_NAME → PREFIX_FLAG_NAME
kong.Parse(&cli, kong.DefaultEnvars("MYAPP"))
// --port → MYAPP_PORT, --db-host → MYAPP_DB_HOST
```

### Kong vs caarlos0/env

| Scenario | Use |
|----------|-----|
| CLI flags with env fallback | Kong `env:""` tag |
| App config loaded at startup (no CLI) | `caarlos0/env` with `ParseAs[T]()` |
| CLI tool with separate runtime config | Kong for flags, `caarlos0/env` for config struct |

**See**: `go-toolbox` skill for `caarlos0/env` patterns.

---

## Custom Type Mappers

### MapperValue — Type Implements Parsing

```go
type LogLevel zerolog.Level

func (l *LogLevel) Decode(ctx *kong.DecodeContext) error {
    var raw string
    if err := ctx.Scan.PopValueInto("level", &raw); err != nil {
        return err
    }
    level, err := zerolog.ParseLevel(raw)
    if err != nil {
        return fmt.Errorf("invalid log level %q: %w", raw, err)
    }
    *l = LogLevel(level)
    return nil
}

// Usage
type Globals struct {
    LogLevel LogLevel `help:"Log level" default:"info" enum:"debug,info,warn,error"`
}
```

### Named Mapper — Registered by Name

```go
type portMapper struct{}

func (m portMapper) Decode(ctx *kong.DecodeContext, target reflect.Value) error {
    var raw string
    if err := ctx.Scan.PopValueInto("port", &raw); err != nil {
        return err
    }
    port, err := strconv.Atoi(raw)
    if err != nil || port < 1 || port > 65535 {
        return fmt.Errorf("invalid port: %s", raw)
    }
    target.SetInt(int64(port))
    return nil
}

// Register and use via type tag
kong.Parse(&cli, kong.NamedMapper("port", portMapper{}))
// Port int `type:"port" default:"8080"`
```

### Built-in Type Mappers

| Name | Validates |
|------|-----------|
| `existingfile` | File must exist |
| `existingdir` | Directory must exist |
| `path` | Path (created if needed) |
| `counter` | Repeatable flag (`-vvv`) |

---

## Testing CLI Tools

### Capture Output

```go
func TestServeCommand(t *testing.T) {
    var stdout, stderr bytes.Buffer

    cli := CLI{}
    parser, err := kong.New(&cli,
        kong.Name("test"),
        kong.Exit(func(int) {}),         // prevent os.Exit
        kong.Writers(&stdout, &stderr),   // capture output
    )
    require.NoError(t, err)

    ctx, err := parser.Parse([]string{"serve", "--addr", ":9090"})
    require.NoError(t, err)

    err = ctx.Run(&cli.Globals)
    require.NoError(t, err)
}
```

### Test Parse Errors

```go
func TestInvalidFlag(t *testing.T) {
    var cli CLI
    parser, err := kong.New(&cli, kong.Exit(func(int) {}))
    require.NoError(t, err)

    _, err = parser.Parse([]string{"--invalid"})
    assert.Error(t, err)
}
```

### Test Enum Validation

```go
func TestFormatEnum(t *testing.T) {
    var cli CLI
    parser, _ := kong.New(&cli, kong.Exit(func(int) {}))

    _, err := parser.Parse([]string{"--format", "xml"})
    assert.Error(t, err) // xml not in enum
}
```

---

## BAD vs GOOD

```go
// BAD — monolithic CLI struct with all logic in main
func main() {
    var port int
    flag.IntVar(&port, "port", 8080, "listen port")
    flag.Parse()
    // 200 lines of logic here
}

// GOOD — Kong struct grammar, commands in internal/cmd/
type CLI struct {
    Globals
    Serve   ServeCommand   `cmd:"" help:"Start server"`
    Migrate MigrateCommand `cmd:"" help:"Run migrations"`
}
```

```go
// BAD — manual env fallback
port := os.Getenv("PORT")
if port == "" {
    port = "8080"
}

// GOOD — Kong handles it
type ServeCmd struct {
    Port int `env:"PORT" default:"8080" help:"Listen port"`
}
```

```go
// BAD — command logic directly on CLI struct
func (c *CLI) Run() error {
    // which command? check flags manually...
}

// GOOD — each command owns its Run()
func (c *ServeCommand) Run(g *Globals) error {
    return serve(c.Addr, g.Logger)
}
```

---

## Quick Reference

### Common Kong Parse Options

| Option | Purpose |
|--------|---------|
| `kong.Name("app")` | Application name |
| `kong.Description("...")` | App description |
| `kong.UsageOnError()` | Show usage on parse error |
| `kong.DefaultEnvars("PFX")` | Auto env var binding |
| `kong.ConfigureHelp(HelpOptions{Compact: true})` | Compact help |
| `kong.Bind(&globals)` | Inject into Run() |
| `kong.BindTo(impl, (*Iface)(nil))` | Bind to interface |
| `kong.Vars{"k": "v"}` | Interpolation variables |
| `kong.Exit(func(int){})` | Custom exit (for tests) |
| `kong.Writers(out, err)` | Custom output (for tests) |

### Minimal CLI Skeleton

```go
// Smallest useful CLI
type CLI struct {
    File   string `arg:"" type:"existingfile" help:"Input file"`
    Output string `short:"o" default:"-" help:"Output file (- for stdout)"`
}

func main() {
    var cli CLI
    kong.Parse(&cli, kong.UsageOnError())
    // use cli.File, cli.Output
}
```
