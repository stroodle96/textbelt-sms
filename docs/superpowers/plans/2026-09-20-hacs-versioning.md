# HACS Versioning and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish validated, selectable Textbelt SMS versions through HACS, beginning with GitHub prerelease `v0.2.0` and supporting safe in-place promotion to stable.

**Architecture:** Treat `custom_components/textbelt_sms/manifest.json` as the sole version source, enforce its contract through a tested Python CLI, and expose a manually dispatched GitHub Actions release workflow. HACS consumes GitHub's tagged source archive directly; no custom release ZIP or runtime integration changes are required.

**Tech Stack:** Home Assistant custom integration, HACS, Python 3.14 standard library and pytest, GitHub Actions, GitHub CLI, Ruff, Hassfest, Docker-based Home Assistant smoke harness.

**Spec:** `docs/superpowers/specs/2026-09-20-hacs-versioning-design.md`

## Global Constraints

- Implement on branch `hacs-versioning`, based on the current fetched `origin/main` commit.
- Preserve the existing `v0.1.0` tag and GitHub prerelease without modification.
- Use strict manifest versions in `MAJOR.MINOR.PATCH` form and derive tags as `vMAJOR.MINOR.PATCH`.
- Publish `v0.2.0` first as a GitHub prerelease and promote that same release in place when stable.
- Never move, overwrite, or recreate an existing Git tag.
- Keep minimum versions `homeassistant: 2026.8.2` and `hacs: 2.0.1`.
- Do not add `zip_release`, `filename`, or a release archive; HACS installs `custom_components/textbelt_sms/` from the tagged source tree.
- Distribution in this plan is through a HACS custom Integration repository, not the HACS default catalog.
- Ignore only the HACS `brands` validation until project-owned brand assets are available; no other HACS check may be ignored.

## Review Focus

- Requested version contains a leading `v`, missing component, suffix, or leading zero: reject before any tag or release mutation.
- Requested version differs from `manifest.json`: reject and report both values.
- A tag or release already exists during create: reject without moving the tag or editing the release.
- Stable promotion targets a tag outside `main` history, a tag with a mismatched manifest, or a release that is already stable: reject without changing GitHub state.
- The workflow is dispatched from a branch other than `main`: reject before validation or publication.

---

### Task 1: Recover the repository and establish the version contract

**Files:**
- Create: `scripts/release_contract.py`
- Create: `tests/test_release_contract.py`
- Modify: `custom_components/textbelt_sms/manifest.json`
- Modify: `hacs.json`
- Delete: `custom_components/textbelt_sms/README_CLEANUP.txt`
- Delete: `custom_components/textbelt_sms/REMOVE_THESE_FILES.txt`
- Commit unchanged planning artifacts: `docs/superpowers/specs/2026-09-20-hacs-versioning-design.md`, `docs/superpowers/plans/2026-09-20-hacs-versioning.md`

**Interfaces:**
- Produces: `validate_release_version(version: str, manifest_path: pathlib.Path) -> str`, returning the `v`-prefixed tag or raising `ValueError`.
- Produces: CLI `python scripts/release_contract.py --version VERSION --manifest PATH`, printing only the derived tag on success and exiting nonzero with a readable error on failure.
- Consumes: manifest JSON key `version` as the canonical version.

- [ ] **Step 1: Verify the empty workspace before attaching the remote**

Run:

```powershell
git status --short --branch
git remote -v
git log -1 --oneline
```

Expected: branch reports `main` with no commits, no remote is configured, and only the two planning files are untracked. Stop if any unrelated local files or commits appear.

- [ ] **Step 2: Attach the public repository and create the implementation branch**

Run:

```powershell
git remote add origin https://github.com/stroodle96/textbelt-sms.git
git fetch origin --tags
git switch -c hacs-versioning origin/main
git branch -f main origin/main
```

Expected: `hacs-versioning` tracks the current code from `origin/main`; local `main` points at `origin/main`; the untracked planning files remain present.

- [ ] **Step 3: Confirm the recovered baseline**

Run:

```powershell
git status --short --branch
git log -3 --oneline --decorate
git tag --list
git diff -- custom_components/textbelt_sms/manifest.json hacs.json
```

Expected: current branch is `hacs-versioning`; `v0.1.0` is present; tracked files are unchanged; only the planning files are untracked.

