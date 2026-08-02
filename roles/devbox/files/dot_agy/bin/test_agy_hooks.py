import json
from pathlib import Path


def test_agy_hooks_no_duplicates():
    path = Path(__file__).resolve().parents[2] / "dot_agy/config/hooks.json.j2"
    with path.open() as stream:
        data = json.load(stream)
    seen = set()
    for h in data.values():
        key = (h["event"], h["handler"]["command"])
        assert key not in seen, f"Duplicate hook registration found for {key}"
        seen.add(key)
