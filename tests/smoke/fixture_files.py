# Copyright (c) 2026 Textbelt SMS contributors
"""Clear only the marked disposable config mount from an isolated root helper."""

from __future__ import annotations

import asyncio
import re
import shutil
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
from pathlib import Path


def clear_fixture_contents(project: str, *, mount: Path = Path("/fixture")) -> None:
    """Validate the fixture mount/marker before deleting its children."""
    if (
        mount.resolve() != mount
        or not mount.is_dir()
        or not re.fullmatch(r"textbelt-sms-smoke-[A-Za-z0-9_-]+", project)
        or (mount / ".textbelt-smoke-fixture").read_text() != project
    ):
        message = "Refusing cleanup of an unverified smoke fixture"
        raise ValueError(message)
    marker = mount / ".textbelt-smoke-fixture"
    for child in mount.iterdir():
        if child == marker:
            continue
        if child.is_symlink() or not child.is_dir():
            child.unlink()
        else:
            shutil.rmtree(child)
    marker.unlink()


async def wait_for_migrated_entry(
    read_runtime: Callable[[], Awaitable[list[dict]]],
    read_storage: Callable[[], dict],
    *,
    attempts: int = 600,
    pause: Callable[[float], Awaitable[object]] = asyncio.sleep,
) -> dict:
    """Wait for actual entry setup and HA's separately scheduled disk migration."""
    last_state = "missing"
    last_version = None
    for _ in range(attempts):
        entries = [
            entry for entry in await read_runtime() if entry["domain"] == "textbelt_sms"
        ]
        if len(entries) == 1:
            entry = entries[0]
            last_state = entry["state"]
            if last_state in {"migration_error", "setup_error", "failed_unload"}:
                message = f"Textbelt entry readiness failed: {last_state}"
                raise RuntimeError(message)
            if last_state == "loaded":
                stored = next(
                    (
                        item
                        for item in read_storage()["data"]["entries"]
                        if item["entry_id"] == entry["entry_id"]
                    ),
                    None,
                )
                last_version = stored.get("version") if stored else None
                if last_version == 2:  # noqa: PLR2004 -- frozen migration target.
                    return stored
        await pause(0.1)
    message = (
        f"Textbelt migration readiness deadline: state={last_state}, "
        f"stored_version={last_version}"
    )
    raise RuntimeError(message)


if __name__ == "__main__":
    clear_fixture_contents(sys.argv[1])
