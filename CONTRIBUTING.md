# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## Github is used for everything

Github is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. Fork the repo and create your branch from `main`.
2. If you've changed something, update the documentation.
3. Make sure your code lints (using `scripts/lint`).
4. Test your contribution with the local unit suite.
5. Issue that pull request!

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issues](../../issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](../../issues/new/choose); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People *love* thorough bug reports. I'm not even kidding.

## Use a Consistent Coding Style

Use [black](https://github.com/ambv/black) to make sure the code follows the style.

## Test your code modification

Install the pinned development and test dependencies, then run the Home Assistant-aware
unit tests (including coverage):

```bash
python3 -m pip install -r requirements_test.txt
python3 -m pytest
```

The real-Home-Assistant smoke harness starts a fresh Home Assistant 2026.8.2
alongside a deterministic local Textbelt stub. It creates its own temporary Home
Assistant user through the onboarding API, so no token or repository secret is
needed. It never sends an SMS. Run:

```bash
bash tests/smoke/run.sh
```

The harness requires Docker and preserves Compose state, HA/stub logs, requests,
configuration, and a smoke report in a temporary `textbelt-ha-artifacts-*` directory when it exits.

This custom component is based on [integration_blueprint template](https://github.com/ludeeus/integration_blueprint).

It comes with development environment in a container, easy to launch
if you use Visual Studio Code. With this container you will have a stand alone
Home Assistant instance running and already configured with the included
[`configuration.yaml`](./config/configuration.yaml)
file.

## Publishing releases

Merging a version bump does not publish a GitHub release. Run the Release workflow
after merge and verify publication before announcing that version as available in HACS.

1. Merge the version change into `main` and confirm lint, unit tests, the local
   Textbelt stub/HA smoke test, Hassfest, and HACS validation pass. The integration
   manifest must contain the exact version being released, without the `v` prefix.
2. Check the [existing tags](https://github.com/stroodle96/textbelt-sms/tags) and
   [releases](https://github.com/stroodle96/textbelt-sms/releases). Never move or
   recreate an existing release tag. If a tag exists without a release, investigate
   the incomplete publication before retrying.
3. From GitHub **Actions → Release → Run workflow**, select `main`, enter the
   manifest version, and explicitly select `prerelease`. For example:

   ```sh
   gh workflow run release.yml --repo stroodle96/textbelt-sms --ref main -f version=0.2.0 -f channel=prerelease
   ```

4. Wait for both **Verify release** and **Publish release** to succeed. Check the
   published release is not a draft, is marked as a prerelease, and its tag resolves
   to the successful workflow run's tested commit. Confirm the tagged manifest has
   the requested version. Record the release ID and resolved tag SHA for promotion:

   ```sh
   gh api repos/stroodle96/textbelt-sms/releases/tags/v0.2.0 --jq '{id,tag_name,draft,prerelease,html_url}'
   gh api repos/stroodle96/textbelt-sms/git/ref/tags/v0.2.0 --jq '{ref,object}'
   gh api 'repos/stroodle96/textbelt-sms/contents/custom_components/textbelt_sms/manifest.json?ref=v0.2.0' -H 'Accept: application/vnd.github.raw+json'
   ```

5. Verify installation through HACS with prerelease access enabled: select
   **Update information**, download the published version, check the installed
   manifest, restart Home Assistant, and confirm the integration loads. The local
   HA smoke harness tests the checked-out code; it does not prove HACS discovery
   or installation. Routine SMS behavior checks use the local Textbelt stub.
6. After the HACS check passes, promote the same release by dispatching **Release**
   from `main` with the same version and `stable`. Main's manifest must still
   contain that version. The workflow retests the immutable tagged code before
   promotion; it does not move the tag:

   ```sh
   gh workflow run release.yml --repo stroodle96/textbelt-sms --ref main -f version=0.2.0 -f channel=stable
   ```

7. Verify the release is non-draft and stable, its ID and resolved tag SHA are
   unchanged, and GitHub identifies it as the latest release. Turn off the HACS
   prerelease switch, refresh information, and confirm the stable version remains
   downloadable. Install it with prereleases disabled, check the installed manifest
   version, restart Home Assistant, and confirm the integration loads:

   ```sh
   gh api repos/stroodle96/textbelt-sms/releases/tags/v0.2.0 --jq '{id,tag_name,draft,prerelease,html_url}'
   gh api repos/stroodle96/textbelt-sms/git/ref/tags/v0.2.0 --jq '{ref,object}'
   gh api repos/stroodle96/textbelt-sms/releases/latest --jq .tag_name
   ```

Replace `0.2.0` and `v0.2.0` in these examples for subsequent releases. Stop on a
failed validation or publication step and inspect its logs before retrying.
GitHub-generated source archives are sufficient; no custom ZIP asset is required.
Keep earlier releases for rollback, including the historical `v0.1.0` prerelease.

## License

By contributing, you agree that your contributions will be licensed under its MIT License.

### Native Assist smoke fixture

Run `LIVE_SMOKE=0 bash tests/smoke/run.sh` from a Linux/WSL shell with Docker
Compose. Offline mode explicitly forces `http://textbelt:8080`, `smoke-test-key`
and reserved synthetic recipients, overriding inherited provider endpoint/key
settings. Exposed HA/stub ports bind only to localhost. The native fixture is
forbidden in `LIVE_SMOKE=1`; historical live paths are outside routine validation.

A smoke-only integration registers two deterministic HA conversation agents
through the supported agent API. Signed callbacks enter the product's generated
webhook and traverse its actual `PipelineRun`/`PipelineInput`. Assertions inspect
admin pipeline debug WebSocket events, fresh context IDs, conversation IDs,
read-only agent snapshots and observable stub sends. No routing automation,
script, monkeypatched pipeline or product diagnostic backdoor is used.

The synthetic `https://ha.example.com` external URL validates configuration only.
The helper discovers the generated path in a captured send and posts signed
fixtures to local HA. It never requests that public hostname. Migration changes
only stopped disposable HA storage. Restart checks retain initiating IDs and
admitted callback bodies; they enforce a restart deadline inside the local
two-minute duplicate policy instead of silently allowing expiry.

Artifacts include pipeline events, synthetic execution snapshots, callback-event
observations, request/outcome ledgers, migration/registry snapshots, metadata
Store snapshots, Compose status/configuration and logs. Native helper tokens pass through stdin; the legacy API helper still uses
`--token` process arguments. Tokens are not intentionally saved in these artifacts. Fixture payloads, API keys and recipients
are synthetic. The outcome ledger distinguishes rejection from acceptance followed
by disconnect; native response failures must not repeat the pipeline or send.
Actual coordinator-run evidence and remaining limits are recorded in
[stage4-local-validation.md](docs/research/stage4-local-validation.md).
