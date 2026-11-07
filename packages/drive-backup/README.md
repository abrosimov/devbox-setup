# drive-backup

Archive a set of directories into a git repository whose `*.tar.zst` files live in
Git LFS, then commit and push. Built to run unattended from a scheduler (a launchd
LaunchAgent in devbox), so every outcome — including failure — ends up in a log
that is committed next to the archives.

Stdlib-only, Python 3.14+ (`compression.zstd`, `tomllib`, `tarfile`). Needs `git`
and `git-lfs` on `PATH`.

## Usage

```bash
drive-backup check-config            # validate, print the resolved plan
drive-backup run                     # archive immediately, commit, push
drive-backup run --no-push           # commit locally only, at refs/drive-backup/unpushed/
drive-backup --config other.toml run
```

Exit codes: `0` ok, `1` run failed, `2` configuration error, `75` another run holds
the lock.

## Environment

| Variable | Used for |
|---|---|
| `MNEMOSYNE_PERISTASEOS` | archive-name prefix (the profile, e.g. `work`); `--profile` overrides |
| `AION_AUTOPOIESEON` | base for relative paths and for the default `repo_dir` |
| `XDG_CONFIG_HOME` | config lookup, default `~/.config/drive-backup/config.toml` |
| `XDG_STATE_HOME` | lock file, default `~/.local/state/drive-backup/run.lock` |

## Configuration

```toml
repo_dir = "drive/base"      # default; relative to $AION_AUTOPOIESEON
remote = "origin"            # default
branch = "master"            # default: the remote's default branch
zstd_level = 9               # 1..22
max_part_bytes = 1992294400  # default 1900 MiB; 1..2147483648 (GitHub LFS 2 GiB limit)

[[dir]]
name = "claude"              # [a-z0-9-]; part of the archive file name
path = "~/.claude"           # ~, $VARS, or relative to $AION_AUTOPOIESEON
exclude = ["bin/.venv", "**/__pycache__"]
```

`branch` is where every backup goes. Without it, a run uses the remote's default
branch: `refs/remotes/<remote>/HEAD` when the clone has it, otherwise the remote's
`HEAD` as reported by `git ls-remote --symref`. The branch checked out in
`repo_dir` plays no part.

`exclude` patterns are matched against the path relative to the directory with
`PurePath.full_match` semantics: `*` stays within one path segment, `**` spans any
number. A pattern that matches a directory prunes the whole subtree.

`max_part_bytes` caps the size of every file a run writes, because GitHub LFS
rejects objects larger than 2 GiB (2147483648 bytes). An archive whose compressed
stream is larger is written as numbered parts (see the layout below). The default,
1900 MiB, leaves headroom under the limit.

Older configs may still contain per-directory `busy` lists and a top-level
`[defer]` table. They are validated for compatibility but ignored; every run
archives immediately.

## What a run does

1. Takes an exclusive lock.
2. Preflight: `repo_dir` is a repository root, `git-lfs` is installed and its
   filters are configured. If this fails, nothing is written; the error goes to
   stderr only.
3. Fetches the target branch into `refs/remotes/<remote>/<branch>` and checks it
   out, detached, into a private worktree at `<git dir>/drive-backup-worktree`
   (with `GIT_LFS_SKIP_SMUDGE=1`: other machines' archives stay pointers). A
   worktree left there by a crashed run is removed first. If the fetch fails,
   the run fails before writing anything, as in step 2.
4. Replays backup commits that an earlier run did not push (see below) onto the
   remote tip, so they go out with this run's push. One that does not apply
   cleanly is skipped with a warning and left in place.
5. Immediately archives every configured directory as a fuzzy snapshot into the
   worktree, without inspecting running processes. Every file it produces must
   be LFS-tracked according to the target branch's `.gitattributes`, or the
   archive is discarded and the run fails.
6. Commits the archives and the run log in one commit, uploads LFS objects
   explicitly (`git lfs push`), pushes `HEAD` to `<remote>/<branch>`, and on a
   rejected push fetches, rebases and retries (three attempts). A rebase that
   stops on a conflict is aborted and the run fails.
7. Removes the worktree, whether the run succeeded or failed.

The run never touches the checkout in `repo_dir`: its branch, upstream, `HEAD`,
index and working tree (dirty or not) stay exactly as they were, and its local
branches are not updated; only `refs/remotes/<remote>/<branch>` moves.

A commit that was not pushed — `run --no-push`, or a push that failed every
attempt — is kept at `refs/drive-backup/unpushed/<sha>`, on no branch, and the
next run replays it. List them with `git for-each-ref refs/drive-backup/`; drop
one with `git update-ref -d <ref>`.

Layout:

```
<YYYY-MM>/<profile>_<name>_<YYYY-MM-DD>.tar.zst            # -2, -3 … on same-day reruns
<YYYY-MM>/<profile>_<name>_<YYYY-MM-DD>.tar.zst.part-001   # larger than max_part_bytes:
<YYYY-MM>/<profile>_<name>_<YYYY-MM-DD>.tar.zst.part-002   #   parts instead of the .tar.zst
<YYYY-MM>/<profile>_backup_<YYYY-MM-DD>.log
```

An archive that fits in `max_part_bytes` is a single `.tar.zst`. A larger one is
cut on the fly into `.part-001`, `.part-002`, … (contiguous, every part but the
last exactly `max_part_bytes`) and no `.tar.zst` is written. The parts are a plain
byte split of the one compressed stream, so concatenating them in order yields the
`.tar.zst`; there is no manifest. The repository's `.gitattributes` must track both
names:

```
*.tar.zst filter=lfs diff=lfs merge=lfs -text
*.tar.zst.part-* filter=lfs diff=lfs merge=lfs -text
```

Archives are rooted at the directory's own name (`.claude/…`). Restore a
single-file archive:

```bash
git lfs pull --include '2026-09/work_claude_2026-09-26.tar.zst'
tar --zstd -xf 2026-09/work_claude_2026-09-26.tar.zst -C /tmp/restore
```

Restore a multi-part archive (the shell sorts the zero-padded part names in order):

```bash
git lfs pull --include '2026-09/work_codex_2026-09-26.tar.zst.part-*'
cat 2026-09/work_codex_2026-09-26.tar.zst.part-* | tar --zstd -xf - -C /tmp/restore
```

Files that change while being read are stored at the size recorded in their tar
header: growth is truncated without a warning, while shrinkage is zero-padded and
logged. Files that vanish or cannot be read are skipped with a warning. A snapshot
may therefore contain an incomplete application session, but one live process
never delays or blocks the rest of the backup.

All git commands run with `core.hooksPath=/dev/null`, so user-level hooks never
touch backup commits.

## Development

```bash
uv sync
uv run pytest
uv run ruff check && uv run ruff format --check
uv run pyrefly check
```
