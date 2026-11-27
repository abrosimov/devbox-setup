#!/usr/bin/env python3
# Print `true` when this login session runs with separate Spaces per display and
# `false` otherwise, by asking SkyLight exactly what Rift asks at start
# (acsandmann/rift src/sys/screen.rs). NSScreen.screensHaveSeparateSpaces can
# report false while that answer is true.
#
# Self-contained, standard library only — run by configure_window_manager.yml
# with the playbook's own interpreter. A failure exits 1 with nothing on stdout,
# which the playbook reads as "not ready". Tests: tests/scripts/.
from __future__ import annotations

import ctypes
import sys
from typing import Final

SKYLIGHT: Final = "/System/Library/PrivateFrameworks/SkyLight.framework/SkyLight"
SEPARATE_SPACES_MODE: Final = 1


def space_management_mode(library: str = SKYLIGHT) -> int:
    skylight = ctypes.CDLL(library)
    main_connection_id = skylight.SLSMainConnectionID
    main_connection_id.argtypes = []
    main_connection_id.restype = ctypes.c_int
    get_space_management_mode = skylight.SLSGetSpaceManagementMode
    get_space_management_mode.argtypes = [ctypes.c_int]
    get_space_management_mode.restype = ctypes.c_int
    return int(get_space_management_mode(main_connection_id()))


def main() -> int:
    try:
        mode = space_management_mode()
    except (OSError, AttributeError) as err:
        print(f"session-separate-spaces: cannot ask SkyLight: {err}", file=sys.stderr)
        return 1
    print("true" if mode == SEPARATE_SPACES_MODE else "false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
