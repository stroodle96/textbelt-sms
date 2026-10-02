# Minimal native SMS Assist carrier acceptance packet

Status October 2, 2026: locally prepared, **not executed**. Candidate `94bdb9575ccfd836928b12a5b85622c753fd5f94`; manifest `0.2.0`, not a new release assignment. Initial scope is one user-selected actual native SMS path: one greeting and one harmless question/reply. No real device/home-control requests, character sweep, opt-out probe or automatic resend.

## Observed live readiness

Read-only coordinator live readiness at 2026-10-02 18:42:03 UTC found HA Core 2026.9.4 running, with only `textbelt_sms.send_sms` registered and native `textbelt_sms.start_conversation` absent. The current preferred pipeline is ChatGPT Brina Assistant (`conversation.chatgpt`, English, local intents enabled); preserve the user's preference. This service inventory does not establish the deployed Git SHA or public callback reachability. The native trial cannot run in that observed state: an explicitly authorized candidate deployment and verified service registration are prerequisites. The coordinator's actual offline HA 2026.9.4 smoke passed on October 2, 2026 with `LIVE_SMOKE=0` and exit 0: 25 recorded checks and nine complete INTENT-only pipeline traces. The product baseline remains `94bdb9575ccfd836928b12a5b85622c753fd5f94`; the optional Compose image setting is the sole harness delta. This is local compatibility evidence, separate from the prior 448-test/93.29% result and from unrun live acceptance. See [HA 2026.9.4 compatibility evidence](native-assist-ha-compatibility.md).

## Inputs required before execution

- Applicable deployment authorization, deployed candidate commit and exact HA version; verified HA backup before risky changes and a recorded rollback candidate. Confirm old SMS-to-Assist routers disabled.
- User-designated consenting US recipient/device and actual path: T-Mobile cellular or actual Starlink/T-Satellite. Record device/OS, carrier/account eligibility and evidence of transport mode. Keep raw phone numbers and credentials out of tracked docs.
- Explicitly authorized provider key mechanism and eligible paid account for US replies. Do not read/reuse the old DPAPI secret or closed 33-credit Stage 0 allowance. User supplies a new approved credit exposure/reserve and approval for up to six provider submissions. Do not use a historical quota as current balance.
- Selected pipeline ID or preferred plus its currently resolved pipeline/agent. Choose an arithmetic-capable pipeline with household controls/tools unavailable for this trial; a request to avoid tools alone does not enforce that restriction. Record any temporary configuration and its authorized restoration plan.
- Native Assist enabled with only the independently authorized trial sender as appropriate, actual public HTTPS generated callback reachable, and signed callback admission/correlation observable without retaining a key, raw signature, raw endpoint identifier or inbound payload with phone values.
- A way to observe actual quota before/after and accepted IDs/statuses without key-bearing URL logs. Pause unrelated sends on the same key with applicable authorization, or mark debit attribution confounded and do not proceed to another stage. Decide a five-minute operator observation deadline; this is a trial stop deadline, not a claimed provider reply/delivery window.

## Submission and credit boundary

The greeting prepares to one part. One inbound question can cause up to five automatic response parts, including a safe fallback/error response. **Initial plan: at most six provider `/text` submissions (one plus five), with no retries.** Handset-originated inbound texts and carrier charges are separate. The exact sample answer below is illustrative; the live pipeline's length/content is not predetermined.

This is an operator plan for exactly one greeting and one inbound question, not a product-enforced trial-wide limit. Extra distinct inbound messages, other listeners or unrelated outbound activity can add sends. Do not send additional input; stop native processing if unexpected activity appears. Product part policy stays unchanged. Five prepared response parts do not guarantee five billed credits; provider additions and carrier segmentation can charge more. A quota check after a batch cannot prevent that batch's debit. Obtain explicit approval for that exposure and a separately stated credit reserve before launching. If the user requires a strict hard credit ceiling that the authorized account arrangement cannot enforce, do not execute this native automatic-response trial.

