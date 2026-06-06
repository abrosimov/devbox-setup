// env-setup.js — Shared PATH hardening for hook scripts.
//
// Hook scripts run as Node.js child processes that inherit Claude Code's
// environment. When Claude Code is launched from a GUI context (Spotlight,
// dock, IDE) rather than a terminal, the process may lack paths configured
// by fish/bash profiles. This module augments PATH with known tool
// directories so hooks can find goimports, ruff, npx, etc.
//
// Usage: require("./env-setup") at the top of any hook script.

const path = require("path");
const fs = require("fs");

const HOME = process.env.HOME || process.env.USERPROFILE || "/tmp";

const EXTRA_PATHS = [
  "/opt/homebrew/bin",
  "/opt/homebrew/sbin",
  path.join(HOME, ".local", "bin"),
  path.join(HOME, ".programming", "go", "bin"),
  path.join(HOME, ".cargo", "bin"),
  path.join(HOME, ".claude", "bin"),
  path.join(HOME, "bin"),
  path.join(HOME, ".programming", "ruby", "gems", "bin"),
];

const currentPath = process.env.PATH || "";
const currentDirs = new Set(currentPath.split(":"));

const missing = EXTRA_PATHS.filter(
  (p) => !currentDirs.has(p) && fs.existsSync(p)
);

if (missing.length > 0) {
  process.env.PATH = missing.join(":") + ":" + currentPath;
}

// Also set GOPATH if not present — needed by goimports
if (!process.env.GOPATH) {
  process.env.GOPATH = path.join(HOME, ".programming", "go");
}

// Sandbox-safe toolchain environment:
// Redirect caches to $TMPDIR (sandbox-writable) instead of defaults
// under ~/.cache or ~/Library/Caches which are outside the write allowlist.
const TMPDIR = process.env.TMPDIR || "/tmp";

// Go
if (!process.env.GOTOOLCHAIN) {
  process.env.GOTOOLCHAIN = "local";
}
if (!process.env.GOCACHE) {
  process.env.GOCACHE = path.join(TMPDIR, "go-build-cache");
}
if (!process.env.GOMODCACHE) {
  process.env.GOMODCACHE = path.join(TMPDIR, "go-mod-cache");
}

// Python (uv, ruff, mypy)
if (!process.env.UV_CACHE_DIR) {
  process.env.UV_CACHE_DIR = path.join(TMPDIR, "uv-cache");
}
if (!process.env.RUFF_CACHE_DIR) {
  process.env.RUFF_CACHE_DIR = path.join(TMPDIR, "ruff-cache");
}
if (!process.env.MYPY_CACHE_DIR) {
  process.env.MYPY_CACHE_DIR = path.join(TMPDIR, "mypy-cache");
}

// Node (npm/npx)
if (!process.env.NPM_CONFIG_CACHE) {
  process.env.NPM_CONFIG_CACHE = path.join(TMPDIR, "npm-cache");
}
