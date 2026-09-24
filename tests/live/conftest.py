from __future__ import annotations

import os

# The engine tests spawn real `claude` / `codex` / `agy` binaries. Collecting them
# by default would make `make test`, `make qa` and any bare `pytest` depend on a
# provisioned workstation. test_throwaway_guard.py stays collected: it is hermetic
# and it is what proves the safety guard around these tests still fires.
if os.environ.get("DEVBOX_LIVE_ENGINE_TESTS") != "1":
    collect_ignore_glob = ["test_live_*.py"]
