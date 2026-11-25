# commit-staged-topics

Splits the staged changes into one commit per topic on `master` and pushes them. A historical
one-off for cleaning up a large staged change set; it predates the rule that agents never commit
to a protected branch, so run it only on the owner's explicit instruction.
`--dry-run` prints the planned commits without creating them; `--no-push` commits without pushing.

Run: `uv run ai/scripts/commit-staged-topics/commit_topics.py [--dry-run] [--no-push]`

Test: `uv run pytest ai/scripts/commit-staged-topics`
