from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_SOURCES = [
    REPO_ROOT / "scripts/otelbox-edge-cert-check.py",
    REPO_ROOT / "scripts/otelbox-edge-config.py",
    REPO_ROOT / "scripts/otelbox-edge-test.py",
    *(REPO_ROOT / "scripts/otelbox_edge").glob("*.py"),
]


class TestPythonCompatibility:
    def test_all_otelbox_edge_sources_parse_as_python_39(self) -> None:
        failures: list[str] = []
        for path in PYTHON_SOURCES:
            try:
                ast.parse(
                    path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 9)
                )
            except SyntaxError as error:
                failures.append(f"{path.relative_to(REPO_ROOT)}: {error}")

        assert failures == []
