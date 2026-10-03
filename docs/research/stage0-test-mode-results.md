# Stage 0 test-mode control results

Executed September 30, 2026 America/New_York. The first control ran at
22: 01: 59–22: 02: 02 EDT (October 1, 02: 01: 59–02: 02: 02 UTC); the remaining five
ran at 23: 45: 26–23: 45: 51 EDT (October 1, 03: 45: 26–03: 45: 51 UTC).

Six authorized POST controls used the documented `_test` key suffix. No paid
send was performed in this control sequence. Private numbers, keys and returned
message IDs are omitted. The initial quota was 349. Independent reconciliation
and all subsequent before/after quota observations remained 349: observed debit
zero credits. The first request was not repeated after its follow-up quota read
failed; a later independent read reconciled the balance.

| Control | Payload | HTTP | API success | Observed result |
| --- | --- | --- | --- | --- |
| Valid short | `A B` | 200 | true | Accepted test response |
| Missing message | Field omitted | 200 | false | Missing-message error |
| Empty message | Empty string | 200 | false | Same missing-message error |
| Invalid phone | `A B`, deliberately invalid destination | 200 | true | Destination invalidity did not reject this test request |
| Length hypothesis | 512 repeated ASCII A | 200 | true | Test accepted; no maximum established |
| Bullet/non-BMP | A, U+2022, U+1F600, B | 200 | true | Test accepted; no carrier/encoding support established |

The two failures reported: `Missing message parameter. Your request may be
malformed.` HTTP 200 is transport success even when API `success` is false.

## Interpretation and decision

These controls prove missing/empty-message checks on this test path and observed
no quota deduction for these six requests. Invalid-phone acceptance demonstrates
that test acceptance is insufficient to establish production destination validity.
The accepted length and Unicode samples do not prove production character or
length validation, nor establish that those particular checks are definitely
bypassed: neither sample is documented as necessarily invalid in production.
The current hard message maximum remains unresolved.

The 177-probe `_test` sweep is therefore skipped. Relevant content validation
coverage is unestablished; running it would not justify a production allowlist.
The versioned 177-record corpus remains `not_run`, with unknown API verdicts,
unconfirmed carrier verdicts and unknown fidelity. These six controls are a
separate evidence set and must not overwrite corpus verdicts.

Returned IDs are not documented as synthetic or delivery proof. No user handset
receipt confirmation was available at this checkpoint, so non-delivery is not
empirically confirmed. The test path's no-debit observation must not be expanded
into a no-delivery claim. No uncertain POST was automatically retried.

At this historical control checkpoint, grouped carrier probes and boundary
checks were the next proposed work. Seven grouped probes and fifteen boundary
probes subsequently executed; see [grouped results](stage0-carrier-results.md)
and [boundary results](stage0-boundary-results.md). The combined trial spent
28 credits, stopped at the reserve, and requires no further POSTs. Grouped
copied receipts now support a proposed character set; boundary exact fidelity
and the overall Stage 0 checkpoint remain pending. The original 177-record
fixture is unchanged and the exhaustive test-mode sweep was skipped.

## Evidence scope

Reviewed local sanitized `test-mode-controls.json` and
`test-mode-controls-remaining.json`; this report's author made no API calls or
credential reads. Documentation context: [provider source research](provider-source-research.md)
and https://docs.textbelt.com/#testing-this-api . The private execution artifacts
remain outside the shareable report; account identifiers are deliberately omitted.
