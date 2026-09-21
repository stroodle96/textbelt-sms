# Copyright (c) 2026 Daniel Strodl
"""Tests for the release version contract."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from scripts.release_contract import validate_release_version

if TYPE_CHECKING:
    from pathlib import Path


def write_manifest(tmp_path: Path, version: object = "0.2.0") -> Path:
    """Write a minimal integration manifest for a contract test."""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"version": version}), encoding="utf-8")
    return manifest_path


def test_valid_version_returns_prefixed_tag(tmp_path: Path) -> None:
    """A strict manifest version produces its v-prefixed release tag."""
    assert validate_release_version("0.2.0", write_manifest(tmp_path)) == "v0.2.0"


@pytest.mark.parametrize(
    "version",
    ["v0.2.0", "0.2", "0.2.0b1", "01.2.3", "0.02.3", "0.2.03", "0.2.0+build"],
)
def test_invalid_versions_are_rejected(tmp_path: Path, version: str) -> None:
    """Only strict numeric MAJOR.MINOR.PATCH versions are accepted."""
    with pytest.raises(ValueError, match=r"strict MAJOR\.MINOR\.PATCH"):
        validate_release_version(version, write_manifest(tmp_path))


def test_manifest_mismatch_is_rejected(tmp_path: Path) -> None:
    """The requested version must equal the manifest version exactly."""
    pattern = r"requested 0\.2\.0, manifest contains 0\.1\.0"
    with pytest.raises(ValueError, match=pattern):
        validate_release_version("0.2.0", write_manifest(tmp_path, "0.1.0"))


@pytest.mark.parametrize("manifest", [{}, {"version": 200}, {"version": None}])
def test_missing_or_non_string_manifest_version_is_rejected(
    tmp_path: Path, manifest: dict[str, object]
) -> None:
    """The manifest version must exist and be a string."""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="string version"):
        validate_release_version("0.2.0", manifest_path)
