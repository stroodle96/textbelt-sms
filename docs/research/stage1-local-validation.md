# Stage 1 local validation and checkpoint

Implemented the user-approved shared preparation/delivery stage on the isolated
branch based on `1b9a42e`. User approved the 124-character policy, a 160-septet
prepared-part budget, and a five-part integration cap on 2026-10-01. These are
integration defaults, not a provider hard maximum or guaranteed credit limit.

## Behavior

- The immutable runtime policy exactly matches all 124 approved evidence entries;
  the original 13 exclusions and historical observations remain unchanged.
- Preparation preserves permitted characters and meaningful values, normalizes
  supported presentation markup/punctuation, and validates every completed part.
  Automation messages that are empty, unsupported, or too long fail before sending.
- Parts include their labels within the budget. Future Assist callers can request
  compact text, an empty-response fallback, and visible bounded shortening.
  No Assist adapter or notify entity is introduced in this stage.
- The shared sender serializes whole batches and retains known IDs on partial,
  rejected, cancelled, or unknown outcomes. It never automatically retries.
- The existing send_sms action uses this sender. Existing entity IDs, legacy phone
  forms, webhook plumbing, and independent quota refresh remain. Status attributes
  include every accepted ID and per-ID delivery state. A batch is delivered only
  after complete submission and delivery of every part.
- Send/status timeouts are 20/10 seconds; redirects are disabled. API errors are
  sanitized, cancellation propagates, and malformed send replies remain uncertain.

## Verification

Ubuntu WSL, Python 3.14.2, existing isolated test environment, Home Assistant
2026.8.2, and Ruff 0.16.8. No live provider requests or credential reads.

| Check | Result |
| --- | --- |
| Final full `python -m pytest -q` | 296 passed; 96.02% integration coverage |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 39 files already formatted |
| `bash tests/smoke/run.sh`, with live mode and endpoint override explicitly unset | Passed, exit 0; real HA against local Textbelt stub |
| Approved evidence versus runtime policy comparison | Exact 124-character match; 13 exclusions preserved |
| Independent API review | Approved |
| Independent formatter review | Approved after quoted-URL query regression fix |
| Independent delivery and cross-module review | Approved |
| Native staged whitespace check | Passed |

The final suite includes 152 formatter, 64 API, and 51 sender/service/sensor/quota
focused cases. Expected failing tests preceded implementation. Review found and
fixed a URL apostrophe case; nine new regressions cover bare, Markdown, and HTML
links without changing query values. Other tests cover two-digit labels, generated
copy budgets, malformed responses, authentication errors, cancellation, concurrency,
partial delivery, quota outages, and unload/stale-update handling.

The real HA smoke covered configuration, sending, rejection, quota failure/recovery,
restart, status refresh, and the existing webhook using the deterministic stub.
Its cleanup logged permission warnings for temporary root-owned HA files;
subsequent checks confirmed the named temporary paths and Docker containers were
absent. The smoke log is retained in the private local handoff folder. The final
full unit/lint run occurred after the URL fix; that fix is covered by the added
formatter tests and does not change the smoke's plain-text request cases.

## Preparation examples

Input containing a bold Kitchen heading, bullet markers, and a Unicode minus and
degree sign produces:

```text
Kitchen
- Temperature: -2.5 degrees C
- Door: not open
```

A 161-character all-A message produces two labelled parts with lengths 160 and 13,
including `(1/2) ` and `(2/2) `. A 900-character all-A Assist reply produces five
parts with `Response shortened.` inside the final budget. The same oversized
input in automation mode fails before the first POST. An unverified emoji produces
an explicit unsupported-character error rather than silent deletion or `?`.

## Limits and next checkpoint

The evidence remains scoped to the tested account/carrier; provider hard maximum,
wire segmentation, and later reply-contract gaps remain unknown. Provider-added
sender/STOP text may add credits. No real sends were added during Stage 1; the
prior trial remains 28 credits, at most $1.68 at the user's highest supplied rate.

Stage 2A (standard Home Assistant notify entity) and Stage 2B (Assist adapter/options)
remain unimplemented and require the plan's next approval. No push, merge, release,
or deployment occurred.
