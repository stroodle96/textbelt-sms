# HACS Versioning and Release Design

## Goal

Make `stroodle96/textbelt-sms` expose intentional, selectable versions in HACS by publishing validated GitHub releases whose tags agree with the Home Assistant integration manifest.

## Current State

- The public repository is `https://github.com/stroodle96/textbelt-sms`, with protected default branch `main`.
- The local workspace is an unborn Git repository with no remote, so it must be attached to the public repository before implementation.
- `custom_components/textbelt_sms/manifest.json` reports `0.1.0`.
- GitHub contains one published prerelease, `v0.1.0`, from July 2025. It remains part of release history.
- The HACS validation job in `.github/workflows/validate.yml` is commented out.
- The repository is public, has a description and issues enabled, but has no GitHub topics and no Textbelt brand assets.

## Release Contract

- `custom_components/textbelt_sms/manifest.json` is the sole version source.
- Manifest versions use strict numeric SemVer without a prefix: `MAJOR.MINOR.PATCH`.
- Git tags add a `v` prefix to the exact manifest version: manifest `0.2.0` maps to tag `v0.2.0`.
- GitHub releases, not bare Git tags, are the artifacts HACS presents as selectable versions.
- Existing release tags are immutable. The workflow must never move or recreate a published tag.
- The first new release is `v0.2.0`, published as a GitHub prerelease from the tested `main` commit.
- Stabilizing `0.2.0` edits that same GitHub release from prerelease to stable; it does not create a second tag.
- Because `v0.2.0` is initially a prerelease, HACS users must enable the repository's prerelease switch before it appears in version selection.

## Repository and Workflow Design

Implementation happens on branch `hacs-versioning`, created from the fetched `origin/main` commit.

The repository will add a small standard-library Python validator. It accepts a requested version and manifest path, rejects non-numeric SemVer or a manifest mismatch, and returns the derived `v`-prefixed tag. Unit tests cover accepted versions and all release-blocking errors.

A manually dispatched GitHub Actions workflow will accept `version` and `channel` inputs. Creation releases the immutable `main` commit that triggered the workflow. Promotion verifies the existing immutable tag is still in `main`'s history, checks out that tag, and tests the tagged code rather than whatever newer commits may have reached `main`. Both paths rerun lint, tests, the local Home Assistant smoke harness, Hassfest, and HACS validation. Creation fails if the tag or release already exists; promotion succeeds only for an existing prerelease whose tag contains the requested manifest version.

HACS will download the standard GitHub source archive. The existing `custom_components/textbelt_sms/` layout is already correct, so the repository will not use `zip_release`, a custom filename, or a release asset.

HACS validation will be re-enabled with the `brands` check explicitly ignored. Brand submission and HACS default-catalog inclusion are not part of this change; the supported distribution path is adding the GitHub URL as a custom Integration repository.

## User Experience

The README will document how to add the custom repository, enable HACS prereleases, refresh repository information, select `v0.2.0`, install it, restart Home Assistant, and later select another published version. It will also explain that prerelease visibility is opt-in and that the default branch remains available until a stable release is promoted.

## References

- HACS integration requirements: https://hacs.xyz/docs/publish/integration/
- HACS repository versions: https://hacs.xyz/docs/publish/start/
- HACS validation action: https://hacs.xyz/docs/publish/action/
- HACS prerelease switch: https://www.hacs.dev/docs/use/entities/switch/
- Home Assistant integration manifest: https://developers.home-assistant.io/docs/creating_integration_manifest/
- Reference integration blueprint: https://github.com/ludeeus/integration_blueprint
- Reference validation workflow: https://github.com/AlexxIT/SonoffLAN/blob/master/.github/workflows/hacs.yml
