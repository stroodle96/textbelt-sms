# Stage 0 grouped carrier results

Seven authorized short messages ran September 30, 2026, 23: 50: 28–23: 51: 11 EDT
(October 1, 03: 50: 28–03: 51: 11 UTC), to the designated US/T-Mobile destination.
All seven POSTs were accepted; every final provider status was DELIVERED.
Quota decreased 349 → 342, exactly one credit each. Private phone/key/IDs omitted.

| Group | Candidates | Sent septets | Copied core fidelity |
| --- | --- | --- | --- |
| G1 | 45 default entries | 54 | Eleven characters converted to question marks |
| G2 | 45 default entries | 54 | Exact |
| G3 | 35 default entries | 44 | Exact |
| G4 | Nine extension entries | 27 | Exact |
| G5 | LF | 10 | Exact actual LF |
| G6 | CR | 10 | LF copied; normalization location unresolved |
| G7 | Form feed | 11 | Apparently CR copied; normalization location unresolved |

Position-by-position comparison of user copies confirms G1 converted Δ Φ Γ Λ Ω
Π Ψ Σ Θ Ξ and ¤ to U+003F. Every other copied G1 core position matches. G1 also
has a separate actual newline plus `Reply STOP to unsubscribe`: 26 code points
and 26 GSM septets. This suffix is provider-added evidence outside the raw core.
G2–G5 copied core strings match; CR/form-feed exact fidelity is unproven because
clipboard/chat normalization can change controls. They are excluded from the
conservative proposal. No conversion is attributed to a particular transport
hop without evidence.

The 137 candidates therefore yield 124 proposed exact-fidelity characters:
137 minus ten Greek characters, ¤, CR and form feed. See the explicit inactive
[character policy proposal](probes/v1-character-policy-proposal.json), which
records each character's group and zero-based core position. This is one trial,
not universal provider/carrier support or approved product policy.

Fifteen later boundary POSTs cost 21 more credits. Total 28 credits 349 → 321,
maximum $1.68 at supplied $3/50 ceiling; five-credit buffer remains unused.
All 22 paid requests ultimately reported DELIVERED. User reports 22 received texts;
exact boundary copies/segmentation remain pending. The extra undownloadable MMS
was reported at a different time; investigation stopped. No further sends.

See [boundary results](stage0-boundary-results.md) and
[sanitized observations](probes/v1-observed-results.json). The original 177-record
pending corpus is unchanged; grouped evidence is not an individual exhaustive
API sweep. No product files or runtime policy were changed by this research.
