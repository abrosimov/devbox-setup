from __future__ import annotations

import pytest

from aerospace_layouts.geometry import (
    MonitorDimensions,
    ScreensProvider,
    focused_monitor_dimensions,
    master_axis,
    master_extent,
)
from aerospace_layouts.model import MasterSide


def _screens(*dims: MonitorDimensions) -> ScreensProvider:
    return lambda: list(dims)


def test_appkit_id_maps_one_based_into_screens():
    provider = _screens(MonitorDimensions(1920, 1080), MonitorDimensions(2560, 1440))
    assert focused_monitor_dimensions(1, provider) == MonitorDimensions(1920, 1080)
    assert focused_monitor_dimensions(2, provider) == MonitorDimensions(2560, 1440)


def test_appkit_id_out_of_range_returns_none():
    provider = _screens(MonitorDimensions(1920, 1080))
    assert focused_monitor_dimensions(0, provider) is None
    assert focused_monitor_dimensions(2, provider) is None


@pytest.mark.parametrize(
    ("side", "axis", "expected"),
    [
        (MasterSide.LEFT, "width", 960),
        (MasterSide.RIGHT, "width", 960),
        (MasterSide.TOP, "height", 540),
        (MasterSide.BOTTOM, "height", 540),
    ],
)
def test_master_extent_is_half_of_the_axis_the_master_side_spans(
    side: MasterSide, axis: str, expected: int
):
    dims = MonitorDimensions(1920, 1080)
    assert master_axis(side) == axis
    assert master_extent(dims, side) == expected


def test_master_extent_honours_ratio_and_rounds():
    assert master_extent(MonitorDimensions(1917, 1080), MasterSide.LEFT, ratio=0.6) == 1150
