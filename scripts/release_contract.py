# Copyright (c) 2026 Daniel Strodl
"""Validate and derive a GitHub release tag from the integration manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RELEASE_VERSION = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:b[1-9]\d*)?$"
)


def validate_release_version(version: str, manifest_path: Path) -> str:
    """Validate VERSION against MANIFEST_PATH and return its Git tag."""
    if RELEASE_VERSION.fullmatch(version) is None:
        message = f"{version!r} is not strict MAJOR.MINOR.PATCH with optional bN beta"
        raise ValueError(message)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_version = manifest.get("version")
    if not isinstance(manifest_version, str):
        message = "manifest.json must contain a string version"
        raise ValueError(message)  # noqa: TRY004 - the public contract uses ValueError.
    if manifest_version != version:
        message = (
            f"Version mismatch: requested {version}, "
            f"manifest contains {manifest_version}"
        )
        raise ValueError(message)
    return f"v{version}"


def main() -> int:
    """Validate CLI arguments and print the matching Git tag."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("custom_components/textbelt_sms/manifest.json"),
    )
    args = parser.parse_args()

    try:
        tag = validate_release_version(args.version, args.manifest)
        sys.stdout.write(f"{tag}\n")
    except (OSError, json.JSONDecodeError, ValueError) as err:
        parser.error(str(err))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
