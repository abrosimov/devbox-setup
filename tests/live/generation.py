"""Generate engine configuration the way the playbook does, into a throwaway home."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Final

from jinja2 import Environment, StrictUndefined
from jinja2.utils import select_autoescape

if TYPE_CHECKING:
    from collections.abc import Mapping

    from throwaway import ThrowawayHome

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
AI_CONFIG: Final = REPO_ROOT / "scripts" / "ai-config"
DEFAULT_PROFILE: Final = "personal"
_APPLY_TIMEOUT_SECONDS: Final = 300.0


class GenerationError(RuntimeError):
    pass


def apply_engine(
    engine: str,
    home: ThrowawayHome,
    *,
    profile: str = DEFAULT_PROFILE,
) -> Mapping[str, object]:
    """Run the same `scripts/ai-config apply` invocation the playbook runs."""
    completed = subprocess.run(
        [
            str(AI_CONFIG),
            "apply",
            engine,
            "--repo-root",
            str(REPO_ROOT),
            "--home",
            str(home.path),
            "--profile",
            profile,
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=_APPLY_TIMEOUT_SECONDS,
        env=home.environment(),
        cwd=REPO_ROOT,
        check=False,
    )
    if completed.returncode != 0:
        message = (
            f"ai-config apply {engine} exited {completed.returncode}\n"
            f"stdout: {completed.stdout}\nstderr: {completed.stderr}"
        )
        raise GenerationError(message)
    try:
        report: object = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        message = f"ai-config apply {engine} did not emit JSON: {completed.stdout}"
        raise GenerationError(message) from error
    if not isinstance(report, dict):
        message = f"ai-config apply {engine} emitted a non-object report: {completed.stdout}"
        raise GenerationError(message)
    return report


def render_ansible_template(source: Path, home: ThrowawayHome) -> str:
    """Render a role template whose only Ansible-ism is `lookup('env', 'HOME')`.

    The Ansible `template` module evaluates that lookup against the controller's
    environment, which is the environment the engine is later started with — so
    binding it to the throwaway home reproduces the deployed text. Any other
    lookup raises rather than rendering something the playbook would not produce.
    """
    environment = home.environment()

    def lookup(plugin: str, name: str) -> str:
        if plugin != "env":
            message = f"{source} uses the {plugin!r} lookup, which this harness cannot reproduce"
            raise GenerationError(message)
        return environment[name]

    jinja = Environment(
        undefined=StrictUndefined,
        autoescape=select_autoescape(enabled_extensions=(), default_for_string=False),
        keep_trailing_newline=True,
    )
    return jinja.from_string(source.read_text(encoding="utf-8")).render(lookup=lookup)
