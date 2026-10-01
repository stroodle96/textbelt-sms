# Textbelt provider contract: Stage 0 review checkpoint

The authorized API trial is complete within its budget. Overall Stage 0 review and boundary receipt fidelity remain pending. Six test-mode
controls, seven grouped character probes and 15 boundary probes have separate
[sanitized observed results](probes/v1-observed-results.json). All 22 paid POSTs
were accepted and ultimately provider-reported DELIVERED. User reports 22 texts.
Quota 349 → 321: 28 credits, at most $1.68 on the supplied $3/50 ceiling; five credits
remain unused after the seven-credit reserve stop. No more POSTs are planned.

## Current character evidence

User copied G1–G5. G1 converted ten Greek characters and ¤ to question marks;
its other positions match. G2–G5 copied cores match, including actual LF. G6/G7
control copies are ambiguous; CR/form feed exact fidelity is unproven.
[grouped results](stage0-carrier-results.md) record this evidence. Boundary exact
receipt/count/segmentation remains unknown; see [boundary results](stage0-boundary-results.md).

The [character proposal](probes/v1-character-policy-proposal.json) explicitly
lists 124 characters with GSM weights and per-character group/position evidence,
plus 13 exclusions. Status is proposed_pending_checkpoint; activation false.
The legacy [empty pending policy](probes/v1-policy-pending.json) is retained as a
historical inactive artifact superseded by this reviewable proposal. Neither is
an active product policy; no Stage 1 implementation approval is implied.

## Proposed Stage 1 preparation contract

- GSM-only output using the 124 reviewed characters; LF permitted, CR/form feed
  excluded. Unsupported meaningful content produces a visible preparation error
  or explicitly reviewed fallback; never silently delete it or substitute `?`.
- Maximum 160 GSM septets per prepared part, including titles, labels, greetings,
  fallback text and shortening notices. Proposed cap: five outgoing requests.
- 160 is an integration part budget, not a provider hard request maximum. Provider
  maximum remains unknown; 306 ASCII A was accepted and billed two credits.
- Provider-added sender/STOP text lies outside prepared text and may increase
  charging. Observed G1 suffix was 26 code points/septets including its newline.
- Preserve accepted, rejected, partial and unknown outcomes; no uncertain POST
  retry or repeated Assist action. Exact provider callback rules and remaining
  unknowns are recorded in [source research](provider-source-research.md).

These are proposed decisions for root review and the user checkpoint. Stop
before Stage 1 implementation until separately approved.

## Offline artifacts and their scope

```sh
python scripts/provider_probe.py docs/research/probes/v1-inputs-and-pending-results.jsonl --overwrite
python -m unittest discover -s tests/provider -v
```

The original 177-record input/pending fixture is unchanged and still preserves
its original pending verdicts. Fifteen of its boundary IDs have executed results
in the separate observed artifact; three remain unrun. No bulk 177 `_test` sweep
occurred. Six controls demonstrate missing/empty validation and no observed
quota debit, while content-validation coverage remains unestablished; see
[test controls](stage0-test-mode-results.md). Authoritative default/extension table
review and follow-up offline tests are in [standards review](gsm-standards-review.md).
Do not overwrite historical inputs or infer production acceptance from stubs.

## Remaining checkpoint input

Root review of the explicit 124-character proposal and copied boundary receipts/
segmentation are pending. Provider hard maximum/unit, reply lifetime/unique inbound
IDs, callback acknowledgment/retries, HELP and idempotency remain unknown. No
further sends or budget request. The separate-time MMS investigation is stopped.
