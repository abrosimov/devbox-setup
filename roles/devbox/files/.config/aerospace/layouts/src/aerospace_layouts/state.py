from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast


def _empty_workspaces() -> dict[str, int]:
    return {}


@dataclass
class State:
    workspaces: dict[str, int] = field(default_factory=_empty_workspaces)


def default_state_path() -> Path:
    base = os.environ.get("XDG_STATE_HOME")
    root = Path(base) if base else Path.home() / ".local" / "state"
    return root / "aerospace-layouts" / "state.json"


def load_state(path: Path) -> State:
    try:
        raw = cast("dict[str, object]", json.loads(path.read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError):
        # Missing or corrupt state resets to empty. AeroSpace rebuilds trees from
        # scratch on restart, so a stale/absent index is harmless.
        return State()
    workspaces = raw.get("workspaces")
    if not isinstance(workspaces, dict):
        return State()
    parsed: dict[str, int] = {}
    for name, value in cast("dict[str, object]", workspaces).items():
        if isinstance(value, dict):
            index = cast("dict[str, object]", value).get("layout_index")
            if isinstance(index, int):
                parsed[str(name)] = index
    return State(parsed)


def save_state(path: Path, state: State) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "workspaces": {name: {"layout_index": idx} for name, idx in state.workspaces.items()}
    }
    tmp = path.parent / f".{path.name}.tmp"
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def get_index(state: State, workspace: str) -> int:
    return state.workspaces.get(workspace, 0)


def set_index(state: State, workspace: str, index: int) -> None:
    state.workspaces[workspace] = index