- [ ] **Step 4: Write failing release-contract tests**

Create `tests/test_release_contract.py`:

```python
"""Tests for the release version contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.release_contract import validate_release_version


def write_manifest(tmp_path: Path, version: object = "0.2.0") -> Path:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"version": version}), encoding="utf-8")
    return manifest_path


def test_valid_version_returns_prefixed_tag(tmp_path: Path) -> None:
    assert validate_release_version("0.2.0", write_manifest(tmp_path)) == "v0.2.0"


@pytest.mark.parametrize(
    "version",
    ["v0.2.0", "0.2", "0.2.0b1", "01.2.3", "0.02.3", "0.2.03", "0.2.0+build"],
)
def test_invalid_versions_are_rejected(tmp_path: Path, version: str) -> None:
    with pytest.raises(ValueError, match="strict MAJOR.MINOR.PATCH"):
        validate_release_version(version, write_manifest(tmp_path))


def test_manifest_mismatch_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requested 0.2.0, manifest contains 0.1.0"):
        validate_release_version("0.2.0", write_manifest(tmp_path, "0.1.0"))


@pytest.mark.parametrize("manifest", [{}, {"version": 200}, {"version": None}])
def test_missing_or_non_string_manifest_version_is_rejected(
    tmp_path: Path, manifest: dict[str, object]
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="string version"):
        validate_release_version("0.2.0", manifest_path)
```

- [ ] **Step 5: Run the focused tests and verify the expected failure**

Run:

```powershell
python -m pytest tests/test_release_contract.py -v
```

Expected: test collection fails because `scripts.release_contract` does not exist.

- [ ] **Step 6: Implement the release-contract CLI**

Create `scripts/release_contract.py`:

```python
"""Validate and derive a GitHub release tag from the integration manifest."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

STRICT_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def validate_release_version(version: str, manifest_path: Path) -> str:
    """Validate VERSION against MANIFEST_PATH and return its Git tag."""
    if STRICT_SEMVER.fullmatch(version) is None:
        raise ValueError(f"{version!r} is not strict MAJOR.MINOR.PATCH")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_version = manifest.get("version")
    if not isinstance(manifest_version, str):
        raise ValueError("manifest.json must contain a string version")
    if manifest_version != version:
        raise ValueError(
            f"Version mismatch: requested {version}, manifest contains {manifest_version}"
        )
    return f"v{version}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("custom_components/textbelt_sms/manifest.json"),
    )
    args = parser.parse_args()

    try:
        print(validate_release_version(args.version, args.manifest))
    except (OSError, json.JSONDecodeError, ValueError) as err:
        parser.error(str(err))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 7: Set the first new version and HACS display name**

Change `custom_components/textbelt_sms/manifest.json` from `"version": "0.1.0"` to:

```json
"version": "0.2.0"
```

Change only the `name` value in `hacs.json`, retaining both compatibility floors:

```json
{
  "name": "Textbelt SMS",
  "homeassistant": "2026.8.2",
  "hacs": "2.0.1"
}
```

Delete the two cleanup marker files from the integration directory so HACS does not install them into Home Assistant.

- [ ] **Step 8: Run focused and full validation**

Run:

```powershell
python -m pytest tests/test_release_contract.py -v
python scripts/release_contract.py --version 0.2.0 --manifest custom_components/textbelt_sms/manifest.json
python -m pytest
python -m ruff check .
python -m ruff format . --check
```

Expected: every command passes; the CLI prints exactly `v0.2.0`.

- [ ] **Step 9: Commit the version contract**

Run:

```powershell
git add docs/superpowers scripts/release_contract.py tests/test_release_contract.py custom_components/textbelt_sms/manifest.json hacs.json custom_components/textbelt_sms/README_CLEANUP.txt custom_components/textbelt_sms/REMOVE_THESE_FILES.txt
git commit -m "chore: establish HACS release version contract"
```

Expected: the commit includes the specification, plan, tested validator, metadata changes, and removal of packaging-only markers.

---

### Task 2: Re-enable HACS validation and add the controlled release workflow

**Files:**
- Modify: `.github/workflows/validate.yml`
- Create: `.github/workflows/release.yml`

**Interfaces:**
- Consumes: `python scripts/release_contract.py --version VERSION` from Task 1.
- Produces: manual workflow inputs `version: string` and `channel: prerelease | stable`.
- Produces: operation `create` for an unused version or `promote` for the exact existing prerelease tag on the same commit.

- [ ] **Step 1: Re-enable HACS validation on pushes and pull requests**

Replace the commented HACS block in `.github/workflows/validate.yml` with:

```yaml
  hacs:
    name: HACS validation
    runs-on: ubuntu-latest
    steps:
      - name: Run HACS validation
        uses: hacs/action@1ebf01c408f29afcb6406bd431bc98fd8cbb15aa # main
        with:
          category: integration
          ignore: brands
