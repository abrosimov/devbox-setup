# Framework bundle

Choose a document by the result needed now. FPF Core supplies shared concepts; each Domain
Principle Framework (DPF) supplies methods for its field. Narrative work uses NSTD through the
`narrative-thinking` skill. Availability of a framework does not make its use mandatory.

This directory is a verbatim copy of the upstream repository's documents, laid out as upstream lays
them out. Start with the upstream [introduction](Readme.md) and the [DPF catalogue](DPFs/README.md);
each suite under `DPFs/` has its own README and reference. Open the selected pattern's problem
frame, solution and checklist, and combine them with actual project evidence. Read neighbouring
patterns only when their result is needed.

## Sources and maintenance

The [licensing notice](LICENSING.md) travels with the documents.
[Snapshot provenance](upstream-snapshot.json) records the single upstream commit and each file's
SHA-256. Upstream documents retain their original bytes and links; links to GitHub `main` may
lead to a newer edition. Use the local files for the recorded snapshot.

In the devbox-setup repository, `config/upstream-docs.json` names the upstream repository, the
tracked ref and this directory as the destination. Every upstream Markdown and `LICENSE` file, at any
depth, is mirrored to the same relative path here. Files recorded in the snapshot that upstream no
longer has are deleted; files the snapshot does not record, such as this index, are never touched.

```sh
make sync-upstream-docs
make sync-upstream-docs ARGS='--check --no-reset-drift'
make sync-upstream-docs ARGS='--ref <commit> --no-reset-drift'
```

The sync resolves one revision, downloads that commit's archive once, validates every upstream
document, then installs additions and changes, removes files dropped upstream, and writes
provenance. It prints the added, removed, modified and renamed paths with the old and new commit;
`--check` prints the same report without changing anything. An upstream with no documents is
refused rather than emptying the bundle. Handled installation failures restore previous files,
deleted ones included. If a concurrent edit or
filesystem failure prevents safe rollback, the tool preserves recovery backups and reports the
incomplete rollback. This is not a crash-atomic transaction or atomic visibility for concurrent
readers. `--check` reports drift without changing
documents or caches. `--no-reset-drift` leaves local badge caches untouched.

The existing statusline and Fish badges track Core and Narrative only. They do not establish
freshness or integrity of the whole Suite. Repository bundle tests verify the recorded hashes
without network access. Synchronisation changes the repository; normal provisioning distributes
the shared skill references to configured clients.
