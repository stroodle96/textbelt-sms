# Textbelt provider contract: Stage 0 blocked checkpoint

Prepared 2026-09-30. Offline preparation is ready; provider and carrier validation have not
occurred. Current primary provider documentation was retrieved September 30, 2026. See [source
research](provider-source-research.md) for documented rules and each unresolved provider
question. The older cloud access failure is historical. No empirical test-mode safety result,
SMS delivery claim, or production allowlist can be established from this session.

## Reproduce offline artifacts

```sh
python scripts/provider_probe.py docs/research/probes/v1-inputs-and-pending-results.jsonl --overwrite
python -m unittest discover -s tests/provider -v
```

Output creation is exclusive by default: an existing file raises FileExistsError without
modifying its contents. Use `--overwrite` only when intentionally regenerating inputs; keep
completed observations in a separate results file.

The 177 versioned records contain 127 GSM default candidates (ESC excluded), 10 extension
candidates, 22 diagnostic Unicode/control/sequence probes and 18 exact-length/encoding
hypotheses. The tables are independently reviewed against pinned ETSI Release 18
default/extension tables; see [standards review](gsm-standards-review.md). They are candidates,
not a verified production alphabet. Every single-character probe uses actual `A + character +
B`; diagnostic sequences remain intact. Boundary messages carry no labels. Form serialization
contains only the message field, excludes phone/key, and round-trips exactly including
LF/CR/CRLF, literal backslash-n, quotes, plus, ampersand, percent and equals. UTF-8 hex, code
points, GSM weights and UTF-16 units are recorded before any normalization.

Once a provider maximum is documented, regenerate with `--documented-maximum N` and record its
source/unit (the generated probes use repeated A). The current artifact deliberately has no
guessed provider maximum. Missing/malformed-message controls and grouped carrier messages must
be finalized only after official test-mode, validation, rate and credit behavior is established.

## Evidence recording rules

Each record supplies separate API (`accepted/rejected/unknown`), carrier
(`delivered/failed/unconfirmed`), and fidelity (`exact/converted/truncated/unknown`) verdicts.
All current results are unknown/unconfirmed, with null HTTP status, response, text ID, quota,
receipt, date and account/country/carrier scope; status timeline is empty. `not_run` is not a
sandbox success. When execution is approved, copy inputs to a separately versioned results file;
retain raw payloads and fill sanitized responses, quota deltas, timelines and received-text
evidence. Exclude keys, private numbers and unnecessary account identifiers. Accepted POSTs and
uncertain outcomes must never be automatically retried. No network executor is embedded in this
harness while non-delivery semantics remain unknown.

## Policy decision

See [pending policy](probes/v1-policy-pending.json). The production allowlist is empty and
activation is blocked. No candidate, including ordinary ASCII, has API plus carrier fidelity
coverage here. Provider message limits, encoding, automatic concatenation, credit costs, reply
lifetime, precise segment charging and measured validation remain null. Proposed integration
caps/timeouts in the plan are proposals only. No runtime ProviderPolicy or product behavior was
added or changed.

Next checkpoint: establish `_test` safety and actual content validation using controls, then
execute the finite raw sweep under authorized credentials. A separate user-designated
destination and explicit credit budget are necessary for carrier coverage; compare grouped
receipts and bisect uncertain groups. Freeze only individually supported output characters and
exact policy values. Stop before Stage 1 until its separate approval.

## Documented contract versus measured policy

Official /text documentation establishes fields, form/JSON examples, response fields, key-suffix
_test validation with no credit deduction, U.S.-only paid-key replies, and HMAC-SHA256
verification of timestamp string plus raw JSON using the API key. UNIX timestamp seconds must
not be more than 15 minutes old. No empirical callback or _test execution occurred. The
conditional test wording implies no send but does not explicitly guarantee no delivery or
content validation.

Official status vocabulary is DELIVERED/SENT/SENDING/FAILED/UNKNOWN with one-week lookup
retention. DELIVERED is carrier-dependent confirmation. Quota counts segments; failed delivery
can still cost credits. General advice is no more than 1–2 SMS/second. Sender identification and
first-contact STOP instructions may be appended. URLs need account whitelisting. STOP opt-out
and START opt-in are provider-handled; HELP behavior remains unknown.

The FAQ's 256-byte auto-segmentation statement and usual 120 segment length lack a precise
current hard request limit/byte definition. Do not set a documented maximum from this sentence.
Reply lifetime, unique inbound identity, callback acknowledgment/retries, polling cadence and
POST idempotency are unspecified. See source research for URLs and detailed qualifications. The
independent pinned Release 18 standards review confirms candidate table membership and encoding
weights; candidate alphabets still require API/carrier evidence.

## Authorized controlled execution checklist

- Obtain user-authorized credential mechanism; keep key out of arguments, logs and reports. Obtain designated destination, country/carrier, maximum API requests and explicit live-send/credit budget. Do not treat free textbelt key as non-delivery mode.
- Establish _test behavior before any sweep using valid short message, missing/empty message, invalid phone and excessive/unsupported-content negative controls. Capture sanitized HTTP/body, quota and any receipt observations. No automatic uncertain POST retry.
- Resolve the hard max/unit with provider clarification before labeling any probe documented-over-limit. 255/256/257 UTF-8 bytes are exploratory hypotheses only.
- If test mode bypasses content validation, keep character/length acceptance unknown. Execute relevant raw finite sweep only where controls establish validation coverage.
- Under separate carrier budget, cover every proposed output character, compare exact received content and ordering, measure quota deltas and auto-appended sender/STOP effects; bisect uncertain groups without treating nonreceipt as a character ban.
- Test documented signature canonicalization offline, then verify actual callback, reply correlation/window, duplicate behavior and opt-outs under approved live scope. No native Assist endpoint activation from documentation alone.
- Freeze only supported finite output policy and exact limits, present actual results and remaining unknowns, then stop before Stage 1 approval.