```

Keep the existing Hassfest job and the workflow-level `permissions: {}` unchanged.

- [ ] **Step 2: Create the manual release workflow**

Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  workflow_dispatch:
    inputs:
      version:
        description: Version from manifest.json, without the v prefix
        required: true
        type: string
      channel:
        description: Publish a prerelease or promote/create a stable release
        required: true
        default: prerelease
        type: choice
        options:
          - prerelease
          - stable

permissions: {}

concurrency:
  group: textbelt-sms-release
  cancel-in-progress: false

jobs:
  verify:
    name: Verify release
    runs-on: ubuntu-latest
    permissions:
      contents: read
    outputs:
      tag: ${{ steps.contract.outputs.tag }}
      operation: ${{ steps.state.outputs.operation }}
    steps:
      - name: Require main branch
        if: github.ref != 'refs/heads/main'
        run: |
          echo "Releases must be dispatched from main." >&2
          exit 1

      - name: Checkout the release commit
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          ref: ${{ github.sha }}

      - name: Set up Python
        uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
        with:
          python-version: "3.14"
          cache: pip

      - name: Validate version contract
        id: contract
        shell: bash
        run: |
          tag="$(python scripts/release_contract.py --version '${{ inputs.version }}')"
          echo "tag=$tag" >> "$GITHUB_OUTPUT"

      - name: Determine allowed release operation
        id: state
        env:
          GH_TOKEN: ${{ github.token }}
          TAG: ${{ steps.contract.outputs.tag }}
          CHANNEL: ${{ inputs.channel }}
        shell: bash
        run: |
          if ! git show-ref --verify --quiet "refs/tags/$TAG"; then
            if gh release view "$TAG" >/dev/null 2>&1; then
              echo "Release $TAG exists without a fetched tag; refusing to continue." >&2
              exit 1
            fi
            echo "operation=create" >> "$GITHUB_OUTPUT"
            exit 0
          fi

          if ! gh release view "$TAG" >/dev/null 2>&1; then
            echo "Tag $TAG already exists without a GitHub release; refusing to move or reuse it." >&2
            exit 1
          fi

          if [[ "$CHANNEL" != "stable" ]]; then
            echo "Tag and release $TAG already exist; only stable promotion is permitted." >&2
            exit 1
          fi

          if [[ "$(gh release view "$TAG" --json isPrerelease --jq .isPrerelease)" != "true" ]]; then
            echo "Release $TAG is already stable; refusing duplicate publication." >&2
            exit 1
          fi

          if ! git merge-base --is-ancestor "$TAG" "$GITHUB_SHA"; then
            echo "Tag $TAG is not in the history of this main commit; refusing promotion." >&2
            exit 1
          fi

          echo "operation=promote" >> "$GITHUB_OUTPUT"

      - name: Check out the immutable prerelease for promotion
        if: steps.state.outputs.operation == 'promote'
        env:
          TAG: ${{ steps.contract.outputs.tag }}
        run: git checkout --detach "$TAG"

      - name: Install requirements from the verified tree
        run: python -m pip install -r requirements.txt -r requirements_test.txt

      - name: Revalidate the checked-out release contract
        if: steps.state.outputs.operation == 'promote'
        run: python scripts/release_contract.py --version '${{ inputs.version }}'

      - name: Run unit tests
        run: python -m pytest

      - name: Run Ruff
        run: |
          python -m ruff check .
          python -m ruff format . --check

      - name: Run Home Assistant smoke harness
        run: bash tests/smoke/run.sh

      - name: Run Hassfest validation
        uses: home-assistant/actions/hassfest@a7c616ce81ccda50150bf1595786c71b1883fabb # master

      - name: Run HACS validation
        uses: hacs/action@1ebf01c408f29afcb6406bd431bc98fd8cbb15aa # main
        with:
          category: integration
          ignore: brands

  publish:
    name: Publish release
    needs: verify
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Create GitHub release
        if: needs.verify.outputs.operation == 'create'
        env:
          GH_TOKEN: ${{ github.token }}
          TAG: ${{ needs.verify.outputs.tag }}
          CHANNEL: ${{ inputs.channel }}
        shell: bash
        run: |
          args=("$TAG" --repo "$GITHUB_REPOSITORY" --target "$GITHUB_SHA" --title "$TAG" --generate-notes)
          if [[ "$CHANNEL" == "prerelease" ]]; then
            args+=(--prerelease)
          fi
          gh release create "${args[@]}"

      - name: Promote GitHub prerelease
        if: needs.verify.outputs.operation == 'promote'
        env:
          GH_TOKEN: ${{ github.token }}
          TAG: ${{ needs.verify.outputs.tag }}
        shell: bash
        run: gh release edit "$TAG" --repo "$GITHUB_REPOSITORY" --prerelease=false --latest --title "$TAG"
```

