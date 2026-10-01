# Stage 0 boundary results and final empirical checkpoint

Fifteen unlabeled boundary POSTs ran September 30, 2026, 23: 56: 15–23: 57: 52 EDT
(October 1, 03: 56: 15–03: 57: 52 UTC). Read-only followups at 03: 58: 36–03: 58: 39 UTC
resolved three earlier SENT statuses to DELIVERED; no resend occurred.

| Corpus ID | Encoding measurement | Credits | API | Final provider status | Fidelity |
| --- | --- | --- | --- | --- | --- |
| boundary-ascii-160 | 160 septets | 1 | Accepted | DELIVERED | Exact copied text |
| boundary-ascii-161 | 161 septets | 2 | Accepted | DELIVERED | Exact copied text |
| boundary-extension-80 | 160 septets | 1 | Accepted | DELIVERED | Exact copied text |
| boundary-extension-81 | 162 septets | 2 | Accepted | DELIVERED | Exact copied text |
| boundary-bmp-70 | 70 UTF-16 units | 1 | Accepted | DELIVERED | Unknown |
| boundary-bmp-71 | 71 UTF-16 units | 2 | Accepted | DELIVERED | Unknown |
| boundary-emoji-35 | 70 UTF-16 units | 1 | Accepted | DELIVERED | Unknown |
| boundary-emoji-36 | 72 UTF-16 units | 2 | Accepted | DELIVERED | Unknown |
| encoding-switch-69 | 70 UTF-16 units | 1 | Accepted | DELIVERED | Unknown |
| encoding-switch-70 | 71 UTF-16 units | 2 | Accepted | DELIVERED | Unknown |
| boundary-ascii-159 | 159 septets | 1 | Accepted | DELIVERED | Unknown |
| boundary-extension-79 | 158 septets | 1 | Accepted | DELIVERED | Unknown |
| boundary-bmp-69 | 69 UTF-16 units | 1 | Accepted | DELIVERED | Unknown |
| boundary-emoji-34 | 68 UTF-16 units | 1 | Accepted | DELIVERED | Unknown |
| boundary-ascii-306 | 306 septets | 2 | Accepted | DELIVERED | Exact copied text |

Boundary debit 21 credits 342 → 321. Including seven grouped probes, total 28 credits
349 → 321, at most $1.68 at the supplied $3/50-credit price ceiling. Five credits
remain unused from 33; the seven-credit reserve stopped further POSTs.

Unrun: `boundary-ascii-307`, `boundary-bmp-134`, `boundary-bmp-135`. The original
177-record pending fixture remains unchanged. Separate observed evidence records
six test controls, seven groups and 15 executed boundary IDs. The exhaustive test
sweep was skipped because relevant content validation was unestablished.

Observed billing is consistent with one credit at 160 GSM septets/70 UTF-16 units
and two at immediately larger tested values. Caret extension weighting and mixed
bullet samples show the corresponding change. 306 ASCII A also cost two credits.
These observations are trial-specific; they establish no hard provider request
maximum, universal credit algorithm, full Unicode support or handset segmentation.
The accepted 306-ASCII request is an observed lower bound, not a known maximum.

All 22 paid POSTs were accepted and ultimately provider-reported DELIVERED. User
reports 22 received texts. Copied A160, A161, caret80, caret81 and A306 payloads exactly match sent text. The other ten executed boundary copies remain unknown; wire segmentation is not established by these copies. The screenshot provides additional partial visual evidence.
Grouped G1–G5 now have copied evidence: G1 has eleven substitutions; G2–G5 exact
core strings. CR/form-feed copies remain ambiguous. See
[grouped results](stage0-carrier-results.md) and the inactive
[124-character proposal](probes/v1-character-policy-proposal.json).

Remaining receipt input is the other ten boundary copies and handset segmentation details. There are
no further sends or new budget requests. The user reports the extra undownloadable
MMS at a different time; investigation stopped. No inbox access is assumed.
Provider maximum/unit, reply lifetime/inbound IDs, callback retries/acknowledgments,
HELP and idempotency remain unresolved. Stop before Stage 1 approval.

The [sanitized observations](probes/v1-observed-results.json) preserve exact
payloads, code points, quota and status with explicit ID-redaction flags. Private
originals retain identifiers; no key, phone or raw HTTP is shared. Research authors
made no provider calls or credential reads in preparing these reports.
