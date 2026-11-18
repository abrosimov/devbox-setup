---
name: commit-and-pr-text
description: Writes commit messages and PR/MR titles and descriptions in the repository's own convention, short and free of session history. Use before every git commit, gh pr create, glab mr create, or PR/MR description update, and when amending or squashing commit text.
version: 1
triggers:
  - commit message
  - git commit
  - pull request
  - merge request
  - PR description
  - MR description
  - gh pr create
  - glab mr create
problem: "Agents write commit messages and PR bodies as the session's report to the user, with verification history, environment failures and labels nobody outside the session can resolve, and in a convention the repository does not use."
related: [writing-for-the-reader, workflow]
---

# Commit and PR Text

A commit message and a PR/MR are read by a reviewer today and by a maintainer running `git log`
or `git blame` months later. Neither saw the session. They need to know what changed and why, in
the form the rest of the history uses; they do not need to know how the work went.

## 1. Take the convention from the repository

Each repository has its own convention, so read it before writing:

```bash
git log -20 --format=%s
```

Match what you see: a type prefix such as `fix:` or `feat(scope):` or plain sentences, where the
Jira key sits, sentence case or lower case, the `(#123)` suffix the forge adds on merge. A
`CONTRIBUTING.md` or a commit-lint configuration in the repository overrides the history.

When the history shows no clear convention, write a plain imperative sentence: "Retry the export
when the gateway is unavailable".

A `prepare-commit-msg` hook may add the Jira key from the branch name (check `git config
core.hooksPath` and `.git/hooks/`). When one does, do not add the key yourself.

## 2. Commit message

- **Subject:** up to about 72 characters, imperative mood, no full stop. It names the change, not
  the activity: "Pin the edge collector to 2.7.0", not "Update config".
- **Body:** only when the reason is not evident from the subject. One to three sentences on why:
  the problem the change solves and, if it is not obvious, why this approach. Wrap at 72.
- One commit per coherent change. Fix-up commits made during the session are squashed before the
  push when the repository's history does not keep them.

## 3. PR/MR

- **Title:** the same rule as a commit subject. With one commit, reuse its subject.
- **Body**, in this order and no longer:
  1. Why: two or three sentences on the problem.
  2. What changed: at most five bullets, each a change a reviewer can see in the diff.
  3. Checks: one line naming the checks that ran, for example `make lint and make test pass`.
- Add what a reviewer needs to judge the risk: a migration, a breaking change, a manual step after
  merge, a related PR in another repository.
- Follow a `PULL_REQUEST_TEMPLATE.md` in the repository when there is one, keeping each of its
  sections as short as the rules above.
- For an MR description that links Jira, Confluence or pinned code, the `jira-text` skill decides
  the link formats and the text rules (backticks, semicolons, internal labels, HTML entities): run
  its checker before handing the description over.

## 4. What stays out

These belong in the report to the user, never in a commit or a PR:

- how the session went: attempts, dead ends, what was tried first;
- how the work was verified, beyond the one line of checks;
- failures of the session's environment: sandbox denials, missing credentials, test suites that
  fail for reasons unrelated to the change;
- work left for later and open questions for the user;
- labels that only the session can resolve: numbered items from a plan, a list, an option card or
  research notes. Name the thing instead, or use an identifier anyone can open: a Jira key, an
  issue or PR number, a file path;
- attribution lines the user has not asked for.

## 5. Example

Too long, written as a session report:

> Fixed the queue sizing as discussed in the plan. Verified against upstream sources. Tests: lint
> passes; 38 deploy tests fail because the sandbox blocks ansible-playbook, unrelated. Follow-up:
> consider alerting later.

Right size:

> The edge lost spans during a ten-hour gateway outage: its queue was sized from compressed
> throughput, while the sizer counts uncompressed bytes.
>
> - Size the queue and the write-ahead log for a 72-hour outage.
> - Refuse new data at once when the queue is full instead of blocking clients.
> - Warn locally when the queue fills or the drain stalls.
>
> `make lint` and `make test` pass.