- [ ] **Step 3: Run local checks that exercise the workflow's commands**

Run:

```powershell
python scripts/release_contract.py --version 0.2.0
python -m pytest
python -m ruff check .
python -m ruff format . --check
```

Expected: all commands pass and the contract CLI prints `v0.2.0`.

- [ ] **Step 4: Inspect the workflow diff for release safety**

Run:

```powershell
git diff --check
git diff -- .github/workflows/validate.yml .github/workflows/release.yml
```

Expected: no whitespace errors; the release workflow has write permission only in `publish`; branch, mismatch, duplicate, ancestry, and promotion guards precede publication; promotion tests the tagged tree.

- [ ] **Step 5: Commit the CI and release workflow**

Run:

```powershell
git add .github/workflows/validate.yml .github/workflows/release.yml
git commit -m "ci: add controlled HACS release workflow"
```

---

### Task 3: Document HACS custom-repository and version selection

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: repository URL `https://github.com/stroodle96/textbelt-sms` and release tag `v0.2.0`.
- Produces: user instructions for adding the Integration repository, enabling prereleases, selecting a release, and restarting Home Assistant.

- [ ] **Step 1: Replace the HACS installation section with version-aware instructions**

Use this content under `## Installation`:

```markdown
### HACS custom repository (recommended)

1. Install and configure [HACS](https://www.hacs.xyz/) if it is not already available.
2. Open HACS, open the menu, and select **Custom repositories**.
3. Enter `https://github.com/stroodle96/textbelt-sms`, select **Integration**, and add the repository.
4. Open **Textbelt SMS** and select **Download**.
5. Under **Need a different version?**, choose the release to install.
6. Restart Home Assistant after installation or a version change.

#### Installing a prerelease

HACS excludes GitHub prereleases by default. To install `v0.2.0` while it is marked as a prerelease:

1. Go to **Settings → Devices & services → HACS → Entities**.
2. Show disabled entities and enable the prerelease switch associated with Textbelt SMS.
3. Turn the switch on.
4. In HACS, open Textbelt SMS and select **Update information**.
5. Download Textbelt SMS and select `v0.2.0` under **Need a different version?**.

