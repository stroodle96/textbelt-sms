# Stage 2A local validation and checkpoint

Implemented the approved standard notification stage on the isolated branch based
on `a8af991`. The user's Continue approved Stage 2A; later Assist stages remain
separate checkpoints.

## Result

The integration now exposes a standard Home Assistant notification entity per
configured recipient, with title support and the existing shared preparation and
batch sender. Recipient settings accept one explicit international number per
line, normalize presentation separators, deduplicate, and reload automatically.
Validation checks 2-15 ASCII digits after a nonzero country-prefix digit and `+`;
it does not verify assignment or deliverability or guess a country.

Registry identity uses a deterministic phone digest and config-entry identity;
entity IDs do not contain the raw destination. Friendly names show the last four
digits. Removing a recipient leaves its registry entry unavailable, preventing
sends while preserving identity and user renames for re-addition. Reordering does
not change identity. Empty recipient settings preserve legacy outbound operation.

Notifications work without an external callback or Assist configuration, and
recipients do not grant future Assist authorization. Titles and bodies pass through
the same sender. Rejected, partial, uncertain, or invalid submissions raise visible
HA errors and do not advance the notification success timestamp. Quota refresh is
requested once per attempt and remains independent of submission success. The
existing dynamic `textbelt_sms.send_sms` action remains available.

## Verification

Pinned Home Assistant 2026.8.2, Ubuntu WSL, Python 3.14.2, Ruff 0.16.8.

| Check | Result |
| --- | --- |
| Product focused tests | 34 passed |
| Smoke helper focused tests | 8 passed |
| Full `python -m pytest -q` | 312 passed; 96.31% integration coverage |
| `python -m ruff check .` | Passed |
| `python -m ruff format --check .` | 43 files already formatted |
| Native staged whitespace check | Passed |
| Independent spec, quality and cross-module review | Approved; no important findings |
| Real HA/local Textbelt stub smoke | Passed, exit 0; four synthetic requests; live_smoke=0 |

Focused failing tests preceded implementation. Cases cover titles, multiple
recipients, automatic options reload, empty recipients, number validation,
deduplication, unrelated option preservation, removal/re-addition/reordering,
user-renamed identity, inactive runtimes, unsupported content, partial/unknown/
rejected submission, unchanged failure timestamps, and independent quota refresh.

The real HA smoke retained the three legacy request cases, then configured a
recipient through the native options flow, discovered its notify entity, sent a
standard titled notification, and verified the timestamp and fourth stub request.
Both the runner and helper exclude this extra case from live smoke mode. The
coordinator independently checked the preserved request ledger: all four requests
used the synthetic smoke key, and the fourth contained exactly:

```text
Water leak: Water was detected in utility room.
```

The smoke's root-owned temporary HA configuration required follow-up cleanup;
its resolved task-specific path was verified and removed. Container cleanup
completed. Sanitized local-stub evidence and validation logs remain in the private
handoff folder. No provider requests, real SMS, saved-key access, deployment,
push, merge, or release occurred in Stage 2A.

## Alert example

Select the actual notification entity in Home Assistant's action editor (or rename
it to the example entity ID first):

```yaml
action: notify.send_message
target:
  entity_id: notify.my_phone
data:
  title: Water leak
  message: Water was detected in utility room.
```

The notification timestamp records successful submission, not carrier delivery;
the integration's delivery sensor tracks subsequent per-part status.

## Sources and next stage

The implementation was checked against the installed, pinned HA code and the
[NotifyEntity documentation](https://developers.home-assistant.io/docs/core/entity/notify/)
and [options-flow documentation](https://developers.home-assistant.io/docs/core/integration/options_flow/),
read October 1, 2026. The pinned API takes precedence over newer example syntax.

Stage 2B adds selected/default Assist pipeline options and the text pipeline
adapter. Native incoming conversations belong to the later Stage 3. Both remain
unimplemented and require their planned approval checkpoints.
