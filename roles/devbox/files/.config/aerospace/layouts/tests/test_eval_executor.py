from __future__ import annotations

from aerospace_layouts.aerospace import AerospaceClient
from aerospace_layouts.executor import render_eval_batch, run_eval
from aerospace_layouts.model import (
    Command,
    balance_sizes,
    join_with,
    resize_to,
    set_layout,
)

from .conftest import FakeRunner


def _tile_batch() -> list[Command]:
    # A representative tile apply (n=3, master LEFT) with an absolute master extent.
    return [
        set_layout("h_tiles", 10),
        join_with("left", 12),
        set_layout("v_tiles", 11),
        balance_sizes("3"),
        resize_to("width", 960, 10),
    ]


def test_render_joins_commands_with_semicolons():
    assert render_eval_batch(_tile_batch()) == (
        "layout h_tiles --window-id 10 ; "
        "join-with left --window-id 12 ; "
        "layout v_tiles --window-id 11 ; "
        "balance-sizes --workspace 3 ; "
        "resize width 960 --window-id 10"
    )


def test_run_eval_issues_one_eval_call_with_the_batch_string():
    runner = FakeRunner()
    run_eval(AerospaceClient(runner), _tile_batch())
    assert len(runner.calls) == 1
    assert runner.calls[0][0] == "eval"
    assert runner.calls[0][1] == render_eval_batch(_tile_batch())


def test_run_eval_empty_list_issues_no_call():
    runner = FakeRunner()
    run_eval(AerospaceClient(runner), [])
    assert runner.calls == []


def test_render_uses_height_axis_for_horizontal_master_resize():
    assert render_eval_batch([resize_to("height", 540, 10)]) == "resize height 540 --window-id 10"
