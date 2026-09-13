# Framework bundle

Choose a document by the result needed now. FPF Core supplies shared concepts; each Domain
Principle Framework (DPF) supplies methods for its field. Narrative work uses NSTD through the
`narrative-thinking` skill. Availability of a framework does not make its use mandatory.

Start with the [Suite introduction](<Engineering DPF Suite/README.md>) or search the
[Suite Reference](<Engineering DPF Suite/ENGINEERING-DPF-SUITE-REFERENCE.md>) for the current
working question. Open the selected pattern's problem frame, solution and checklist, and combine
them with actual project evidence. Read neighbouring patterns only when their result is needed.

| Needed result | Domain document |
|---|---|
| System boundary, architecture, integration or delivery decision | [Systems Engineering](<Engineering DPF Suite/SYSTEMS-ENGINEERING-PRINCIPLES-FRAMEWORK.md>) |
| A reproducible or improved way of working | [Method Engineering](<Engineering DPF Suite/METHOD-ENGINEERING-PRINCIPLES-FRAMEWORK.md>) |
| Problem formulation, alternatives or recommendation | [Problem Structuring and Decision Support](<Engineering DPF Suite/PROBLEM-STRUCTURING-AND-DECISION-SUPPORT-PRINCIPLES-FRAMEWORK.md>) |
| Research design or examination of a claim | [Research Method Practice](<Engineering DPF Suite/RESEARCH-METHOD-PRACTICE-PRINCIPLES-FRAMEWORK.md>) |
| Agreement about meaning across models or systems | [Semantic Integration Engineering](<Engineering DPF Suite/SEMANTIC-INTEGRATION-ENGINEERING-PRINCIPLES-FRAMEWORK.md>) |
| An understandable, usable explanation | [Explanation Design](<Engineering DPF Suite/EXPLANATION-DESIGN-PRINCIPLES-FRAMEWORK.md>) |
| Direction and options under uncertainty | [Strategy](<Engineering DPF Suite/STRATEGY-PRINCIPLES-FRAMEWORK.md>) |
| Development opportunities or advice about development | [Development Opportunity Construction and Development-Direction Advising](<Engineering DPF Suite/DEVELOPMENT-OPPORTUNITY-CONSTRUCTION-AND-DEVELOPMENT-DIRECTION-ADVISING-PRINCIPLES-FRAMEWORK.md>) |
| Capability development or a learning programme | [Human Capability Development](<Engineering DPF Suite/HUMAN-CAPABILITY-DEVELOPMENT-PRINCIPLES-FRAMEWORK.md>) |
| An organisational change and its consequences | [Organization Change Engineering](<Engineering DPF Suite/ORGANIZATION-CHANGE-ENGINEERING-PRINCIPLES-FRAMEWORK.md>) |
| Administrative arrangements and authority | [Organization Administration](<Engineering DPF Suite/ORGANIZATION-ADMINISTRATION-PRINCIPLES-FRAMEWORK.md>) |
| Operating capacity, queues or commitments | [Operations Management](<Engineering DPF Suite/OPERATIONS-MANAGEMENT-PRINCIPLES-FRAMEWORK.md>) |
| Maintenance decisions for equipment functioning | [Maintenance Engineering](<Engineering DPF Suite/MAINTENANCE-ENGINEERING-PRINCIPLES-FRAMEWORK.md>) |
| Continued asset use, renewal or replacement | [Engineering Asset Management](<Engineering DPF Suite/ENGINEERING-ASSET-MANAGEMENT-PRINCIPLES-FRAMEWORK.md>) |
| Resource use, costs or operating accounts | [Management Accounting](<Engineering DPF Suite/MANAGEMENT-ACCOUNTING-PRINCIPLES-FRAMEWORK.md>) |
| Financial positions, rights or effects | [Financial Domain Modeling](<Engineering DPF Suite/FINANCIAL-DOMAIN-MODELING-PRINCIPLES-FRAMEWORK.md>) |
| Valuation, financing or liquidity | [Corporate Finance](<Engineering DPF Suite/CORPORATE-FINANCE-PRINCIPLES-FRAMEWORK.md>) |
| Music or dance practice design and development | [Music and Dance Practice Engineering](<Engineering DPF Suite/MUSIC-AND-DANCE-PRACTICE-ENGINEERING-PRINCIPLES-FRAMEWORK.md>) |

## Sources and maintenance

The [upstream introduction](Readme.md), [licensing notice](LICENSING.md) and
[Suite licensing notice](<Engineering DPF Suite/LICENSING.md>) travel with the documents.
[Snapshot provenance](upstream-snapshot.json) records the single upstream commit and each file's
SHA-256. Upstream documents retain their original bytes and links; links to GitHub `main` may
lead to a newer edition. Use the local files for the recorded snapshot.

In the devbox-setup repository, `config/upstream-docs.json` explicitly lists the imported files.
Add newly published documents there after reviewing their scope and update this index when needed.

```sh
make sync-upstream-docs
make sync-upstream-docs ARGS='--check --no-reset-drift'
make sync-upstream-docs ARGS='--ref <commit> --no-reset-drift'
```

The sync resolves one revision, downloads and validates the full manifest, then installs documents
and provenance. Handled installation failures restore previous files. If a concurrent edit or
filesystem failure prevents safe rollback, the tool preserves recovery backups and reports the
incomplete rollback. This is not a crash-atomic transaction or atomic visibility for concurrent
readers. `--check` reports drift without changing
documents or caches. `--no-reset-drift` leaves local badge caches untouched.

The existing statusline and Fish badges track Core and Narrative only. They do not establish
freshness or integrity of the whole Suite. Repository bundle tests verify the recorded hashes
without network access. Synchronisation changes the repository; normal provisioning distributes
the shared skill references to configured clients.
