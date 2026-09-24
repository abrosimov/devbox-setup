from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

import yaml
from jinja2 import Environment, StrictUndefined
from jinja2 import TemplateError as JinjaTemplateError
from jinja2.utils import select_autoescape

from .core import MissingValue

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .model import FieldPath, SemanticSnapshot

type TemplateVariables = Mapping[str, object]

_DEFAULTS_DIRECTORY = Path("roles/devbox/defaults/main")
_PROFILES_DIRECTORY = Path("profiles")

# A probe string wraps the real one rather than replacing it, so it is longer and
# therefore always differs, whatever the real value happens to be. Wrapping on both
# sides also keeps `{{ x[0] }}` and `{{ x[-1] }}` distinguishable. The marker stays
# printable because JSON rejects unescaped control characters inside a string.
_PROBE_PREFIX = "<ai-config-probe>"
_PROBE_SUFFIX = "</ai-config-probe>"


class TemplateError(ValueError):
    pass


def load_template_variables(repo_root: Path, profile: str) -> TemplateVariables:
    """Role defaults overlaid by the profile selected with --profile.

    Values are taken verbatim: a default whose own value is a Jinja expression
    (``devbox_sudo_password``, ``devbox_user.ssh_pass_phrase``) stays inert text
    rather than being evaluated, so no keychain lookup can reach a rendered
    document through this context.
    """
    defaults = repo_root / _DEFAULTS_DIRECTORY
    variables: dict[str, object] = {}
    if defaults.is_dir():
        for path in sorted(defaults.glob("*.yml")):
            variables.update(_load_variable_file(path))
    overlay = repo_root / _PROFILES_DIRECTORY / f"{profile}.yml"
    if overlay.is_file():
        variables.update(_load_variable_file(overlay))
        return variables
    # A tree carrying role defaults must also carry the selected profile: without
    # the overlay every per-profile value would silently render its placeholder
    # default. A tree with neither is an isolated fixture holding literals only.
    if defaults.is_dir():
        message = f"no variables for profile: {overlay}"
        raise TemplateError(message)
    return variables


def probe_variables(variables: TemplateVariables) -> TemplateVariables:
    """A type-preserving alternative context in which every variable differs.

    Rendering the same source against both contexts reveals which leaf paths an
    expression produced: those are exactly the paths whose value differs.
    """
    return {name: _probe_value(value) for name, value in variables.items()}


def render_source(source: bytes, variables: TemplateVariables) -> bytes:
    try:
        text = source.decode()
    except UnicodeDecodeError as error:
        message = "repository source must be UTF-8"
        raise TemplateError(message) from error
    environment = Environment(
        undefined=StrictUndefined,
        # Escaping is disabled for every source: the output is JSON or TOML, and
        # HTML entities would corrupt values such as `a && b` or `"quoted"`.
        autoescape=select_autoescape(enabled_extensions=(), default_for_string=False),
        keep_trailing_newline=True,
    )
    try:
        return environment.from_string(text).render(variables).encode()
    except JinjaTemplateError as error:
        message = f"cannot render repository source: {error}"
        raise TemplateError(message) from error


def divergent_paths(left: SemanticSnapshot, right: SemanticSnapshot) -> frozenset[FieldPath]:
    """Leaf paths the two documents disagree on, counting absence as a value."""
    left_fields = {field.path: field.value for field in left.semantic_fields()}
    right_fields = {field.path: field.value for field in right.semantic_fields()}
    return frozenset(
        path
        for path in left_fields.keys() | right_fields.keys()
        if left_fields.get(path, MissingValue.MISSING)
        != right_fields.get(path, MissingValue.MISSING)
    )


def _load_variable_file(path: Path) -> TemplateVariables:
    try:
        loaded: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        message = f"cannot read template variables: {path}"
        raise TemplateError(message) from error
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        message = f"template variable files must hold a mapping: {path}"
        raise TemplateError(message)
    mapping = cast("dict[object, object]", loaded)
    if not all(isinstance(name, str) for name in mapping):
        message = f"template variable names must be strings: {path}"
        raise TemplateError(message)
    return cast("TemplateVariables", mapping)


def _probe_value(value: object) -> object:
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return value + 1.0
    if isinstance(value, list):
        items = cast("list[object]", value)
        return [_probe_value(item) for item in items]
    if isinstance(value, dict):
        mapping = cast("dict[object, object]", value)
        return {key: _probe_value(item) for key, item in mapping.items()}
    return f"{_PROBE_PREFIX}{value}{_PROBE_SUFFIX}"
