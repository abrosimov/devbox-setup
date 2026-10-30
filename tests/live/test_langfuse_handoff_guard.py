"""The handoff harness obtains the edge the playbook installs, or reports why not.

Hermetic: collected with the other guards, so the checksum refusal and the
platform refusal are proven without a download or a binary.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest
from generation import REPO_ROOT
from langfuse_handoff import (
    EdgePin,
    EdgeUnavailableError,
    SpanIdentity,
    decode_spans,
    edge_pin,
    linux_asset,
    verified_release_asset,
)

if TYPE_CHECKING:
    from pathlib import Path

INSTALL_TASK = REPO_ROOT / "roles/devbox/tasks/darwin/install_otelbox_edge.yml"
PIN = EdgePin(version="9.9.9", release_base="https://example.test/releases/download")
ASSET = "otelcol-otelbox_linux_amd64"
BINARY = b"\x7fELF pinned edge"


def varint(value: int) -> bytes:
    encoded = bytearray()
    while True:
        low, value = value & 0x7F, value >> 7
        encoded.append(low | (0x80 if value else 0))
        if not value:
            return bytes(encoded)


def length_delimited(number: int, payload: bytes) -> bytes:
    return varint(number << 3 | 2) + varint(len(payload)) + payload


def fixed64(number: int, value: int) -> bytes:
    return varint(number << 3 | 1) + value.to_bytes(8, "little")


def span(trace_id: bytes, span_id: bytes, parent: bytes, start: int, end: int) -> bytes:
    return (
        length_delimited(1, trace_id)
        + length_delimited(2, span_id)
        + length_delimited(3, b"")
        + length_delimited(4, parent)
        + length_delimited(5, b"Conversational Turn " * 10)
        + varint(6 << 3)
        + varint(1)
        + fixed64(7, start)
        + fixed64(8, end)
    )


def test_spans_are_read_off_an_otlp_trace_request() -> None:
    first = span(b"\x01" * 16, b"\x02" * 8, b"\x03" * 8, 10**18, 10**18 + 5)
    second = span(b"\x04" * 16, b"\x05" * 8, b"", 7, 9)
    scope = length_delimited(1, length_delimited(1, b"langfuse"))
    scope += length_delimited(2, first) + length_delimited(2, second)
    resource = length_delimited(1, b"") + length_delimited(2, scope)
    request = length_delimited(1, resource) + length_delimited(1, resource)

    spans = decode_spans(request)

    one = SpanIdentity("01" * 16, "02" * 8, "03" * 8, 10**18, 10**18 + 5)
    other = SpanIdentity("04" * 16, "05" * 8, "", 7, 9)
    assert spans == [one, other, one, other]


def test_the_pin_is_the_one_the_install_task_downloads() -> None:
    pin = edge_pin()
    task = INSTALL_TASK.read_text(encoding="utf-8")
    assert "devbox_packages.otelbox_edge.release_base }}/v{{" in task
    assert 'checksum: "sha256:{{ devbox_otelbox_edge_asset_base }}.sha256"' in task
    assert pin.url(ASSET) == f"{pin.release_base}/v{pin.version}/{ASSET}"
    assert pin.release_base.startswith("https://")


def serve(files: dict[str, bytes], fetched: list[str]):
    def opener(url: str, timeout: float) -> bytes:
        assert timeout > 0
        fetched.append(url)
        return files[url]

    return opener


def test_an_asset_matching_its_published_digest_is_installed_and_reused(tmp_path: Path) -> None:
    fetched: list[str] = []
    digest = hashlib.sha256(BINARY).hexdigest()
    opener = serve(
        {PIN.url(ASSET): BINARY, PIN.url(f"{ASSET}.sha256"): f"{digest}\n".encode()}, fetched
    )

    installed = verified_release_asset(PIN, ASSET, tmp_path, opener)
    again = verified_release_asset(PIN, ASSET, tmp_path, opener)

    assert installed.read_bytes() == BINARY
    assert installed.stat().st_mode & 0o111
    assert again == installed
    assert fetched == [PIN.url(f"{ASSET}.sha256"), PIN.url(ASSET)]


def test_an_asset_whose_digest_differs_is_refused(tmp_path: Path) -> None:
    opener = serve(
        {PIN.url(ASSET): BINARY, PIN.url(f"{ASSET}.sha256"): b"0" * 64},
        [],
    )

    with pytest.raises(EdgeUnavailableError, match="checksum mismatch"):
        verified_release_asset(PIN, ASSET, tmp_path, opener)
    assert not list(tmp_path.rglob(ASSET))


def test_a_digest_file_that_is_not_one_bare_digest_is_refused(tmp_path: Path) -> None:
    digest = hashlib.sha256(BINARY).hexdigest()
    opener = serve(
        {PIN.url(ASSET): BINARY, PIN.url(f"{ASSET}.sha256"): f"{digest}  {ASSET}\n".encode()},
        [],
    )

    with pytest.raises(EdgeUnavailableError, match="bare SHA-256"):
        verified_release_asset(PIN, ASSET, tmp_path, opener)


def test_macos_is_reported_as_unable_to_trust_a_test_ca() -> None:
    with pytest.raises(EdgeUnavailableError, match="SSL_CERT_FILE"):
        linux_asset("Darwin", "arm64")


def test_an_architecture_without_a_release_asset_is_reported() -> None:
    with pytest.raises(EdgeUnavailableError, match="aarch64"):
        linux_asset("Linux", "aarch64")


def test_linux_amd64_maps_to_the_published_asset() -> None:
    assert linux_asset("Linux", "x86_64") == ASSET