Optional follow-on: only after the initial record is reviewed and additional authorization/reserve is confirmed, send the context question below, reserving up to five more submissions (eleven cumulative for that path). A separate carrier/path trial starts its own packet with up to six submissions and its own approved credit exposure. There is no automatic combined twelve-submission authorization. T-Mobile cellular success does not prove Starlink/T-Satellite success; actual satellite-mode evidence is required, otherwise record path unknown.

## Exact initial run sheet

1. Complete and sign off the preflight fields below. Record UTC and local time, initial actual provider quota and refreshed HA quota sensor. Record which evidence is available. Make no SMS submission when a prerequisite or credit approval is missing.
2. Once only, call the actual HA action using the designated private number:

   ```yaml
   action: textbelt_sms.start_conversation
   data:
     phone: "<AUTHORIZED_US_E164>"
   ```

   This is a placeholder template, not executable with the placeholder. The action's built-in outgoing text is exactly:

   ```text
   Home Assistant: reply with a request. Send /new to start a new conversation.
   ```

   Expected: one known accepted outgoing ID, generated callback correlation metadata, then a received greeting. Record provider status independently. Capture any appended sender/STOP text separately. Check actual quota debit; stop if unexplained/unapproved before continuing. Do not retry an ambiguous or missing greeting.
3. Only after the greeting is received and its evidence/budget check passes, reply once in that handset thread with exactly:

   ```text
   What is 2 plus 2? Answer briefly without using tools or controlling devices.
   ```

   Expected: authenticated callback correlates its `textId` with the accepted greeting and authorized sender; one native pipeline run and one response batch, zero household actions. A suitable arithmetic agent should answer 4; exact wording/part count is agent-dependent. For reference only, `2 plus 2 is 4.` is a valid one-part answer. Record all submitted parts, response IDs, arrival order, latency and received text. Safe error/fallback copy is a plumbing observation, not successful arithmetic acceptance.
4. Observe once through completion or the pre-agreed five-minute deadline; status/quota reads may continue within the authorized observation method without SMS retries. Record final quota and reconcile all known/unknown submissions. Finish the initial packet and stop. Do not send `/new`, repeat the question or switch carriers to fill missing evidence.

Optional later context input (requires the separate gate above):

```text
What was the answer to my last question? Answer briefly without using tools or controlling devices.
```

Expected: same sender/resolved pipeline context recalls 4, one additional pipeline run and response batch. Do not test restart, controls, formatting, opt-out or device actions in this minimal carrier trial; their deterministic evidence remains separate.

## Local sample preparation check

Fresh local check October 2, 2026 used the candidate's existing `prepare_message(mode="assist", compact=True)` with bytecode writes disabled, importing only message/models. No HA, provider/network request or test-suite run occurred. These literal ASCII samples normalize unchanged; none are shortened:

| Sample | Prepared parts | GSM septets |
|---|---:|---:|
| Exact built-in greeting | 1 | 76 |
| Initial handset question, checked as a reference string | 1 | 76 |
| Illustrative answer `2 plus 2 is 4.` | 1 | 14 |
| Optional handset context question, checked as a reference string | 1 | 99 |

Inbound reference preparation does not mean inbound texts go through the outbound formatter or consume provider submissions. Live agent output must be observed separately. The default finite policy remains 124 approved characters, 160 septets/part and five parts; see [provider contract](textbelt-provider-contract.md) and [local evidence](stage4-local-validation.md).

## Stop and rollback

Stop on unknown/timeout outcome, failed/partial response, unexpected debit, duplicate pipeline/action/submission, unauthorized activity, invalid/unobserved authentication, wrong carrier path or expired observation deadline. Do not retry uncertain submissions or repeat an action. Preserve masked evidence and actual quota, and distinguish already accepted IDs from unknown requests. An API timeout can hide a paid accepted request; inability to observe an ID is not proof of zero debit.

