# Native Assist Home Assistant compatibility

Status: **PASS for the actual deterministic offline Home Assistant 2026.9.4 smoke, exit 0, on 2026-10-02.**

Read-only live readiness observed Core 2026.9.4 RUNNING on 2026-10-02; only `textbelt_sms.send_sms` was registered. The native `start_conversation` service was absent. These observations do not identify the deployed Git revision or prove compatibility with candidate `94bdb9575ccfd836928b12a5b85622c753fd5f94` on branch `codex/textbelt-assist-stage0`.

## Image contract and reproduction

`tests/smoke/docker-compose.yml` accepts optional `HA_SMOKE_IMAGE`. Unset or empty uses the unchanged pinned default `ghcr.io/home-assistant/home-assistant:2026.8.2`. The requested compatibility override is exactly `ghcr.io/home-assistant/home-assistant:2026.9.4`. Runner and fixture behavior are unchanged.

Run from the repository in WSL Ubuntu with Docker/Compose available and localhost ports 8080/8123 free. Use the persistent artifact parent because WSL temporary directories can disappear between processes:

```bash
mkdir -p /home/drew/.cache/textbelt-local-validation/tmp
TMPDIR=/home/drew/.cache/textbelt-local-validation/tmp LIVE_SMOKE=0 \
  HA_SMOKE_IMAGE=ghcr.io/home-assistant/home-assistant:2026.9.4 \
  bash tests/smoke/run.sh

# Reproduce the pinned default explicitly, ignoring inherited overrides.
env -u HA_SMOKE_IMAGE TMPDIR=/home/drew/.cache/textbelt-local-validation/tmp \
  LIVE_SMOKE=0 bash tests/smoke/run.sh
```

`LIVE_SMOKE=0` still forces the local Textbelt stub endpoint, `smoke-test-key`, and reserved synthetic phones; ports remain bound to localhost. Native cases remain restricted to offline mode. No provider credentials are needed.

## Recorded checks and limits

Before the edit, a config-only expectation for the 2026.9.4 override failed with exit 1: Compose resolved 2026.8.2. After the one-line interpolation, config-only checks verify the unset/empty default and explicit override. Compose config validates YAML resolution without pulling an image or starting containers. The coordinator then ran the actual 2026.9.4 smoke successfully; its evidence is recorded below.

Prior 2026.8.2 proof remains [Stage 4 local validation](stage4-local-validation.md): coordinator run 5 exited 0 with 25 verdicts and nine actual INTENT-only traces; recorded whole-suite verification was 448 passed with 93.29% coverage. These are prior results, not fresh execution for this YAML/documentation change. No new candidate was deployed and no fresh full 448-test suite was run for this change.

## Actual 2026.9.4 evidence

The coordinator ran the unchanged product baseline `94bdb9575ccfd836928b12a5b85622c753fd5f94`; the optional Compose image setting was the sole harness delta. Exact WSL command:

```powershell
wsl -d Ubuntu -- bash -lc 'set -o pipefail; cd /mnt/c/Users/dstro/.codex/worktrees/textbelt-assist-stage0/Textbelt && mkdir -p /home/drew/.cache/textbelt-oct2-smoke/tmp && TMPDIR=/home/drew/.cache/textbelt-oct2-smoke/tmp HA_SMOKE_IMAGE=ghcr.io/home-assistant/home-assistant:2026.9.4 LIVE_SMOKE=0 GITHUB_RUN_ID=codex-oct2-ha-compatibility bash tests/smoke/run.sh 2>&1 | tee /home/drew/.cache/textbelt-oct2-smoke/coordinator-ha-2026.9.4-run-1.log'
```

Observed image provenance:

- Tag/resolved Compose image: `ghcr.io/home-assistant/home-assistant:2026.9.4`.
- RepoDigest: `ghcr.io/home-assistant/home-assistant@sha256:3e6710a7ab2a61311d9d899b719f6c3657791c63e8f4942cec4ebc42401d6b76`.
- Running image ID: `sha256:cd74b0e02cee84de9f53b0f8fc079c8979796b81a6b02e1ee0cd09f038703afd`.

Log: `/home/drew/.cache/textbelt-oct2-smoke/coordinator-ha-2026.9.4-run-1.log`. Artifacts: `/home/drew/.cache/textbelt-oct2-smoke/tmp/textbelt-ha-artifacts-hnKEta`. Project: `textbelt-sms-smoke-codex-oct2-ha-compatibility-20255`. `smoke-report.txt` records `live_smoke=0` and `exit_code=0`. The coordinator result and `compatibility-artifact-proof.txt` in `.superpowers/sdd/textbelt-native-assist-handoff/` were read in full for this evidence update; the documentation owner did not rerun Docker or the suite.

The retained evidence contains 25 passing check records (23 distinct labels; some repeat across senders/phases) and nine complete actual INTENT-only pipeline traces, each exactly `run-start`, `intent-start`, `intent-end`, `run-end`. Checks cover key-only migration/native disabled, retained sender memory and sender isolation, preferred pipeline changes, correlated unauthorized sender HTTP 403, signed rejection/replay/controls and /new, ordered multipart, independent quota/status failure recovery, signed legacy/disabled paths, and restart with no active/queued replay and fresh context.

Migration produced version 2 and a 64-character generated webhook ID, preserving unrelated options and entity/unique IDs. Synthetic partial rejection retained known ID 20 and quota 81→80 (one debit); accepted-disconnect uncertainty retained known ID 22 and quota 80→78 (two debits). Sensor known-ID arrays agree; these stub accounting observations do not establish actual provider charging.

One config-entry-keyed metadata Store retained 19 outgoing records and 15 records in each duplicate/packet ledger. Recursive key inspection found no transcript/text/message, signature/API-key, conversation/session/context fields. The previously audited normal-stop `metadata_not_durable` warning recurred; no Store write error was found. Home Assistant queues shutdown snapshot persistence for a later final-write event; this run does not claim immediate confirmation of every write requested during stopping.

Cleanup verification found the project containers, named volume, network, and resolved verified temporary config absent. Local compatibility against this observed image and fixture passed; no user Home Assistant deployment, real provider credentials/SMS, public callback, carrier, satellite, or actual charging test occurred.

## Remaining limits and live gates

A deterministic local run proves framework plumbing only within its observed image and fixture. It does not prove real ChatGPT behavior, household device actions, public authenticated callback reachability, carrier replies/delivery, satellite delivery, or actual provider credit charging.

Before a live trial, retain explicit candidate deployment authorization, a verified backup/rollback path, exact deployed candidate provenance and native service registration, approved destination and selected pipeline, approved API-key/credential mechanism, authenticated public callback verification, and explicit paid-SMS authorization with a bounded credit budget. The image override itself satisfies none of these gates. See [carrier trial procedure](native-assist-carrier-trial.md) and the local live-readiness report for current observations.
