from __future__ import annotations

import tomllib

from ai_config.adapters import ConfigurationFormat
from ai_config.document import render_document


class TestTomlSourcePreservation:
    def test_only_rerenders_changed_top_level_roots(self) -> None:
        source = (
            b'# Managed configuration.\nmodel = "old"\n\n'
            b"[features]\nmemories = true\n\n"
            b'[[hooks.PreToolUse]]\nmatcher = ".*"\n'
            b"[[hooks.PreToolUse.hooks]]\n"
            b'type = "command"\ncommand = "logger"\n'
        )
        configuration = tomllib.loads(source.decode())
        configuration["model"] = "new"
        configuration["plugins"] = {"browser@example": {"enabled": True}}

        rendered = render_document(
            configuration,
            ConfigurationFormat.TOML,
            source=source,
        )

        hook_block = (
            b'[[hooks.PreToolUse]]\nmatcher = ".*"\n'
            b"[[hooks.PreToolUse.hooks]]\n"
            b'type = "command"\ncommand = "logger"\n'
        )
        assert hook_block in rendered
        assert b'# Managed configuration.\nmodel = "new"\n' in rendered
        assert tomllib.loads(rendered.decode()) == configuration

    def test_removes_only_the_deleted_top_level_root(self) -> None:
        source = (
            b"""model = "current"\n\n[desktop]\nfont_size = 14\n\n[features]\nmemories = true\n"""
        )
        configuration = tomllib.loads(source.decode())
        configuration.pop("desktop")

        rendered = render_document(
            configuration,
            ConfigurationFormat.TOML,
            source=source,
        )

        assert b"[desktop]" not in rendered
        assert b"[features]\nmemories = true\n" in rendered
        assert tomllib.loads(rendered.decode()) == configuration

    def test_preserves_trivia_before_the_next_unchanged_table(self) -> None:
        source = (
            b"[changed]\nvalue = 'old'\n"
            b"\n# This separator belongs at the table boundary.\n\n"
            b"[unchanged]\nenabled = true\n"
        )
        configuration = tomllib.loads(source.decode())
        changed = configuration["changed"]
        assert isinstance(changed, dict)
        changed["value"] = "new"

        rendered = render_document(
            configuration,
            ConfigurationFormat.TOML,
            source=source,
        )

        assert b"\n# This separator belongs at the table boundary.\n\n[unchanged]\n" in rendered
        assert tomllib.loads(rendered.decode()) == configuration

    def test_replaces_the_complete_multiline_top_level_assignment(self) -> None:
        source = (
            b"changed = [\n  'old',\n  'values',\n]\n"
            b"\n# Keep this boundary note.\n\n"
            b"[unchanged]\nenabled = true\n"
        )
        configuration = tomllib.loads(source.decode())
        configuration["changed"] = ["new"]

        rendered = render_document(
            configuration,
            ConfigurationFormat.TOML,
            source=source,
        )

        assert b"'old'" not in rendered
        assert b"\n# Keep this boundary note.\n\n[unchanged]\n" in rendered
        assert tomllib.loads(rendered.decode()) == configuration

    def test_multiline_string_content_is_not_mistaken_for_a_table(self) -> None:
        source = (
            b'changed = """\nold\n[not-a-table]\n"""\n'
            b"\n# Keep this string boundary.\n\n"
            b"[unchanged]\nenabled = true\n"
        )
        configuration = tomllib.loads(source.decode())
        configuration["changed"] = "new"

        rendered = render_document(
            configuration,
            ConfigurationFormat.TOML,
            source=source,
        )

        assert b"[not-a-table]" not in rendered
        assert b"\n# Keep this string boundary.\n\n[unchanged]\n" in rendered
        assert tomllib.loads(rendered.decode()) == configuration