With the previously authorized trial configuration owner, disable native Assist to stop further native turns, leaving the old router disabled. Cancellation cannot retract accepted SMS or completed actions. Check HA for any execution before considering another trial. Restore recorded temporary pipeline configuration; if an authorized deployment rollback is necessary, use the approved candidate/verified backup procedure. Do not delete metadata, reset quota, replace credentials or publish as a recovery step.

Provider STOP opt-out and recipient START opt-in are account behavior; the integration excludes exact trimmed STOP/START/HELP from native execution and automatic replies. Do not test these unsolicited or bypass an existing opt-out. Callback acknowledgment/retry rules, inbound-message IDs and reply windows are unresolved. One successful signed callback supplies instance evidence, not verified general retry semantics.

## Result template (one copy per actual path)

All fields below begin **NOT RUN / UNKNOWN**. Save the sanitized copy only; keep private phone/key/signature details out of tracked artifacts. Record exact harmless received message bodies where possible, redacting identifying additions and declaring each redaction.

| Preflight / execution field | Result |
|---|---|
| Candidate full commit / installed manifest / deployment verification | NOT RUN |
| Backup verified / authorized deployment and rollback reference | NOT RUN |
| HA version / date UTC and timezone / operator | NOT RUN |
| Provider account alias / reply eligibility / authorized key mechanism reference (no secret) | UNKNOWN |
| Designated recipient alias or last four / device model / OS / consent | UNKNOWN |
| Carrier / country / exact cellular or satellite path / transport-mode evidence | UNKNOWN |
| Pipeline setting / resolved pipeline and agent / controls-tools restriction | UNKNOWN |
| Old routers disabled / independent sender authorization | NOT RUN |
| Callback reachability evidence / signature-valid admission / correlation matched (masked ID + sender alias) | UNKNOWN |
| Submission approval (initial maximum 6) / credit approval and reserve / hard-cap arrangement if required | NOT SUPPLIED |
| Observation start / five-minute deadline / unrelated-send isolation | NOT RUN |
| Provider quota before / after greeting / final, with observation times | UNKNOWN |
| HA quota sensor before / refreshed after / discrepancy | UNKNOWN |
| Actual total debit / attributable debit / unexplained debit and other activity | UNKNOWN |

For each greeting/response part, add a separate row. Include rejected and unknown attempts, not just accepted IDs:

| Step / part / submission time | Prepared text and septets if observed | ID alias/masked ID / HTTP outcome | API accepted/rejected/unknown | Carrier delivered/failed/unconfirmed + status/time | Received exact/converted/truncated/unknown + exact text/additions | Latency / ordering |
|---|---|---|---|---|---|---|
| Greeting / 1 | Built-in 76-septet text | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Answer / 1..N (one row per part) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |

| Final verdict field | Result |
|---|---|
| Handset question sent once / signed callback count / correlated initiating ID | UNKNOWN |
| Pipeline runs / household actions / duplicate execution observed | UNKNOWN |
| Known accepted / rejected / unknown submissions / total attempted (initial planned maximum 6) | UNKNOWN |
| Answer equals 4 / actual response / errors or shortening | UNKNOWN |
| Response part order / end-to-end latency / deadline outcome | UNKNOWN |
| Quota debit reconciliation / reserve still acceptable | UNKNOWN |
| Stop reason / native disable / temporary settings restored / rollback if needed | NOT RUN |
| Initial-path acceptance / material uncertainty / evidence links (sanitized) | NOT RUN |
| Optional follow-on requested, authorized and separately recorded | NOT AUTHORIZED |

Verdicts remain independent: API `success` is not carrier delivery; provider `DELIVERED` is not proof of exact received text. A path passes this narrow trial only with the actual greeting/question/answer, valid admission/correlation, one pipeline execution, no household/duplicate action, reconciled submissions/debit and observed designated transport. Missing transport evidence prevents a satellite claim. This trial does not prove all-character fidelity, multipart worst-case delivery, every carrier, retry semantics or general device-control safety.
