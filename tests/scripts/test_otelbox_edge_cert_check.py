from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import pytest
from otelbox_edge import cert_check

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "scripts/otelbox-edge-cert-check.py"


@dataclass(frozen=True)
class CertificatePair:
    cert: Path
    key: Path


def _run(*paths: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(CHECKER), *(str(path) for path in paths)],
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def _generate_pair(root: Path, name: str) -> CertificatePair:
    key = root / f"{name}.key"
    cert = root / f"{name}.crt"
    subprocess.run(
        ["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", key],
        check=True,
        capture_output=True,
        timeout=30,
    )
    subprocess.run(
        [
            "openssl",
            "req",
            "-new",
            "-x509",
            "-key",
            key,
            "-out",
            cert,
            "-days",
            "1",
            "-subj",
            f"/CN={name}",
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return CertificatePair(cert=cert, key=key)


@pytest.fixture
def pair(tmp_path: Path) -> CertificatePair:
    return _generate_pair(tmp_path, "client")


class TestCertificateChecker:
    def test_valid_pair_is_silent(self, pair: CertificatePair) -> None:
        result = _run(pair.cert, pair.key)

        assert result.returncode == 0
        assert result.stdout == ""
        assert result.stderr == ""

    def test_mismatched_pair_exits_78(self, tmp_path: Path) -> None:
        first = _generate_pair(tmp_path, "first")
        second = _generate_pair(tmp_path, "second")

        result = _run(first.cert, second.key)

        assert result.returncode == 78
        assert "do not match" in result.stderr

    @pytest.mark.parametrize("broken", ["certificate", "key"])
    def test_malformed_material_exits_78(self, pair: CertificatePair, broken: str) -> None:
        path = pair.cert if broken == "certificate" else pair.key
        path.write_text("not PEM\n", encoding="utf-8")

        result = _run(pair.cert, pair.key)

        assert result.returncode == 78

    def test_missing_file_exits_78(self, pair: CertificatePair, tmp_path: Path) -> None:
        result = _run(pair.cert, tmp_path / "missing.key")

        assert result.returncode == 78
        assert "missing or unreadable" in result.stderr

    @pytest.mark.parametrize("arguments", [[], ["one"], ["one", "two", "three"]])
    def test_bad_arity_exits_64(self, arguments: list[str]) -> None:
        result = subprocess.run(
            [str(CHECKER), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 64
        assert result.stderr == "usage: otelbox-edge-cert-check.py CERT_FILE KEY_FILE\n"

    def test_missing_openssl_exits_69(
        self, pair: CertificatePair, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stderr = StringIO()
        monkeypatch.setattr(cert_check, "resolve_openssl", lambda _environment: None)

        result = cert_check.main(
            [str(pair.cert), str(pair.key)],
            environment={"PATH": ""},
            stderr=stderr,
        )

        assert result == 69
        assert stderr.getvalue() == "otelbox-edge-cert-check: no usable openssl\n"
