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

// Sandbox-safe Go environment:
// - GOTOOLCHAIN=local prevents Go from downloading a newer toolchain binary,
//   which fails in sandbox due to filesystem/network restrictions.
// - GOCACHE/GOMODCACHE use $TMPDIR (sandbox-writable) instead of default
//   ~/Library/Caches or ~/.cache which may be outside the write allowlist.
if (!process.env.GOTOOLCHAIN) {
  process.env.GOTOOLCHAIN = "local";
}
const TMPDIR = process.env.TMPDIR || "/tmp";
if (!process.env.GOCACHE) {
  process.env.GOCACHE = path.join(TMPDIR, "go-build-cache");
}
if (!process.env.GOMODCACHE) {
  process.env.GOMODCACHE = path.join(TMPDIR, "go-mod-cache");
}
