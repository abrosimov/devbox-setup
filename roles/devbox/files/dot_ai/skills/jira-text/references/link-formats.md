# Link formats and text rules for Jira and Confluence

One format per link kind. Each entry gives the Markdown source, how it reads once rendered, and
the rules the checker enforces (rule id in brackets) or leaves to the writer.

## Contents

- [Jira ticket](#jira-ticket)
- [Jira comment](#jira-comment)
- [Spec rule](#spec-rule)
- [Code](#code)
- [Test](#test)
- [Merge request](#merge-request)
- [Commit in prose and the pin header](#commit-in-prose-and-the-pin-header)
- [Text rules](#text-rules)

## Jira ticket

```markdown
[EF-9792](https://openinnovationai.atlassian.net/browse/EF-9792) carries the specification corrections.
```

Renders as: [EF-9792](https://openinnovationai.atlassian.net/browse/EF-9792) carries the
specification corrections.

- Link the key at its first mention in each section. Later mentions in the same section stay bare.
  A section starts at a heading or at a line that is bold from end to end (`**1.2 …**`).
  [`unlinked-jira-key`]
- The key may sit inside longer link text, as long as the link goes to that key:
  `[Your reply on EF-8530](…/browse/EF-8530?focusedCommentId=…)` counts as a link to EF-8530.
- A key inside a quotation is someone else's text. Leave it and link the key next to the quote.

## Jira comment

```markdown
[Frane's decision on EF-9205](https://openinnovationai.atlassian.net/browse/EF-9205?focusedCommentId=79613#comment-79613)
```

Renders as: [Frane's decision on EF-9205](https://openinnovationai.atlassian.net/browse/EF-9205?focusedCommentId=79613#comment-79613)

- The link text says whose comment and on what: "Frane's decision on EF-9205", "your reply on
  EF-8073". Not "comment 79613" and not "here". [`unreadable-link-text` catches only "here",
  "link" and digit-only text. The rest is the writer's job.]
- The URL carries both `focusedCommentId=<id>` and `#comment-<id>`, so it opens and scrolls to
  the comment.
- Never link a comment that is not posted yet. A ticket that links a draft comment, and a comment
  that links back to that ticket, form a cycle with a dead end. Post the comment first, then add
  its link to the ticket.

## Spec rule

Spec rules have ids such as `WS-BR-42` or `TENRES-BR-27` and no anchors of their own, so the link
goes to the heading of the section that holds the rule.

```markdown
[WS-BR-42 of Workspace — Monitor](https://openinnovationai.atlassian.net/wiki/spaces/EF/pages/1615691920/Workspace+Monitor#Capacity-and-use)
```

Renders as: [WS-BR-42 of Workspace — Monitor](https://openinnovationai.atlassian.net/wiki/spaces/EF/pages/1615691920/Workspace+Monitor#Capacity-and-use)

- Link text: the rule id, then "of" and the page title.
- Anchor: the section heading as Confluence writes it (spaces become `-`, punctuation is
  percent-encoded: `#Which-workspaces%2C-and-accelerators-beyond-what-the-tenant-has`). Open the
  link and check it lands on the rule.
- Link at the first mention in each section, like a Jira key. [`unlinked-spec-rule`] Several rules
  in one link text (`[TENRES-BR-28 and TENRES-BR-29](…)`) count as linked.
- A short form (`BR-69`) after the full id (`TENRES-BR-69`) in the same section counts as a later
  mention. On its own it is flagged: write the full id.

## Code

```markdown
[ResourceAllocationService.py:584-616](https://gitlab.com/openinnovationai/platform/mlops/mlops-be/-/blob/7ff63b71a08f867690360c577c6779c64f9742fa/app/modules/resource_allocation/ResourceAllocationService.py#L584-616)
```

Renders as: [ResourceAllocationService.py:584-616](https://gitlab.com/openinnovationai/platform/mlops/mlops-be/-/blob/7ff63b71a08f867690360c577c6779c64f9742fa/app/modules/resource_allocation/ResourceAllocationService.py#L584-616)

- Pin the link to a full 40-character commit SHA, never `blob/main`, a branch or a tag: those move
  and the lines drift. [`unpinned-blob`]
- Line anchors: GitLab `#L584-616`, GitHub `#L584-L616`.
- Link text: file name and lines. Never `[:493-499]`, never a bare number. [`unreadable-link-text`]
- A function name in backticks is fine as link text when the sentence is about the function:
  ``[`get_total_available_resource_for_tenant`](…#L416-428)``.

## Test

```markdown
[`test_no_total_counts_an_unhealthy_node`](https://gitlab.com/openinnovationai/platform/mlops/mlops-be/-/blob/7b61f17c0cc48984e06cce8050612fd72101d1fa/tests/app/modules/resource_allocation/test_ResourceAllocationService_node_total.py#L199)
```

Renders as: [`test_no_total_counts_an_unhealthy_node`](https://gitlab.com/openinnovationai/platform/mlops/mlops-be/-/blob/7b61f17c0cc48984e06cce8050612fd72101d1fa/tests/app/modules/resource_allocation/test_ResourceAllocationService_node_total.py#L199)

- Link text: the test name in backticks.
- Anchor: the single line of the `def` (Python) or `func` (Go), so the reader lands on the name.
- Pin to the head commit of the MR that holds the test, and list that commit in the pin header.

## Merge request

```markdown
[`workspace-resource-updater` MR !28](https://gitlab.com/openinnovationai/platform/mlops/workspace-resource-updater/-/merge_requests/28)
```

Renders as: [`workspace-resource-updater` MR !28](https://gitlab.com/openinnovationai/platform/mlops/workspace-resource-updater/-/merge_requests/28)

- Link text: the repository in backticks, then `MR !<number>`. The number alone does not say
  which repository.

## Commit in prose and the pin header

In prose, a commit is its short SHA in backticks: `` `7ff63b71a` ``.

Every draft with code links carries a pin header near the top: one line that contains the word
"pinned" and lists, per repository, the commit its links point at. The checker reads every
backticked SHA on such a line, so reproducer heads and a deliberate tag pin go on it too:

```markdown
Code links are pinned to current main as of 2026-11-18: `mlops-be` `7ff63b71a`, `mlops-fe` `4ff12a7a9`, Volcano v1.14.1 `49b8f40ba`. One link in 2.7 is pinned to the `workspace-resource-updater` tag `v1.19.0` (`2bdbf7160`) on purpose. Reproducer tests are pinned to the MR heads, `mlops-be` `7b61f17c0` and `workspace-resource-updater` `2a2c63b4a`.
```

Every blob link must start with one of the listed SHAs. [`pin-mismatch`] With no pin header the
check is skipped. A line starting `Pins:` also counts as a pin header.

## Text rules

| Write | Not | Rule id |
| --- | --- | --- |
| `` `<workspace_id>` `` | <workspace_id> (can be read as an HTML tag and vanish) | `bare-placeholder` |
| `` `GET /v3/workspaces/<workspace_id>/resources` `` | GET /v3/workspaces/… | `bare-api-path` |
| `` `{"mig_profile": null}` ``, `` `resources_used` ``, `` `SHOW_WORKSPACE_AVAILABLE_RESOURCES` `` | the same without backticks | `bare-literal` covers `true`/`false`/`null` only |
| `` `true` ``, `` `false` ``, `` `null` `` as values | defaults to true | `bare-literal` |
| `` `workspace-resource-updater` ``, `` `mlops-be` `` (our services) | workspace-resource-updater | not checked |
| Volcano, Kubernetes, metrics-server (third-party products) | `` `Volcano` `` | not checked |
| Two sentences | a semicolon joining two clauses | `semicolon` |
| The thing's name or a link anyone can open | ledger ids such as B5, D3, E7, Q9f, R1, I1–I9, "decision 1.4" | `internal-label` |
| `<` and `>` inside backticks | `&lt;` and `&gt;` (they show literally) | `html-entity` |
| A URL link | an Obsidian `[[wikilink]]` (does not render in Jira) | `wikilink` |

Payloads, field names, environment variables and identifiers go in backticks as well. The checker
cannot tell an identifier from a word, so only the forms in the table are checked.
