from __future__ import annotations

import logging

from aerospace_layouts.aerospace import AerospaceClient
from aerospace_layouts.model import Command

logger = logging.getLogger("aerospace_layouts")


def render_eval_batch(commands: list[Command]) -> str:
    # `;` runs each sub-command sequentially regardless of exit, so tolerate_nonzero no-op
    # `layout` commands never abort the batch (AeroSpace >= 0.21.0-Beta `eval` semantics).
    return " ; ".join(" ".join(command.to_argv()) for command in commands)


def run_eval(client: AerospaceClient, commands: list[Command]) -> None:
    if not commands:
        return
    argv = ["eval", render_eval_batch(commands)]
    result = client.run_argv(argv)
    logger.info("eval rc=%d argv=%s", result.returncode, " ".join(argv))
    if result.returncode != 0 and result.stderr.strip():
        # A batched `layout` no-op legitimately makes eval non-zero; master reflow is
        # best-effort for a keybinding, so warn rather than raise.
        logger.warning("eval stderr: %s", result.stderr.strip())
