# Stage 4 local validation

Status: **PASS for the deterministic local Home Assistant 2026.8.2 smoke run**.
Coordinator run 5 completed with `LIVE_SMOKE=0` and exit 0. Final coordinator
verification passed: 448 tests in 36.33 seconds, 93.29% coverage, Ruff clean and
62 files already formatted. Shell syntax checks also passed.
Provider, external callback reachability, carrier and satellite acceptance remain
unverified by this local run.

## Reproduction

Pinned HA image: `ghcr.io/home-assistant/home-assistant:2026.8.2`. Stub and cleanup
helper image: `python:3.14.2-alpine`. Linux/WSL, Python 3, Docker and Docker Compose
are required; localhost ports 8080/8123 must be free.

```bash
LIVE_SMOKE=0 bash tests/smoke/run.sh
python -m pytest tests/smoke/test_exercise_api.py tests/smoke/test_textbelt_stub.py tests/smoke/test_fixture_files.py --no-cov -q --tb=short
python -m ruff check tests/smoke
python -m ruff format --check tests/smoke
bash -n tests/smoke/run.sh
```

For WSL installations whose `/tmp` disappears between processes, use a persistent
artifact parent:

```bash
mkdir -p "$HOME/.cache/textbelt-local-validation/tmp"
TMPDIR="$HOME/.cache/textbelt-local-validation/tmp" LIVE_SMOKE=0 bash tests/smoke/run.sh
```

Offline mode forces `http://textbelt:8080`, `smoke-test-key` and reserved synthetic
phones. Native cases never run in live mode; published ports bind only to
localhost. `https://ha.example.com` is configuration-only reserved example space:
the helper discovers its generated path in a captured send, then posts signed
bytes to local HA. It never contacts that hostname. A registered deterministic
conversation agent routes no SMS; the production native adapter executes actual
HA `PipelineRun`/`PipelineInput` with no user routing automation or script.

## Check matrix

| Check | Observable assertion | Result |
|---|---|---|
| Helper signing/discovery/offline key | Independent timestamp + exact-byte HMAC; permitted generated host/path; inherited key override | PASS, focused tests |
| Stub FIFO/unknown/reset | Actual loopback HTTP; accepted-disconnect debits once; no hidden attempt; reset preserves quota | PASS, focused tests |
| Startup/outbound/notify | Loaded single entry/public services; masked notify and successful timestamp | PASS, local HA |
| Migration | Stopped key-only version 1 becomes version 2/native disabled; unrelated option/entity identities preserved | PASS, local HA |
| Greeting/two turns/isolation/preference | Actual sends; INTENT-only debug events; remembered alpha/IDs; fresh trusted contexts; A/B preference | PASS, local HA |
| Signed rejection/replay/controls/new | Matching accepted-ID unauthorized sender rejected; no extra calls/runs/events/sends for rejection/replay/controls; /new resets without pipeline | PASS, local HA |
| Legacy/disabled | Fixed signed events-only compatibility; raw-phone URL exception; disabled generated endpoint emits only event | PASS, local HA |
| Multipart/partial/unknown | Ordered bounded prepared parts; stop at failed second part; visible outcome/known IDs/metadata/quota debit; no pipeline/send retry | PASS, local HA |
| Quota/status failure/recovery | Independent HTTP/malformed failures and recovery without extra submissions | PASS, local HA |
| Restart | Active/queued turns not replayed; fresh turn 1/new context; initiating correlation and generated webhook stable | PASS, local HA |
| Cleanup guards | Wrong-project/symlink refusal; child symlinks do not escape fixture mount | PASS, focused tests |
| Runtime cleanup | Unique project containers/volumes/networks and disposable config removed | PASS, coordinator inspection |
| Whole repository suite/coverage/Ruff | Final checks after the decoder regressions | PASS, 448 tests / 93.29% coverage; Ruff / format clean |

## Recorded evidence

Successful run log:
`/home/drew/.cache/textbelt-oct2-smoke/coordinator-run-5.log`.
Preserved artifacts:
`/home/drew/.cache/textbelt-oct2-smoke/tmp/textbelt-ha-artifacts-kmUpGU`.
`smoke-report.txt` records project `textbelt-sms-smoke-codex-oct2-coordinator-1079`,
`live_smoke=0` and `exit_code=0`.

