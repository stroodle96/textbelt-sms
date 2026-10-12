# Stage 0 standards review

Reviewed 2026-09-30. Scope: offline harness/table/corpus review against primary standards; no
provider POST, source edits, or provider/carrier acceptance claim.

## Pinned primary references

- [ETSI TS 123 038 V18.0.0 / 3GPP TS 23.038 Release 18 (2024-05)](https://www.etsi.org/deliver/etsi_ts/123000_123099/123038/18.00.00_60/ts_123038v180000p.pdf), retrieved through web PDF reader September 30, 2026. Clause 6.2.1 default table printed p20; ESC note p21; clause 6.2.1.1 extension table and notes p22; clause 4 encoding capacities p10; clause 6.1.1 controls p15. Pinned reproducible edition, not a claim of newest edition.
- [ETSI TS 123 040 V18.0.0 / 3GPP TS 23.040 Release 18 (2024-05)](https://www.etsi.org/deliver/etsi_ts/123000_123099/123040/18.00.00_60/ts_123040v180000p.pdf), retrieved through web PDF reader September 30, 2026. Clause 9.2.3.24 header layout pp72-74; clause 9.2.3.24.1 concatenation pp76-77; clause 9.2.3.24.8 16-bit reference pp81-82. Printed page numbers used throughout.

## Findings

`scripts/provider_probe.py` DEFAULT matches all 127 default-table text/control entries excluding
ESC at GSM position 0x1B. No missing, extra, or substituted character found. LF, CR and space
are included; raw ESC belongs only to diagnostics. DEFAULT sequence corresponds to ascending GSM
positions with ESC omitted.

EXTENSION matches ten defined text/control entries: U+000C form feed/page break, caret, braces,
backslash, square brackets, tilde, vertical bar, euro. Its string order is not GSM position
order, which is harmless for enumeration and membership counting. Page break is ESC+0x0A; the
extension ESC+0x1B entry is reserved, correctly excluded. LF/CR each cost one septet; extension
entries cost two. CR may overwrite displayed text; standards eligibility does not imply
fidelity.

Single-message capacity is 140 octets: 160 septets or 70 UCS-2 units. For the six-octet header
with 8-bit concatenation reference, 153 septets and 67 UCS-2 units are correct. Seven-octet
headers with 16-bit references instead leave 152 septets and 66 UCS-2 units. Other information
elements reduce capacity. Escape sequences and UCS-2 characters must remain intact at splits.

`units()` correctly measures default/extension septets and UTF-16 code units for Unicode scalar
strings. It is a classifier/count, not an SMS encoder. UTF-16 emoji counts do not establish
UCS-2, Textbelt, or carrier support. Lone surrogate inputs raise encoding errors, rather than
yielding metadata; none occurs in this corpus. National-language shift tables are outside the
deliberately default-table classifier.

## Corpus and tests

Read `tests/provider/test_probe.py` and the saved JSONL. Saved counts are 127 default, 10
extension, 22 diagnostic, 16 length, 2 encoding-switch = 177. All planned section 5 boundary
hypotheses are represented without labels. Counts: caret 79/80/81 = 158/160/162 septets; emoji
34/35/36 = 68/70/72 UTF-16 units; mixed 69/70 A plus bullet = 70/71 units. A306 and BMP134
exercise two-part totals under the six-octet-header hypothesis; A307 and BMP135 exceed those
totals.

No exact standards mismatch found. At the time of this review, tests checked
counts/uniqueness and selected weights, but did not compare every entry to an
independent pinned table: retain this review as the independent table evidence.
Python execution was unavailable in the original review shell (`python`, `py`,
`python3` not found); no test-pass claim made. PowerShell independently read
corpus categories and boundary counters.

The policy file correctly leaves the production allowlist empty and activation disabled.
Standards review only validates candidate encoding metadata; every API verdict remains unknown,
carrier verdict unconfirmed, and fidelity unknown. These capacities are test hypotheses, never
provider request maxima or credit rules.

## Follow-up test coverage

After this review, `test_reviewed_primary_table_membership` added independent
code-point sets for the pinned default and extension tables, and
`test_preserved_corpus_fixture` added a frozen SHA-256 and corpus comparison.
These tests address the earlier coverage limitation. The source agent reported
99 passing tests under Python 3.14, including six provider tests. That is a
follow-up report, not an execution result from the original standards review;
final verification evidence is recorded separately. Provider acceptance and
carrier fidelity remain untested.
