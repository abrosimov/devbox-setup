"""Phase 2 seam: absolute master sizing.

Deliberately empty for the MVP. The current master ratio is a *relative* nudge
(Design R): after `balance-sizes`, the master is widened by a fixed number of
`resize smart +STEP` steps (see ``layouts.tile``).

Phase 2 will compute an *absolute* master fraction from the monitor width. That
requires reading display bounds (e.g. CGDisplayBounds via a helper, since
``aerospace list-monitors`` exposes no width and there is no way to read back
window geometry) and converting a target fraction into a points delta. None of
that is implemented here yet -- this module marks where it will live.
"""

from __future__ import annotations

# TODO(phase-2): monitor-width -> absolute master fraction -> resize points delta.
