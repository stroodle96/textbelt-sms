# Copyright (c) 2026 Textbelt SMS contributors
"""Safety checks for isolated disposable-config cleanup."""

from pathlib import Path

import pytest

from tests.smoke.fixture_files import clear_fixture_contents, wait_for_migrated_entry


def test_cleanup_clears_marked_fixture_without_following_symlink(
    tmp_path: Path,
) -> None:
    """A fixture link cannot cause deletion outside the mounted config root."""
    root = tmp_path / "fixture"
    root.mkdir()
    project = "textbelt-sms-smoke-test-1"
    (root / ".textbelt-smoke-fixture").write_text(project)
    nested = root / ".storage"
    nested.mkdir()
    (nested / "entry").write_text("synthetic")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep").write_text("preserved")
    (root / "link").symlink_to(outside, target_is_directory=True)
    clear_fixture_contents(project, mount=root)
    assert list(root.iterdir()) == []
    assert (outside / "keep").read_text() == "preserved"


def test_cleanup_rejects_wrong_project_without_deleting(tmp_path: Path) -> None:
    """Only the current uniquely named project's marker grants cleanup."""
    (tmp_path / ".textbelt-smoke-fixture").write_text("textbelt-sms-smoke-other")
    keep = tmp_path / "keep"
    keep.write_text("preserved")
    with pytest.raises(ValueError, match="unverified smoke fixture"):
        clear_fixture_contents("textbelt-sms-smoke-current", mount=tmp_path)
    assert keep.read_text() == "preserved"


def test_cleanup_rejects_symlink_mount(tmp_path: Path) -> None:
    """Resolve the mount before permitting recursive operations."""
    target = tmp_path / "target"
    target.mkdir()
    (target / ".textbelt-smoke-fixture").write_text("textbelt-sms-smoke-current")
    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="unverified smoke fixture"):
        clear_fixture_contents("textbelt-sms-smoke-current", mount=alias)
    assert (target / ".textbelt-smoke-fixture").exists()


async def test_migration_waits_for_loaded_entry_and_deferred_storage_save() -> None:
    """HTTP readiness and a loaded entry can both precede the migrated disk save."""
    runtime = iter(
        [
            [
                {
                    "domain": "textbelt_sms",
                    "entry_id": "current",
                    "state": "setup_in_progress",
                }
            ],
            [{"domain": "textbelt_sms", "entry_id": "current", "state": "loaded"}],
            [{"domain": "textbelt_sms", "entry_id": "current", "state": "loaded"}],
        ]
    )
    stored = iter(
        [
            {
                "data": {
                    "entries": [
                        {"domain": "textbelt_sms", "entry_id": "current", "version": 1}
                    ]
                }
            },
            {
                "data": {
                    "entries": [
                        {"domain": "textbelt_sms", "entry_id": "current", "version": 2}
                    ]
                }
            },
        ]
    )
    reads = []

    async def read_runtime() -> list[dict]:
        return next(runtime)

    def read_storage() -> dict:
        reads.append("storage")
        return next(stored)

    async def pause(_delay: float) -> None:
        return None

    result = await wait_for_migrated_entry(
        read_runtime, read_storage, attempts=3, pause=pause
    )
    assert result["version"] == 2  # noqa: PLR2004
    assert len(reads) == 2  # noqa: PLR2004


async def test_migration_wait_fails_explicitly_on_actual_migration_error() -> None:
    """An actual HA migration failure must not be disguised as readiness delay."""

    async def runtime() -> list[dict]:
        return [
            {
                "domain": "textbelt_sms",
                "entry_id": "current",
                "state": "migration_error",
            }
        ]

    with pytest.raises(RuntimeError, match="migration_error"):
        await wait_for_migrated_entry(runtime, dict, attempts=1)
