# Bash command sample statistics

Sample size: **459** bash tool_use commands across 25 most recent sessions.

Source CSV: `all-commands-classified.csv` in the same directory.

---

## Counts by shape

| Shape | Count | % of total |
|---|---:|---:|
| redirected | 152 | 33.1% |
| piped | 93 | 20.3% |
| cd-prefix | 72 | 15.7% |
| chained | 65 | 14.2% |
| bare | 49 | 10.7% |
| env-prefix | 19 | 4.1% |
| multiline | 9 | 2.0% |

## Top 10 most-used base commands (first segment, env-prefix stripped)

| Base command | Count |
|---|---:|
| `grep` | 135 |
| `cd` | 76 |
| `ls` | 74 |
| `git` | 56 |
| `find` | 26 |
| `cat` | 21 |
| `rg` | 14 |
| `uv` | 9 |
| `../base/.venv/bin/python` | 7 |
| `wc` | 6 |

## Top 10 most-used (base, subcommand) pairs

| Base + sub | Count |
|---|---:|
| `grep -n` | 52 |
| `grep -rn` | 45 |
| `cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints"` | 39 |
| `cd ~/Work/mlops-be/OICM-7329_migration_for_masking_encrypted_blueprints` | 23 |
| `ls -la` | 17 |
| `git diff` | 17 |
| `grep -nE` | 12 |
| `rg -n` | 12 |
| `git status` | 10 |
| `uv run` | 9 |

## Counts of specific patterns within commands

| Pattern | Count | % of total |
|---|---:|---:|
| `cd "$...` | 43 | 9.4% |
| `&&` | 139 | 30.3% |
| `2>&1` | 90 | 19.6% |
| `| head` | 233 | 50.8% |
| `| tail` | 37 | 8.1% |
| `| wc` | 6 | 1.3% |
| `>/dev/null` | 211 | 46.0% |
| `env-prefix` | 20 | 4.4% |
| `$(...)` | 8 | 1.7% |
| `heredoc <<` | 0 | 0.0% |

## Allow-list simulation

Commands where the FIRST segment's head token (after env-prefix stripping) does NOT appear in any base allow rule, OR where at least one chained segment's head does not match: **97** of 459 (21.1%).

Caveats:
- This simulation is **conservative** (false-negative biased): it accepts any matching base head even if the subcommand-specific rule would still deny (e.g. `git rebase` matches `git` base but is denied by `Bash(git rebase *)` deny rule). Real prompt rate is **higher** than this number.
- Real harness matcher is prefix-based on the full command, not just the head. A bare `go test ./...` may match `Bash(go test *)` but a chained `go test ./... && go vet ./...` will not match either rule wholesale; each segment is matched independently.
- Compound chains, heredocs, and env-prefix lead-segments are the major false-positives in the allow-set: the head matches but the full command does not — real prompt rate is higher than reported here.