`stage4-evidence.json` contains 25 recorded case verdicts and 9 real pipeline traces.
Every trace contains exactly `run-start`, `intent-start`, `intent-end`, `run-end`.
It records the retained same-sender memory, isolated second sender, changed
preferred pipeline, matched unauthorized sender rejected with HTTP 403, /new and fresh postrestart turn.
The partial rejection records known ID 20 and synthetic quota 81→80; accepted-then-
disconnected records known ID 22 and quota 80→78. Public failure/outcome attributes,
known-ID Store retention and uncertain-ID exclusion agree with that stub ledger;
replays add neither pipeline execution nor submission. These synthetic debit
assertions do not establish provider/carrier credit charging.

Coordinator inspected one metadata Store with no text/message/signature/API-key/
conversation/session fields, and confirmed project resources and
`textbelt-ha-config.m7vGW5` were removed. Cleanup uses stopped-container copies
and a no-network helper mounted only to the verified marked temporary config;
it leaves user HA files and permissions untouched. Native helper tokens use stdin;
legacy API helper tokens still use `--token` arguments. Artifact collection omits
HA auth storage and does not intentionally save auth tokens.

Final focused owner command: 25 tests passed in 3.08 seconds on pinned WSL
Python 3.14.2 / HA 2026.8.2. Scoped Ruff passed, format checked 10 files, shell syntax and
diff whitespace checks passed. Coordinator final checks passed: `python -m pytest -q` yielded 448 passed in
36.33 seconds at 93.29% coverage; `python -m ruff check .` passed and
`python -m ruff format --check .` reported 62 files already formatted.
`bash -n tests/smoke/run.sh` passed. Actual Docker and full-suite execution
belong to the coordinator.

## Repaired harness failures

The successful result follows four failed coordinator attempts, retained in
`coordinator-run-1.log` through `coordinator-run-4.log` under the same log parent.
They are not passing native validation runs:

1. Host migration write hit HA-container file ownership. Stopped-container
   copy/edit/copy-back now preserves mode; named artifact reads and guarded
   isolated cleanup also use ownership-safe operations.
2. Immediate disk-version assertion preceded entry readiness/deferred HA storage
   saving. A bounded wait now requires the loaded current entry and saved version 2;
   actual setup/migration error states fail clearly. All migration assertions remain.
3. The `.test` synthetic hostname was rejected by frozen production validation.
   The reserved `ha.example.com` placeholder now passes that actual validator;
   no production URL rule was weakened and no external hostname is contacted.
4. Deliberate partial notify returned the expected plaintext HTTP 500, which the
   helper incorrectly decoded as JSON. It now permits plaintext only for an exact
   expected error status; mismatched statuses and invalid successful JSON still fail.

Focused regressions cover delayed migration persistence, terminal migration error,
actual placeholder validation, expected HA-shaped 500 plaintext, wrong statuses and
invalid-success JSON. Initial socket/import test-fixture issues were corrected
separately and were not product failures. The normal-stop metadata warning was audited against pinned HA Store behavior:
HA enters stopping before the integration shutdown callback, so Store queues the
snapshot for a later final-write event and the adapter reports the immediate
write as unconfirmed. The retained Store contains 19 outgoing records and 15
records in each replay ledger; no Store write error appears in the log. Earlier
confirmed native admissions retain their durability guarantee. This does not
claim that all writes requested during stopping are confirmed; no necessary
product fix was identified by that audit.

## Limits

The fixture establishes local deterministic pipeline plumbing/context against
pinned HA. It does not prove real LLM quality, household device actions, external
callback reachability, provider retries, carrier or satellite delivery. Exhaustive
parser/capacity/lifecycle boundaries also have producer unit coverage; this compact
smoke matrix is not exhaustive. Provider acknowledgments/retries/inbound IDs/reply
windows and request maximum remain unresolved. Historical character evidence is
bounded to the reviewed 124-character GSM policy and one account/US-T-Mobile trial;
no expanded fidelity claim is made. The 160-septet/five-prepared-part limits constrain
integration submissions, not guaranteed credit cost or carrier segment delivery.
Local correlation/dedup policy is not an exactly-once or provider-window guarantee.

Reply-state Store metadata excludes transcript/message text; outgoing sensor
attributes may be retained by HA Recorder/history, and event consumers/agents may
retain their own content. Volatile native sessions/queues/actions are not restored
or replayed after restart. No real credentials/provider sends, carrier trial,
publication or deployment occurred in this stage.
