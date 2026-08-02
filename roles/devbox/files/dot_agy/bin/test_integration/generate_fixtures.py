#!/usr/bin/env python3
"""Generate synthetic hook fixtures via hypothesis strategies.

Materialises N examples per lifecycle bucket, anonymises them, and writes
them under ``fixtures/<lifecycle>/synth_<sha8>.json``. The ``synth_`` prefix
distinguishes generated fixtures from ``extract_fixtures.py`` output.

Deterministic with respect to ``--seed``: same seed + same count + same
strategy versions ⇒ same files on disk. This makes the regenerate target
reproducible across machines / CI.

Stdlib + hypothesis. The hypothesis dependency is dev-only (declared in
``pyproject.toml``), so this script is not part of the deployed runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))
sys.path.insert(0, str(THIS_DIR))

from test_integration.anonymise import anonymise
from test_integration.strategies import LIFECYCLE_STRATEGIES


def _stable_sha8(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def _materialise_examples(
    strategy: st.SearchStrategy[dict[str, object]],
    count: int,
    seed: int,
) -> list[dict[str, object]]:
    collected: list[dict[str, object]] = []

    # hypothesis doesn't expose a public "draw N examples" API; the documented
    # pattern is to embed the strategy inside a settings(max_examples=count)
    # test, then capture each example via assertion side effect. The test
    # itself always passes — we use the framework purely as an example pump.
    @settings(
        max_examples=count,
        deadline=None,
        database=None,
        derandomize=True,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.large_base_example],
    )
    @given(payload=strategy)
    def _pump(payload: dict[str, object]) -> None:
        collected.append(payload)

    # ``derandomize=True`` + the seed-derived test name gives reproducible
    # output: hypothesis derives its PRNG from the test's qualified name when
    # derandomize is set. We rename the function to include the seed so two
    # runs with different seeds yield different example sets.
    _pump.__name__ = f"_pump_seed_{seed}"
    _pump.__qualname__ = f"_pump_seed_{seed}"
    _pump()
    return collected


def generate_for_lifecycle(
    lifecycle: str,
    strategy: st.SearchStrategy[dict[str, object]],
    count: int,
    out_root: Path,
    seed: int,
) -> int:
    bucket_dir = out_root / lifecycle
    bucket_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    examples = _materialise_examples(strategy, count, seed)
    for raw in examples:
        anon = anonymise(raw)
        sha = _stable_sha8(anon)
        target = bucket_dir / f"synth_{sha}.json"
        if target.exists():
            continue
        target.write_text(json.dumps(anon, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written += 1
    return written


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate synthetic hook fixtures via hypothesis strategies.",
    )
    parser.add_argument(
        "--lifecycle",
        action="append",
        help="Lifecycle to generate for (may repeat). Omit with --all for every lifecycle.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate for every lifecycle in LIFECYCLE_STRATEGIES.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=50,
        help="Examples per lifecycle (default: 50).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic seed (default: 42).",
    )
    parser.add_argument(
        "--out",
        default=str(THIS_DIR / "fixtures"),
        help="Output directory for fixture buckets (default: ./fixtures).",
    )
    args = parser.parse_args()

    if not args.all and not args.lifecycle:
        parser.error("specify --all or one or more --lifecycle <name>")

    lifecycles: list[str] = (
        sorted(LIFECYCLE_STRATEGIES.keys()) if args.all else list(args.lifecycle)
    )

    out_root = Path(args.out).expanduser()
    out_root.mkdir(parents=True, exist_ok=True)

    counts: Counter[str] = Counter()
    for lifecycle in lifecycles:
        strategy = LIFECYCLE_STRATEGIES.get(lifecycle)
        if strategy is None:
            sys.stderr.write(f"unknown lifecycle: {lifecycle}\n")
            return 2
        counts[lifecycle] = generate_for_lifecycle(
            lifecycle,
            strategy,
            args.count,
            out_root,
            args.seed,
        )

    sys.stdout.write("Generated synthetic fixtures per bucket:\n")
    for bucket in sorted(counts):
        sys.stdout.write(f"  {bucket}: {counts[bucket]}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
