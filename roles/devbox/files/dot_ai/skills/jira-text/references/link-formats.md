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
[PROJ-123](https://example.atlassian.net/browse/PROJ-123) carries the specification corrections.
```

Renders as: [PROJ-123](https://example.atlassian.net/browse/PROJ-123) carries the
specification corrections.

- The key is linked at every mention: a reader may land on any line from a search or a link.
  [`unlinked-jira-key`]
- The key may sit inside longer link text, as long as the link goes to that key:
  `[Your reply on PROJ-98](…/browse/PROJ-98?focusedCommentId=…)` counts as a link to PROJ-98.
- A key inside a quotation is linked too: `"(related: [PROJ-160](…/browse/PROJ-160))"`.

## Jira comment

```markdown
[Alice's decision on PROJ-120](https://example.atlassian.net/browse/PROJ-120?focusedCommentId=10001#comment-10001)
```

Renders as: [Alice's decision on PROJ-120](https://example.atlassian.net/browse/PROJ-120?focusedCommentId=10001#comment-10001)

- The link text says whose comment and on what: "Alice's decision on PROJ-120", "your reply on
  PROJ-87". Not "comment 10001" and not "here". [`unreadable-link-text` catches only "here",
  "link", "this", "this link", "click here", text that starts with `:` and digit-only text. The
  rest is the writer's job.]
- The URL carries both `focusedCommentId=<id>` and `#comment-<id>`, so it opens and scrolls to
  the comment.
- Never link a comment that is not posted yet. A ticket that links a draft comment, and a comment
  that links back to that ticket, form a cycle with a dead end. Post the comment first, then add
  its link to the ticket.

## Spec rule

Spec rules have ids such as `ORD-BR-42` or `PAY-BR-27` and no anchors of their own, so the link
goes to the heading of the section that holds the rule.

```markdown
[ORD-BR-42 of Orders — Checkout](https://example.atlassian.net/wiki/spaces/SHOP/pages/123456789/Orders+Checkout#Order-limits)
```

Renders as: [ORD-BR-42 of Orders — Checkout](https://example.atlassian.net/wiki/spaces/SHOP/pages/123456789/Orders+Checkout#Order-limits)

- Link text: the rule id, then "of" and the page title.
- Anchor: the section heading as Confluence writes it (spaces become `-`, punctuation is
  percent-encoded: `#Which-orders%2C-and-items-beyond-what-the-customer-has`). Open the
  link and check it lands on the rule.
- Linked at every mention, like a Jira key, quotations included. [`unlinked-spec-rule`] Several
  rules in one link text (`[PAY-BR-28 and PAY-BR-29](…)`) count as linked.
- A short form (`BR-69`) is a mention too and needs the link. Prefer the full id (`PAY-BR-69`).

## Code

```markdown
[order_service.py:584-616](https://gitlab.com/acme/shop/orders-api/-/blob/3f9c2a7d1e4b8c06a5d2f7e91b3c4d5e6f708192/app/orders/order_service.py#L584-616)
```

Renders as: [order_service.py:584-616](https://gitlab.com/acme/shop/orders-api/-/blob/3f9c2a7d1e4b8c06a5d2f7e91b3c4d5e6f708192/app/orders/order_service.py#L584-616)

- Pin the link to a full 40-character commit SHA, never `blob/main`, a branch or a tag: those move
  and the lines drift. [`unpinned-blob`]
- Line anchors: GitLab `#L584-616`, GitHub `#L584-L616`.
- Link text: file name and lines. Never `[:493-499]`, never a bare number. [`unreadable-link-text`]
- A function name is fine as link text when the sentence is about the function, without
  backticks: `[get_reserved_items_for_customer](…#L416-428)`. [`code-in-link-text`]

## Test

```markdown
[test_cancelled_order_is_not_counted](https://gitlab.com/acme/shop/orders-api/-/blob/8e1d4b2a9c7f3e05d6b1a2c3e4f50617283a9b0c/tests/orders/test_order_service.py#L199)
```

Renders as: [test_cancelled_order_is_not_counted](https://gitlab.com/acme/shop/orders-api/-/blob/8e1d4b2a9c7f3e05d6b1a2c3e4f50617283a9b0c/tests/orders/test_order_service.py#L199)

- Link text: the test name, without backticks. Jira's Markdown-to-ADF converter drops a link
  whose text holds inline code and keeps only the code, so ``[`test_name`](…)`` arrives as plain
  code with no link. [`code-in-link-text`] GitLab and GitHub render such links, so a PR or MR
  description that will not be pasted into Jira may keep the backticked form (checker flag
  `--allow-code-links`).
- Anchor: the single line of the `def` (Python) or `func` (Go), so the reader lands on the name.
- Pin to the head commit of the MR that holds the test, and list that commit in the pin header.

## Merge request

```markdown
[stock-updater MR !28](https://gitlab.com/acme/shop/stock-updater/-/merge_requests/28)
```

Renders as: [stock-updater MR !28](https://gitlab.com/acme/shop/stock-updater/-/merge_requests/28)

- Link text: the repository, then `MR !<number>`. The number alone does not say which repository.
- No backticks around the repository inside the link text, for the reason given under
  [Test](#test). [`code-in-link-text`] A PR or MR description that will not be pasted into Jira
  may write ``[`stock-updater` MR !28](…)``.

## Commit in prose and the pin header

In prose, a commit is its short SHA in backticks: `` `3f9c2a7d1` ``.

Every draft with code links carries a pin header near the top: one line that contains the word
"pinned" and lists, per repository, the commit its links point at. The checker reads every
backticked SHA on such a line, so reproducer heads and a deliberate tag pin go on it too:

```markdown
Code links are pinned to current main as of 2026-11-18: `orders-api` `3f9c2a7d1`, `shop-web` `c41a9e8d2`, Kubernetes v1.31.0 `5d0e7b3c6`. One link in 2.7 is pinned to the `stock-updater` tag `v1.19.0` (`a7b3c9d1e`) on purpose. Reproducer tests are pinned to the MR heads, `orders-api` `8e1d4b2a9` and `stock-updater` `b2e8f1c4d`.
```

Every blob link must start with one of the listed SHAs. [`pin-mismatch`] With no pin header the
check is skipped. A line starting `Pins:` also counts as a pin header.

## Text rules

| Write | Not | Rule id |
| --- | --- | --- |
| `` `<order_id>` `` | <order_id> (can be read as an HTML tag and vanish) | `bare-placeholder` |
| `` `GET /v3/orders/<order_id>/items` `` | GET /v3/orders/… | `bare-api-path` |
| `` `{"discount_code": null}` ``, `` `items_reserved` ``, `` `SHOW_ORDER_STOCK_LEVELS` `` | the same without backticks | `bare-literal` covers `true`/`false`/`null` only |
| `` `true` ``, `` `false` ``, `` `null` `` as values | defaults to true | `bare-literal` |
| `` `stock-updater` ``, `` `orders-api` `` (our services) | stock-updater | not checked |
| Kubernetes, PostgreSQL, Redis (third-party products) | `` `Kubernetes` `` | not checked |
| Two sentences | a semicolon joining two clauses | `semicolon` |
| The thing's name or a link anyone can open | ledger ids such as B5, D3, E7, Q9f, R1, I1–I9, "decision 1.4" | `internal-label` |
| `<` and `>` inside backticks | `&lt;` and `&gt;` (they show literally) | `html-entity` |
| A URL link | an Obsidian `[[wikilink]]` (does not render in Jira) | `wikilink` |

Payloads, field names, environment variables and identifiers go in backticks as well. The checker
cannot tell an identifier from a word, so only the forms in the table are checked.