The prerelease switch is not required after `v0.2.0` is promoted to a stable GitHub release.
```

Retain the existing manual installation instructions after this section.

- [ ] **Step 2: Correct the repository overview path**

Replace the stale path `custom_components/textbelt-sms/*` with:

```text
custom_components/textbelt_sms/*
```

- [ ] **Step 3: Validate the documentation and repository metadata files**

Run:

```powershell
python -m json.tool hacs.json
python -m json.tool custom_components/textbelt_sms/manifest.json
rg -n "textbelt-sms|textbelt_sms|v0\.2\.0|Need a different version" README.md hacs.json custom_components/textbelt_sms/manifest.json
git diff --check
```

Expected: both JSON files parse; hyphenated `textbelt-sms` appears only in the GitHub repository URL/name context; integration paths use `textbelt_sms`; prerelease instructions name `v0.2.0`.

- [ ] **Step 4: Run the complete pre-push suite**

Run:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format . --check
```

If Docker is available, also run:

```powershell
bash tests/smoke/run.sh
```

Expected: all available checks pass.

- [ ] **Step 5: Commit the user documentation**

Run:

```powershell
git add README.md
git commit -m "docs: explain HACS version selection"
```

---

### Task 4: Configure GitHub metadata and verify the pull request

**Files:**
- No repository file changes.

**Interfaces:**
- Produces: repository topics required by HACS discovery conventions.
- Produces: protected `main` checks for lint, unit tests, Home Assistant smoke, Hassfest, and HACS validation.

- [ ] **Step 1: Push the implementation branch**

Run:

```powershell
git push -u origin hacs-versioning
```

Expected: GitHub creates or updates branch `hacs-versioning` without modifying `main`.

- [ ] **Step 2: Add GitHub repository topics**

In `stroodle96/textbelt-sms` → **Settings** or the repository About editor, set exactly these topics:

```text
home-assistant
home-assistant-custom-component
hacs
sms
textbelt
```

Retain the existing repository description and enabled issue tracker.

- [ ] **Step 3: Confirm Actions can publish releases**

In **Settings → Actions → General → Workflow permissions**, allow workflows to request read/write permissions. The workflow itself remains least-privileged: only the `publish` job requests `contents: write`.

- [ ] **Step 4: Open the pull request and require all validation**

Open a pull request from `hacs-versioning` to `main` with title:

```text
Add controlled HACS version releases
```

Require these checks before merge:

```text
Ruff
Home Assistant unit tests
Real HA and local Textbelt stub
Hassfest validation
HACS validation
```

- [ ] **Step 5: Review PR results and merge without bypassing protection**

Expected: every required check passes on the pull-request commit; HACS validation ignores only `brands`; the PR is merged normally into protected `main`.

---

### Task 5: Publish and verify `v0.2.0` in HACS

**Files:**
- No repository file changes.

**Interfaces:**
- Consumes: merged `main` manifest version `0.2.0`.
- Produces: immutable tag `v0.2.0` and a non-draft GitHub prerelease generated from the tested workflow commit.

- [ ] **Step 1: Confirm main is ready to release**

On GitHub, confirm the merge commit on `main` has successful lint, unit, smoke, Hassfest, and HACS checks. Confirm no `v0.2.0` tag or release exists.

- [ ] **Step 2: Dispatch the first release**

Run the **Release** workflow from `main` with:

```text
version: 0.2.0
channel: prerelease
```

Expected: `verify` passes, `publish` creates tag and release `v0.2.0`, the release is published rather than draft, and GitHub marks it as a prerelease.

- [ ] **Step 3: Verify immutable release state**

Confirm on GitHub:

```text
Tag: v0.2.0
Release title: v0.2.0
Draft: false
Prerelease: true
Target: the workflow's tested main commit
Assets: GitHub-generated source archives only
```

- [ ] **Step 4: Verify HACS version selection in a disposable Home Assistant instance**

1. Add `https://github.com/stroodle96/textbelt-sms` as a custom **Integration** repository.
2. Enable and turn on the Textbelt SMS prerelease switch.
3. Select **Update information** for Textbelt SMS.
4. Open **Download**, expand **Need a different version?**, and select `v0.2.0`.
5. Restart Home Assistant.
6. Confirm `/config/custom_components/textbelt_sms/manifest.json` reports `0.2.0`.
7. Configure Textbelt SMS with a test API key and execute one test send through the documented integration action.

Expected: HACS installs `v0.2.0`; Home Assistant loads the integration; the test send follows the existing success path.

- [ ] **Step 5: Verify failure guards without changing release state**

Dispatching from a non-`main` ref must fail at **Require main branch**. A subsequent `version: 0.2.0`, `channel: prerelease` run must fail because the tag and release exist. A mismatched future version such as `0.2.1` must fail until `manifest.json` is changed to `0.2.1` through a reviewed pull request.

- [ ] **Step 6: Promote the same release after prerelease acceptance**

When `v0.2.0` has passed the HACS installation test, rerun **Release** from `main` while its manifest still reports `0.2.0` with:

```text
version: 0.2.0
channel: stable
```

Expected: the workflow confirms `v0.2.0` remains in `main` history, checks out and retests the tagged code, and changes the existing release to stable without moving the tag. With the HACS prerelease switch off and repository information refreshed, `v0.2.0` remains the available stable version.
