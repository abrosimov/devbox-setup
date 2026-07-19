from __future__ import annotations

import logging

from aerospace_layouts.aerospace import AerospaceClient
from aerospace_layouts.model import Command

logger = logging.getLogger("aerospace_layouts")


def run_commands(client: AerospaceClient, commands: list[Command]) -> None:
    for command in commands:
        logger.debug("exec: %s", " ".join(command.to_argv()))
        client.execute(command)
