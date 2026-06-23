"""Pytest plumbing for the integration harness.

Adds the parent ``bin/`` directory to ``sys.path`` so the harness can import
``_claude_lib`` (used by anonymise/extract helpers) without relying on the
package being installed.
"""

from __future__ import annotations

import sys
from pathlib import Path

BIN_DIR = Path(__file__).resolve().parent.parent
if str(BIN_DIR) not in sys.path:
    sys.path.insert(0, str(BIN_DIR))
