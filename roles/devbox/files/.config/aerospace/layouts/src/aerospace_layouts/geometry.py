"""Absolute master sizing (Design A).

The master target is an *absolute* fraction of the focused monitor's usable area
(menu-bar/Dock excluded), read from AppKit's ``NSScreen.visibleFrame``. AeroSpace's
``%{monitor-appkit-nsscreen-screens-id}`` is a 1-based index into ``NSScreen.screens()``,
so the CLI resolves that id (``AerospaceClient.focused_monitor_appkit_id``) and maps it
here. The gap between tiles is not subtracted -- the half is an accepted approximation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, cast

from aerospace_layouts.model import MasterSide


@dataclass(frozen=True)
class MonitorDimensions:
    width: int
    height: int


ScreensProvider = Callable[[], list[MonitorDimensions]]

_WIDTH_SIDES = frozenset({MasterSide.LEFT, MasterSide.RIGHT})


class _NSSize(Protocol):
    @property
    def width(self) -> float: ...
    @property
    def height(self) -> float: ...


class _NSRect(Protocol):
    @property
    def size(self) -> _NSSize: ...


class _NSScreen(Protocol):
    def visibleFrame(self) -> _NSRect: ...


class _NSScreenClass(Protocol):
    def screens(self) -> list[_NSScreen]: ...


def appkit_screens() -> list[MonitorDimensions]:
    import importlib

    # pyobjc is a runtime-only dep with no static `NSScreen` symbol, so resolve it through
    # the dynamic module (ModuleType.__getattr__) and cast to a typed boundary. Lazy import
    # keeps the unit tests (which inject a screens provider) headless.
    ns_screen = cast("_NSScreenClass", importlib.import_module("AppKit").NSScreen)
    return [
        MonitorDimensions(round(frame.size.width), round(frame.size.height))
        for frame in (screen.visibleFrame() for screen in ns_screen.screens())
    ]


def focused_monitor_dimensions(
    appkit_id: int, screens: ScreensProvider = appkit_screens
) -> MonitorDimensions | None:
    all_screens = screens()
    index = appkit_id - 1
    if not 0 <= index < len(all_screens):
        return None
    return all_screens[index]


def master_axis(side: MasterSide) -> str:
    return "width" if side in _WIDTH_SIDES else "height"


def master_extent(dimensions: MonitorDimensions, side: MasterSide, ratio: float = 0.5) -> int:
    usable = dimensions.width if side in _WIDTH_SIDES else dimensions.height
    return round(ratio * usable)
