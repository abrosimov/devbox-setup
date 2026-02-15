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
  "/opt/homebrew/opt/node@18/bin",
  path.join(HOME, ".programming", "js", "npm-packages", "bin"),
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
