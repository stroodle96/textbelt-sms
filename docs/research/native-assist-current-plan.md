# Textbelt SMS: Native Assist, Notifications, and Reliable Message Handling

**Repository:** https://github.com/stroodle96/textbelt-sms

**Purpose:** A self-contained handoff for an agent who has not seen the planning conversation. This current plan is mirrored byte-for-byte at active worktree docs/research/native-assist-current-plan.md. Historical primary-checkout .handoff-stage0/HANDOFF.md and original-plan.md remain unchanged.

**Binding current scope — 2026-10-03 01:15 UTC:** The user prohibits testing on their live Home Assistant instance. All further development validation uses disposable isolated local HA with the deterministic Textbelt stub. The user's live HA is excluded as a test or deployment-validation target: no candidate installation, native opt-in, restart, check-only helper, probe, backup, recovery or service change there as part of this work. Restored production MCP access or a recovery-key availability answer does not lift this restriction. Prior live readiness, backup and failed check-only receipts remain historical evidence. Live-HA access/recovery-key questions are superseded for current local work and need no answer. Future actual SMS requires separate authorization, a designated recipient/key mechanism and a new explicit numeric credit/send budget; carrier/satellite/live-provider acceptance remains NOT RUN/UNKNOWN. The user separately authorizes continued implementation and push/PR creation once the changes are ready and appropriate local checks pass. Development PR [#104](https://github.com/stroodle96/textbelt-sms/pull/104) is open against main, with published head cbb22ab74166b3308ba231277197bb56d84de03c verified by the coordinator. The next current action is to follow PR CI and fix actual failures locally under the user authorization, then verify CI on the latest published head. Carrier/provider UNKNOWN/NOT RUN limits remain disclosed and do not block this honest development PR. Merge and release remain unrequested and pending. Completed recorded validations are not reopened or rerun merely because scope changed.

**PR follow-up status — October 3, 2026:** [PR #104](https://github.com/stroodle96/textbelt-sms/pull/104) is open against main at verified published head cbb22ab74166b3308ba231277197bb56d84de03c. The fresh final local suite passed 448 tests with 93.29% coverage in 58.97 seconds; Ruff, syntax and release-contract checks passed. All four non-Hassfest PR checks passed on that initial head: Ruff, HACS, unit tests and isolated real-HA/local-stub smoke (3 minutes 39 seconds). Initial GitHub Hassfest failed on manifest key order (domain/name, then alphabetical) and the redundant aiohttp requirement supplied by Core. The metadata owner reproduced the failure with the official pinned Hassfest locally, then verified the two-field metadata-only correction passes: exit 0, Invalid integrations 0. Existing focused release-contract checks passed 12 tests in 1.78 seconds and CLI v0.3.0 passed. Corrected manifest SHA256 is 474F2E3A1E9FF91D1205B9792D07A5AC9D5DA02BD9F8AAC54E89A48F5ABBF675; product behavior is unchanged. This is local correction evidence, not GitHub Hassfest success or latest-head all-CI acceptance. After the combined correction/status commit is pushed, verify all applicable GitHub CI on that actual published head; no future commit SHA or result is asserted. Merge/release remain unrequested. The live-HA prohibition remains binding. The private 27f91f24c89c7f74eee37c35f8fb1882c7e129ba ZIP/helper receipts are frozen historical preparation artifacts, not current PR source after any manifest correction; do not regenerate them or prepare deployment.

**Current state — October 2, 2026 (historical checkpoint):** Stage 0 bounded research and finite policy completed and approved; exhaustive provider/carrier research remains incomplete. Stages 1, 2A, 2B, 3A, 3B and Stage 4 local integration/validation are implemented and reviewed. Local continuation and acceptance/release preparation are authorized. Live carrier acceptance and eventual authorized deployment/publication remain pending.

| Checkpoint | Status / recorded commit |
| --- | --- |
| Stage 0 finite policy | Approved bounded checkpoint; historical unknowns retained |
| Stage 1 shared delivery | Complete, a8af991 |
| Stage 2A notifications | Complete, 9cc6805 |
| Stage 2B options/pipeline | Complete, 27bc7992052ed79ae774be9faab93cb3b15d88ea |
| Stage 3A trusted ingress/state | Complete, 3fd845e2271b27356640c79661e17b36b30c9c7f |
| Stage 3B native conversations | Complete, 957b7c3813b176e278a39a37da92162518558a83 |
| Stage 4 local validation/review | Complete, 94bdb9575ccfd836928b12a5b85622c753fd5f94 |
| Release handoff/carrier-trial packet | Local preparation/review complete; callback wording corrected and coordinator accepted |
| Local version selection/preparation | 0.3.0, initial prerelease intent; focused metadata checks passed; independent review/root acceptance complete |
| Live carrier trial / external execution | Pending live/deployment prerequisites and applicable publication execution |

Active worktree: C:/Users/dstro/.codex/worktrees/textbelt-assist-stage0/Textbelt; branch codex/textbelt-assist-stage0; validated product baseline 94bdb9575ccfd836928b12a5b85622c753fd5f94, recorded clean before this documentation refresh. Current verified candidate HEAD is 27f91f24c89c7f74eee37c35f8fb1882c7e129ba; the 0.3.0 version-only manifest and candidate documentation are committed there. Behavioral product baseline remains 94bdb9575ccfd836928b12a5b85622c753fd5f94. Documentation HEAD at the prior scope correction was eff2661c475b28a0c22ea753f713fa5e9eab0ec2; verified PR head is now cbb22ab74166b3308ba231277197bb56d84de03c; preserve source/archive pin 27f91f24c89c7f74eee37c35f8fb1882c7e129ba. Verify actual HEAD on resume; no future SHA is asserted. Preserve original checkout on hacs-versioning. Historical commits 857f12b/f379e37/1b9a42e retain Stage 0 corpus, observations and receipt copies. Verify branch/HEAD/status on resume. Old attached ZIP/stage0.patch is obsolete: never reapply. Off-machine continuation needs the full current branch. Preserve uploaded attachment and .handoff-stage0/original-plan.md.

Read worktree docs/research/{stage1-local-validation,stage2a-local-validation,stage4-local-validation,stage0-carrier-results,stage0-boundary-results,provider-source-research,textbelt-provider-contract}.md and .superpowers/sdd/textbelt-native-assist-handoff/{final-review,progress}.md. Ledger is append-only; later entries supersede old state.

Most recent recorded verification (prior turn; not rerun for this documentation edit): 448 passed in 36.33 seconds, 93.29% coverage; Ruff clean, 62 files formatted, bash syntax clean. Actual HA 2026.8.2 local-stub run 5 exited 0 with 25 verdicts and nine exact INTENT-only traces. Migration, retained/isolated context, preferred pipeline changes, partial/unknown outcomes, restart/no replay, cleanup and metadata were verified locally. No satellite validation. Published v0.2.0 remains unchanged. Root selected local candidate 0.3.0 with initial prerelease intent; manifest version-only, release-copy preparation and acceptance reconciliation independently reviewed and accepted by root. Review: `.superpowers/sdd/textbelt-native-assist-handoff/completion-metadata-review.md`; the sole P3 historical reference-label finding was corrected/frozen in the acceptance matrix (evidence SHA256 650DFCB5CCD350F69EBBD352D8501C3422890BAA718C8C8ADDA539009CDFF89C). Release owner records 12 existing release-contract tests passed in 0.80 seconds; no publication/deployment or full-suite/smoke rerun for metadata.
Fresh compatibility evidence: coordinator ran the actual offline local-stub matrix against official Home Assistant 2026.9.4 on October 2, exit 0, 25 recorded checks (23 distinct labels) and nine exact INTENT-only traces. The optional HA_SMOKE_IMAGE seam preserves default 2026.8.2. This is a fresh smoke run, not a rerun of the 448-test suite. See `docs/research/native-assist-ha-compatibility.md`, `.superpowers/sdd/textbelt-native-assist-handoff/coordinator-ha-2026.9.4-result.md` and `.superpowers/sdd/textbelt-native-assist-handoff/compatibility-artifact-proof.txt`.

Recorded compatibility artifacts: /home/drew/.cache/textbelt-oct2-smoke/tmp/textbelt-ha-artifacts-hnKEta; log /home/drew/.cache/textbelt-oct2-smoke/coordinator-ha-2026.9.4-run-1.log. Resolved official image ghcr.io/home-assistant/home-assistant:2026.9.4, RepoDigest sha256:3e6710a7ab2a61311d9d899b719f6c3657791c63e8f4942cec4ebc42401d6b76. Metadata/partial/unknown/migration/restart and cleanup proof passed; expected stopping-stage metadata_not_durable warnings do not prove synchronous final writes.

Read-only user-HA readiness at October 2, 18:42:03 UTC: Core 2026.9.4 RUNNING; textbelt_sms.send_sms registered, start_conversation absent; preferred ChatGPT Brina Assistant observed and preserved. Candidate revision/provenance, public callback reachability and live delivery are unverified. Offline compatibility does not authorize or prove deployment.

**Verified status — October 2, 2026, after 22:20 UTC:** Local candidate metadata/docs are committed at 27f91f24c89c7f74eee37c35f8fb1882c7e129ba; source behavior remains the validated 94bdb9575ccfd836928b12a5b85622c753fd5f94 baseline. The existing 12 metadata contract tests passed in 0.80 seconds and independent metadata review accepted the candidate. No full-suite or smoke repeat accompanied this status refresh.

The private completion-candidate.zip is 36,049 bytes, SHA256 a815ef290f65df0596c5e4c9495b8e2bc35198361ce6a523e8f5f5d2a01558d1, pinned to the full candidate SHA above. All 18 source files match Git bytes/hashes; packaged manifest is textbelt_sms/0.3.0. Receipt: `.superpowers/sdd/textbelt-native-assist-handoff/completion-candidate-receipt.json`. The private completion-deploy-helper.py is frozen at SHA256 d45667d0da4df5774b7bb668ace74ecab76f5c3562a888db2b24a6790e83cb3d: 16 isolated helper checks and independent review passed; installation uses atomic exchange only. The supported response-only transport filter passed ten local fixtures and independent review, but is not remotely verified. One remote read-only check-only attempt reached the 50 KiB reflected-command response cap: execution result UNKNOWN, not PASS. No install-mode command was sent; whether the check-only helper executed is UNKNOWN.

One supported HA snapshot completed successfully in 186 seconds: backup 018a1373, created 2026-10-02T17:19:59.962298-04:00, 2,645,166,080 bytes. Independent supported list readback verified homeassistant_included:true, homeassistant_version:2026.9.4, protected:true, database_included:false, agent_ids:[hassio.local]. Recovery-key/emergency-kit availability confirmation remains unanswered; no key was read/downloaded and no restore/delete occurred. Completion and coverage are verified; usability and freshness remain installation gates. The helper requires completion age at most one hour, so this recorded backup must not be assumed freshness-qualified on resume.

HA access remains unavailable after the earlier successful backup readback. At 22:09:33 UTC the configured MCP upstream and native read-only TCP probes were refused; the public HA browser fallback closed its connection. The secondary HA port was not baseline-proven, so these observations do not establish Core downtime or backup causality. Bounded recovery identity diagnosis found no supported direct SSH route to the exact target and stopped without service commands or changes; no verified MCP service identity or precise safe recovery action is available. This is historical connection evidence; the binding October 3 scope prohibits further live-HA attempts as part of this work even if connection state changes.

No candidate install, HA restart/native opt-in, paid or _test SMS, carrier/satellite acceptance, push/PR/merge/release/publication occurred. Published v0.2.0 remains unchanged. The user-designated phone, existing authorized key mechanism and NEW explicit numeric credit/send cap remain unanswered; the original 33-credit budget is closed and Continue authorizes continued implementation but does not provide the missing live-trial inputs or numeric budget. The earlier recovery-key availability question is superseded for current local work and does not need an answer. The accepted remaining-acceptance matrix preserves the six bounded Stage 0 closures and original UNKNOWN/partial research requirements.

Stage 0: 6 _test controls, zero debit; 7 grouped GSM paid messages / 7 credits; 15 boundary paid messages / 21 credits. Total 22 paid POSTs / 28 credits of 33 cap, at most $1.68 using supplied maximum $0.06/credit, 5 unused buffer credits. Last observed quota 321 is not current. No further sends planned; no budget reset. DPAPI mechanism: $env:TEMP/textbelt-stage0-key.clixml; do not read/copy secret or raw recipient. Preserve private .handoff-stage0/*results*.json journals.

Approved policy docs/research/probes/v2-character-policy-approved.json: 124 characters (115 default + 9 extension), 160 septets/part, max 5 parts, all integration defaults. Excluded 10 Greek, currency sign, CR, FF. G1 Greek/currency became ?; G2-G5 exact LF; G6 CR copied LF; G7 FF copied CR, possible clipboard normalization. Group coverage does not prove each character exact in arbitrary contexts. Copies A160, A161, ^80, ^81, A306 exact; 10 other executed boundary copies unknown; A307/BMP134/135 unrun. Actual provider maximum unknown: 306 accepted ASCII is lower bound only. Reply window, stable inbound IDs, callback retry/ack, HELP, idempotency remain unknown. MMS investigation closed by user; no satellite tests. Preserve original 177-row corpus and historical proposals unchanged; approved finite policy supersedes proposals.

Stage 0 unchecked checklist items below denote partial/skipped/unknown original requirements, not authorization for further paid research. The bounded checkpoint was approved without claiming exhaustive completion. Current matrix: `docs/research/native-assist-remaining-acceptance.md`. Source-reading, conservative test disposition and corpus-generation closures are evidence-backed; checked raw/formatter/grouped-policy rows now explicitly cover approved bounded scope. Historical exhaustive/unknown-bearing requirements remain deferred/partial; extra non-GSM Unicode is not activated.

## 1. User goal

Make SMS conversations with Home Assistant Assist native to this custom integration. The user previously routed SMS through HA scripts and automations to an OpenAI-backed Assist setup and received responses over SMS, including through T-Mobile/Starlink in remote locations. Users should no longer have to create that routing themselves.

Build four separate capabilities:

1. Shared provider-compatible message formatting, splitting, and delivery.
2. Standard Home Assistant notification targets for automation alerts.
3. An option to select an Assist pipeline, defaulting to HA's current preferred pipeline.
4. Native incoming SMS conversations with Assist, maintaining separate context per sender and returning responses through SMS.

Original workflows in https://github.com/stroodle96/Edinboro-Home-HA could not be located. The user explicitly waived their discovery. Do not spend further work searching for them or make their availability a prerequisite; implement the behavior described here.

## 2. Execution instructions

- Inspect the current repository, AGENTS.md, contribution instructions, and current CI before editing. Refresh any findings that have changed since the reference commit below.
- Stage 0 covers provider research and controlled test preparation/execution; keep product implementation separate.
- At each stage checkpoint, provide the changes/artifacts, actual verification results, limitations, and the proposed next stage. Wait for approval before the next implementation stage. Preserve approvals already supplied; do not ask again for an already authorized action.
- Live SMS requires a configured key, a user-designated test destination, and an explicit credit/send budget. Historical planning lacked these; Stage 0 subsequently used an authorized mechanism and bounded budget. No further sends are planned. Do not invent credentials or retrieve secrets from unrelated files/email.
- Prefer a verified non-delivery Textbelt test mode for the exhaustive API sweep. Establish its actual behavior before bulk requests.
- Keep API keys out of source, command arguments/logs, fixtures, artifacts, and shared documentation. Use the environment's authorized credential mechanism. Do not publish private Gmail correspondence.
- Do not deploy to a user's HA server, publish a release, or merge/push remotely as part of this handoff without the applicable authorization.
- If multiple agents are used, assign the feature ownership in Section 10. One integration owner controls shared entry/configuration files. Feature agents must not implement duplicate senders or conflicting setup/config-flow changes.

## 3. Verified baseline and limits of the research

Historical reference main commit: b1e7c8f1ef4c90741c8d25134fc1fe3800d76895, inspected September 30, 2026. This is not freshly fetched main; compare current upstream only when needed for an authorized integration/publication step.

Historical baseline behavior at that commit (superseded by Stage 1/2A reports and implemented interfaces below):

- custom_components/textbelt_sms/config_flow.py accepts one API key and permits one config entry.
- __init__.py registers textbelt_sms.send_sms(phone, message), a fixed reply webhook, and textbelt_sms_reply events. The incoming handler parses JSON and emits an event; it does not invoke Assist or authenticate the callback itself.
- api.py posts correctly structured form fields phone, message, key, and optionally replyWebhookUrl. The send path has no explicit integration-level timeout. Quota reads already have a ten-second timeout and disable redirects.
- sensor.py exposes remaining credits and last-message delivery status. Delivery tracking follows the latest text ID, not a whole multipart batch.
- There is no notify platform, options flow, pipeline selection, conversation manager, sanitizer, or splitter.
- README/tests pin Home Assistant 2026.8.2 and include pytest-homeassistant-custom-component plus a deterministic Textbelt stub and real-HA smoke flow.
- HA 2026.8.2 supports AssistPipelineSelector and PipelineRun/PipelineInput. async_get_pipeline(hass, None) resolves the preferred pipeline. Running INTENT through INTENT accepts text without STT/TTS and preserves pipeline configuration such as language and prefer_local_intents.
- HA 2026.8.2 provides NotifyEntity, NotifyEntityFeature.TITLE, and the standard notify.send_message action.

Historical support evidence, already researched:

Textbelt support's Ian replied on May 26, 2025 to the user's Issues with mutiline messages thread:

> To send a multiline text, you need to include a special \n (newline) character to indicate the new line. Your system will need to be able to produce this character.

The complete five-message April–May 2025 thread contains no numeric length limit, bullet restriction, or complete character allowlist. It describes HTTP 400 from an older HA REST command but supplies no request body or provider error detail. Incorrect serialization is a possible explanation, not a verified diagnosis. The email's backslash-n notation does not establish a literal-backslash wire protocol.

Public clients corroborate a candidate Textbelt test mode: append _test to the API key on the normal /text endpoint. One client describes it as not sending SMS and useful for key validation. This was the original planning uncertainty. Subsequent Stage 0 controls observed zero debit and missing/empty rejection, while invalid-phone success and length/Unicode acceptance leave production validation relevance unestablished; see stage0-test-mode-results.md. Rate limits and exhaustive carrier behavior remain unverified.

Direct reads of the public Textbelt site and ETSI PDFs were blocked by the previous environment's unreachable shell proxy. GitHub connector reads worked. That limitation applies only to the earlier reconstruction session. Subsequent Stage 0 retrieved primary documentation and ran the bounded probes recorded in provider-source-research.md and the Stage 0 results. The official typpo/textbelt open-source project describes an older email-gateway service; its behavior is not authoritative for the paid Textbelt API.

## 4. Telecom standards: constraints, not a universal provider allowlist

Use 3GPP TS 23.038 / ETSI TS 123 038 for character encodings and TS 23.040 / ETSI TS 123 040 for SMS transport and user-data/header constraints.

| Encoding/topic | Relevant behavior |
| --- | --- |
| GSM-7 default alphabet | A defined table of letters, digits, punctuation, and selected accented/currency/Greek characters; most default-table characters use one septet. |
| LF/CR | Both are in GSM-7. They are not universally illegal SMS characters. CRLF uses two septets. |
| GSM-7 extension characters | Caret, braces, backslash, square brackets, tilde, vertical bar, euro, and defined controls such as form feed require an escape and normally use two septets. |
| ASCII versus GSM-7 | Different sets: backtick is ASCII but not default GSM-7; pound/e-acute/a-umlaut are GSM-7 but not ASCII. |
| Bullets/smart quotes/long dashes | Outside default GSM-7; require another encoding or deliberate substitutions. Do not label them universally prohibited in SMS. |
| Unicode | The 16-bit SMS encoding is commonly called UCS-2; many modern gateways support UTF-16 surrogate pairs. Non-BMP emoji require explicit provider/carrier verification. |
| Single segment | Up to 140 user-data octets without header overhead: 160 GSM-7 septets or 70 16-bit code units. |
| Concatenated segments | A common six-octet header leaves 153 GSM-7 septets or 67 16-bit units per segment. Other headers can reduce these values. |

These are telecom capacities, not verified Textbelt API maximums or credit rules. One Unicode character may switch the entire message encoding. Count encoding units, not Python len or visible glyphs. Emoji/combined glyphs can occupy several UTF-16 units. Do not split surrogate pairs or grapheme sequences if a verified Unicode policy is supported.

## 5. Stage 0: establish the provider contract and test every allowed character

**Deliverables:** docs/research/textbelt-provider-contract.md; a reproducible character/length probe harness; versioned probe inputs/results; a finite production allowlist with evidence for each character; finalized ProviderPolicy decisions. Stage 0 historically kept product files unchanged; this research corpus is now frozen.

### 0A. Read and record current provider rules

- [x] Read and refresh official Textbelt send/reply/test/quota/status/failure documentation September 30 and October 2; dated extracts/values/URLs in provider-source-research.md and native-assist-remaining-acceptance.md. Documented facts are separate from unresolved general provider guarantees.
- [ ] Verify send fields/content type, accepted phone formats, errors, response schema, API maximum message length, encoding support, automatic splitting, and credit costs.
- [ ] Verify reply initiation, supported countries/accounts, reply lifetime, payload fields, callback signing/canonicalization/timestamps, acknowledgments/retries, and stable inbound IDs.
- [ ] Verify delivery-state vocabulary/retention, polling/rate limits, opt-outs/STOP/HELP, and any POST idempotency mechanism. Do not invent missing signing details.

### 0B. Verify candidate test mode before relying on it

- [ ] Confirm the official _test instructions, whether /text is the correct endpoint, no delivery/credit deduction, and test-mode rate limits. The public key named textbelt is not automatically a non-delivery sandbox; it may send a limited-quota real SMS.
- [ ] Use positive and negative controls to identify validations actually performed: a valid request, malformed/missing message, documented over-limit input, and relevant unsupported-content probes.
- [x] Preserve production character/length validation as unverified where test-path relevance is unestablished; do not infer carrier/content acceptance from _test successes. Six control observations remain bounded, without asserting every validator bypassed.
- [ ] Use verified non-delivery mode for exhaustive API testing where it exercises the relevant validation. Live carrier behavior must be tested separately within the supplied budget.

### 0C. Exhaustive finite character sweep

- [x] Generate and independently review the frozen GSM/default/extension/control and diagnostic corpus against pinned primary tables; raw ESC/reserved entries are diagnostics, not prose. Corpus generation is not execution evidence.
- [ ] For every character, submit raw A + character + B with the intended actual code point and correct form serialization. Stable markers distinguish whitespace from an empty-message rejection.
- [ ] Historical extra-Unicode requirement is not applicable to approved finite GSM-only production policy; no non-GSM expansion activated. Any future expansion requires its own individual reviewed evidence. Diagnostic samples do not establish Unicode-policy acceptance.
- [ ] Also probe actual LF, CR, CRLF, literal backslash plus n, tab, backtick, bullets, smart punctuation, non-Latin scripts, emoji/skin-tone/ZWJ sequences, precomposed/decomposed accents, NBSP, zero-width space, Unicode line separator, and request-escaping characters such as quotes, ampersand, plus, percent, equals, and backslash.
- [x] Execute recorded bounded raw-provider groups/boundaries before sanitization; separately validate approved formatter output locally. The original exhaustive raw corpus remains unrun.
- [x] Preserve grouped live/copy position evidence for every permitted v2 character in the single authorized account/US-T-Mobile trial; exclude observed substitutions and ambiguous controls. This satisfies approved finite scope, without individual/arbitrary-context fidelity or satellite claims.

### 0D. Length and interaction probes

Do not prepend labels to exact-length payloads. The following boundaries are test hypotheses based on common telecom capacities:

| Payload | Raw test lengths |
| --- | --- |
| Repeated A | 159, 160, 161, 306, 307 characters |
| Repeated caret | 79, 80, 81 characters: 158/160/162 GSM septets |
| Repeated CJK BMP character | 69, 70, 71, 134, 135 16-bit units |
| Repeated grinning-face emoji | 34, 35, 36 glyphs: 68/70/72 UTF-16 units if supported |
| Mixed Unicode boundary | 69 A characters plus one bullet; 70 A characters plus one bullet |
| Actual provider maximum | Documented maximum minus one, at maximum, and plus one; only after that limit is known |

- [ ] Test whole-message encoding switches, line-break variants, normalization, extension weights, and group/context interactions.
- [ ] Distinguish provider-managed concatenation from integration-managed independent texts with visible (1/N) labels. Record actual credit usage and delivery/ordering behavior before choosing a production method.

### 0E. Evidence and checkpoint

For each probe, record exact code points, UTF-8 bytes, GSM eligibility/septet cost, UTF-16 units, serialized request type, HTTP status, sanitized response/error, text ID, quota change, status timeline, received text, transformation/segmentation, date, account/country/carrier scope, and verification mode.

Keep three verdicts separate: API accepted/rejected/unknown; carrier delivered/failed/unconfirmed; received text exact/converted/truncated/unknown. success:true is not delivery proof. Do not retry an uncertain POST automatically.

- [x] Freeze approved v2 124-character policy with group/position API/provider-delivery/user-copy evidence and exclusions. Unknown/rejected characters stay outside default; Unicode expansion and universal carrier guarantees remain unsupported.
- [ ] Define exact ProviderPolicy values: allowed characters, weights/encoding, provider request limits, per-part budget, reply window/countries, and integration part cap. Clearly distinguish measured/documented provider rules from integration defaults.
- [x] Present bounded report, examples, credit usage, uncertainties, and revised decisions. User approved the finite policy and Stage 1; exhaustive research remains incomplete as specified above.

## 6. Stage 1 / Agent A: shared preparation and delivery

**Own:** custom_components/textbelt_sms/models.py, message.py, sender.py, api.py; tests/test_message.py, test_sender.py, test_api.py; required multi-ID sensor changes and focused sensor tests. The integration owner wires the service in __init__.py.

Required behavior:

- Normalize Assist markup/list output to readable text. Default compact one-line output is a presentation choice, not a provider newline ban. Preserve permitted GSM characters rather than deleting all non-ASCII text.
- Use approved mappings for bullets, smart punctuation, markup/SSML/HTML, and unsupported symbols. Preserve negatives, decimal readings, units, URL query values, and meaningful content. Unsupported meaningful text must be preserved through verified encoding or visibly rejected/fall back, never silently disappear.
- Count encoding units after normalization. Split on sentence/word boundaries where possible, handle long tokens, account for part labels, and recalculate two-digit part-count labels correctly.
- Implemented integration cap: five outgoing parts. Oversized automation messages fail before sending; oversized Assist replies shorten with Response shortened. inside the final budget. Empty messages never produce a POST; empty Assist output gets a safe fallback.
- Revalidate every completed part against the allowlist and encoding budget after titles, labels, truncation notices, greetings, and fallback copy are added. No unsupported character reaches the client.
- Serialize batches to avoid interleaving; preserve each accepted part ID. Stop further parts after rejection or ambiguous outcomes. Retain quota refresh and last-message sensor identities; never report the entire batch delivered from its final part alone.
- Implemented integration timeouts: send 20 seconds, status read ten seconds. Disable redirects on key-bearing sends. Keep the existing API-base-URL test override.
- Do not retry uncertain sends automatically. Use POST retries only if documented idempotency supports them safely. Do not repeat an Assist action because its response SMS failed.

Tests must parameterize every allowed character from Stage 0's evidence, include unsupported/control inputs, and assert validity of all generated copy. Also cover exact segmentation boundaries, partial/rejected/unknown sends, malformed responses, auth errors, correctly encoded LF versus literal backslash-n, quota failure independence, cancellation, and per-part status.

- [x] Write focused failing tests, run them, implement the module behavior, and rerun the tests.
- [x] Have the owner connect textbelt_sms.send_sms to the shared sender and visible HA action errors. Preserve documented legacy phone formats; require unambiguous international numbers for new configured destinations/authorization without guessing a country.
- [x] Demonstrate preparation examples and failure results; Stage 1 checkpoint reviewed; Stage 2A continuation approved.

## 7. Stage 2A / Agent B: standard notification targets

**Own:** custom_components/textbelt_sms/notify.py and tests/test_notify.py. Owner integrates recipient options and Platform.NOTIFY.

- [x] Use NotifyEntity and TITLE support; create one stable entity per configured recipient. Normalize/deduplicate destinations and derive stable unique IDs without putting raw phone numbers into entity IDs.
- [x] Expose the standard notify.send_message action targeting these entities. Format optional title and message together through the shared sender. Keep textbelt_sms.send_sms for dynamic phone destinations. Do not add an unrequested legacy service alias.
- [x] Notifications remain usable with Assist disabled or no external callback. Notification recipients do not automatically gain Assist authorization.
- [x] Test message/title handling, multiple targets, recipient removal/re-addition, reload identity, no recipients, sender errors/partial/unknown outcomes, and no false successful-notification timestamp after failure. No independent retries/formatters.
- [x] Present a working alert example and test results; Stage 2A checkpoint independently reviewed; subsequent Stages 2B–4 local work also authorized and completed.

Example, with the actual entity selected in HA's UI:

    action: notify.send_message
    target:
      entity_id: notify.textbelt_sms_remote_phone
    data:
      title: Water leak
      message: Water was detected in the utility room.

## 8. Stage 2B / Agent C: options and selected/default text pipeline

**Own:** custom_components/textbelt_sms/options.py, assist.py; tests/test_options.py, test_assist.py. Owner wires config_flow.py, translations, common constants, and config-flow tests.

Options/defaults: assist_enabled=False, pipeline_id=None, authorized Assist senders separate from notification recipients, conversation inactivity timeout 1800 seconds. Native Assist is opt-in on upgrade.

- [x] Add an AssistPipelineSelector. Unset means resolve HA's current preferred pipeline on every turn, not snapshot the preference during setup. Normalize any HA preferred-selector sentinel to None.
- [x] Validate explicit pipeline IDs and numbers. Enabling Assist needs an authorized sender and configured public HTTPS callback shape (actual reachability remains unverified); outbound-only configuration remains usable. Do not silently switch from a deleted explicitly selected pipeline.
- [x] Implement a provider-independent adapter using PipelineRun/PipelineInput and HA chat_session, INTENT through INTENT. Preserve language/local-intent behavior; do not approximate a pipeline by passing its ID as conversation.process's agent_id.
- [x] Consume only completed intent speech, with safe SSML fallback; ignore streaming fragments. No STT/TTS work or SMS sending in this adapter.
- [x] Test current preference changing between calls, explicit/deleted pipeline, session/context handling, completed/empty speech, error events, and the 60-second run timeout/cancellation.
- [x] Present selected/default behavior and tests; implemented and reviewed at Stage 2B.

Stages 2A/2B are complete. TextbeltOptionsFlow uses standard OptionsFlow and an owned policy-first reload listener; OptionsFlowWithReload was incompatible. It preserves notification recipients and other options; notification recipients do not confer Assist authorization.

## 9. Stage 3 / Agent D: trusted incoming SMS and native conversations

**Own:** custom_components/textbelt_sms/webhook.py, conversation.py, state.py; tests/test_webhook.py, test_conversation.py, test_state.py. Owner wires persisted endpoint identity, services, runtime, and lifecycle.

- [x] Generate/store a random per-entry webhook ID and register only required methods. Verify the provider's documented raw-body signature/timestamp rules before parsing or invoking Assist. Do not invent a signature scheme or enable an unsigned native home-control endpoint.
- [x] Implemented integration resource bounds: 16 KiB callback body, 4096-character inbound text, ten pending turns per sender, fifty overall. Provider capacity compatibility remains unverified.
- [x] Validate payload, normalize sender/text ID according to the verified contract, correlate with known outgoing IDs/recipients for the supported reply window, and enforce the explicit sender allowlist.
- [x] Retain authenticated valid textbelt_sms_reply events for custom routing. Explain that old SMS-to-Assist automations must be disabled before native routing to avoid two responders; support events-only mode.
- [x] Return integration-defined callback responses promptly; actual provider acknowledgment/retry compatibility remains unverified; process Assist in integration-owned background tasks. Serialize each sender's turns while allowing other senders to progress.
- [x] Keep context per (entry, normalized phone, resolved pipeline). Configured default inactivity reset: 30 minutes; /new resets explicitly. Pipeline changes, removing authorization, disabling Assist, or HA restart start fresh sessions. Do not replay queued/uncertain home-control actions after restart.
- [x] Persist bounded outgoing-ID correlation and duplicate metadata, not transcripts. Use a documented unique inbound reply ID where available. Never deduplicate by outgoing textId alone: multiple legitimate replies can share it. If no stable inbound ID exists, use the documented two-minute body/identity-digest fallback and its identical-resend ambiguity.
- [x] Send completed responses only to the verified originating sender through the shared sender with shortening enabled. Handle empty/unsupported output safely. For uncertain timeout execution, tell the user to check the result before resending; never repeat an action automatically.
- [x] Add textbelt_sms.start_conversation(phone), restricted to authorized senders, with a built-in safe greeting and provider-required reply correlation. Document whether Textbelt requires an outbound message to initiate a reply-capable thread; explain supported countries/accounts and callback access.
- [x] Respect documented STOP/HELP/opt-out behavior; do not interpret carrier opt-out commands as home-control intents.
- [x] Test signatures/replays, malformed/oversized input, unauthorized/correlated replies, multiple legitimate replies per outgoing ID, per-sender context, concurrency/queue limits, restart/reset, failures, and unload cancellation. No sends after shutdown.
- [x] Demonstrate local-stub end-to-end SMS Assist without user routing YAML; Stage 3 independently reviewed. Actual live SMS Assist remains a carrier acceptance gate.

## 10. Shared interfaces and file ownership

These implemented interfaces supersede original proposals; inspect source before changing a dependent contract:

    AssistOptions(enabled=False, pipeline_id=None, authorized_senders=(),
                  conversation_timeout=1800)
    AssistOptions.from_mapping(options) -> AssistOptions
    PreparedMessage(parts, normalized_text, shortened)
    prepare_message(message, *, title=None, mode='automation'|'assist',
                    compact=False, policy=DEFAULT_POLICY) -> PreparedMessage
    PartResult(index, text_id, outcome, error_code=None)
    SendResult(parts, total_parts, outcome, error_code=None, shortened=False)
    TextbeltSender.async_send(phone, message, *, title=None,
                             mode='automation'|'assist', compact=False,
                             webhook_url=None) -> SendResult
    TextbeltRuntimeData.async_send(hass, phone, message, *, title=None,
                                  webhook_url=None, mode='automation'|'assist',
                                  compact=False) -> None
    async_run_assist(hass, *, text, pipeline_id, conversation_id, context,
                     timeout=60) -> AssistResult
    AssistResult(pipeline_id: str | None, conversation_id: str | None,
                 reply: str, error_code: str | None, ha_session_id: str | None=None)
    VerifiedReply(entry_id, text_id, phone, text, duplicate_digest,
                  packet_digest, packet_expires_at, event_data)
    ReplyState(hass, entry_id, *, clock=...)
    ConversationManager(hass, entry, state, runtime, *, clock=...)
    ConversationManager.async_handle_reply(reply: VerifiedReply)

VerifiedReply can only be constructed through signature verification. Generated ingress requires signed, correlated callbacks; fixed legacy ingress emits signed events only. Unsigned callbacks are rejected. Notification destinations remain separate from Assist authorization. One shared sender formats/sends all paths, with no automatic retries. Runtime exposes visible HA action errors and independent quota refresh; accepted IDs and durable correlation remain observable despite response failure. Provider acceptance is separate from delivery.

The adapter uses public PipelineRun/PipelineInput INTENT through INTENT with completed speech only. Session context retains both agent conversation and HA session IDs; the public HA keepalive is 120 seconds, distinct from the configured default 30-minute inactivity policy. Queues, session context and transcripts are volatile; restart never replays home-control work.

ReplyState Store key is textbelt_sms.reply.{entry_id}, not a webhook ID. It persists bounded outgoing-ID correlation, duplicate and packet metadata only: seven-day outgoing retention, 100 IDs per sender/1000 total, two-minute identical-body fallback, bounded replay metadata. These are integration policies, not measured provider reply/retry windows. When HA is stopping, a Store snapshot may be deferred for HA's final write; this does not claim immediate durable confirmation. Existing last-message sensor attributes can be retained by Recorder and require user retention configuration.

The approved bounded policy remains 124 GSM characters, 160 septets per prepared part and at most five parts. No country guessing, cost guarantee or delivery guarantee. Preparation failures stay visible before POST; partial and unknown sends stop further parts without repeating Assist actions.
One integration owner edits __init__.py, config_flow.py, const.py, manifest.json, services.yaml, translations, migration, and entry lifecycle. Agent A owns the HTTP/sender/preparation models. Agent B owns notify entities. Agent C owns typed options/pipeline adapter. Agent D owns trusted ingress/conversations/metadata. Use isolated branches/workspaces where the execution environment supports them; do not have multiple agents editing the shared files simultaneously.

## 11. Stage 4: integration, migration, smoke tests, and docs

- [x] Preserve single-entry scope, textbelt_sms.send_sms(phone, message), existing quota/last-message sensor identities, and the supported authenticated reply-event interface.
- [x] Migrate existing entries with disabled native Assist/default options and persistent random webhook ID. Resolve authenticated compatibility for outstanding replies sent to the old fixed endpoint; never let an unsigned legacy endpoint execute Assist.
- [x] Add required HA dependencies and notify platform, typed runtime_data, successful setup/unload service ownership, and complete rollback. Test failed setup/unload, reload, in-flight cancellation, and no leaked tasks/listeners/services.
- [x] Extend tests/smoke/textbelt_stub.py, exercise_api.py, test_exercise_api.py, and run.sh for verified callback fixtures, multipart behavior, partial failure, accepted-then-disconnected sends, quota/status failures, and generated callback URLs.
- [x] Smoke-test migration, notification with Assist disabled, native thread initiation, two turns retaining context, a second sender isolated, preferred-pipeline changes, unauthorized/replayed input, restart resets, and no user routing scripts/automations.
- [x] Run appropriate current repository checks, including python -m pytest -q; python -m ruff check .; python -m ruff format --check .; bash tests/smoke/run.sh in its supported Docker environment. Inspect real output. A blocked/unrun check is not passing.
- [x] Document UI setup, notify examples, dynamic preferred-pipeline selection, thread initiation/reset, callbacks/countries/accounts, verified character/encoding policy, limits/costs, truncation, failures/unknown outcomes, opt-outs, restart context, and disabling old routing automations.
- [x] Review the complete local change against this plan and the frozen provider contract; see final-review.md and stage4-local-validation.md.
- [x] Provide local reviewable changes, test/provider evidence and limitations.
- [x] Prepare/review local `docs/research/native-assist-release-handoff.md` and `docs/research/native-assist-carrier-trial.md`; coordinator accepted after correcting generated-webhook-ID wording, distinct from config entry ID. Final spec/quality acceptance is recorded in `.superpowers/sdd/textbelt-native-assist-handoff/next-step-review.md`.
- [ ] Within new designated destination/key mechanism and explicit budget, perform minimal live T-Mobile/Starlink trial; local stubs cannot establish satellite delivery. Historical 33-credit authorization used 28 and is not renewed by generic Continue.
- [x] Select local 0.3.0 candidate with initial prerelease intent and prepare version-only manifest/release copy; owner records 12 existing release-contract tests passed in 0.80 seconds. Independent review/root acceptance complete, including the corrected P3 historical reference label; dated unused-tag observation must be refreshed before publication.
- [ ] Complete candidate deployment and applicable push/PR/merge/release execution; publication and deployment are not established. Local candidate ZIP/helper/transport preparation and reviews are complete; remote check-only execution remains UNKNOWN and HA access is unavailable. Backup completion/coverage remain historical receipts. Current validation proceeds only in disposable isolated local HA with the deterministic stub; live-HA deployment/provenance/native services/public generated callback proof is not authorized in this scope.

## 12. Acceptance criteria

The work is complete when users can configure the integration through HA's UI, send alerts through notify.send_message, and chat with their selected/default Assist pipeline via authorized SMS without routing automations or scripts. All outgoing parts pass the approved finite character/encoding policy with bounded grouped coverage, without claiming individual arbitrary-context carrier proof; long messages obey the reviewed budget/cap, and failures/unknown outcomes remain visible without duplicate sends/actions. Existing outbound service and sensor behavior survives migration. Authentication, isolated context, lifecycle, and deterministic smoke checks pass; carrier claims are limited to actual trial evidence.

## 13. Public references for the delegated agent

- Integration reference tree: https://github.com/stroodle96/textbelt-sms/tree/b1e7c8f1ef4c90741c8d25134fc1fe3800d76895
- Provider docs: https://docs.textbelt.com/ ; https://docs.textbelt.com/sms-replies ; https://docs.textbelt.com/other-api-endpoints — verify current canonical pages.
- Standards: https://www.3gpp.org/dynareport/23038.htm ; https://www.3gpp.org/dynareport/23040.htm
- HA pipeline source: https://github.com/home-assistant/core/blob/2026.8.2/homeassistant/components/assist_pipeline/pipeline.py
- HA exports: https://github.com/home-assistant/core/blob/2026.8.2/homeassistant/components/assist_pipeline/__init__.py
- HA selector: https://github.com/home-assistant/core/blob/2026.8.2/homeassistant/helpers/selector.py
- HA notify: https://github.com/home-assistant/core/blob/2026.8.2/homeassistant/components/notify/__init__.py
- HA webhook: https://github.com/home-assistant/core/blob/2026.8.2/homeassistant/components/webhook/__init__.py
- Corroborating GSM table: https://github.com/warthog618/sms/blob/5a8659af51a664ddd4f9a7e6ffd253b54e79e21e/encoding/gsm7/charset/default.go
- Corroborating UTF-16 implementation: https://github.com/warthog618/sms/blob/5a8659af51a664ddd4f9a7e6ffd253b54e79e21e/encoding/ucs2/ucs2.go
- Candidate test-mode client: https://github.com/knorquist/python_textbelt/blob/94a0e5b09075e0883c2bfaad98dd5177fd6a1d63/src/python_textbelt/textbelt.py
- Candidate test-mode gateway: https://github.com/informatici/openhospital-core/blob/4da5b2c9b11a02f638efac2632c936c7adcd0cb5/src/main/java/org/isf/sms/providers/textbelt/TextbeltGatewayService.java

This document contains the necessary planning context without requiring access to the original chat or private mailbox.

## 14. Exact resume procedure

Read this full plan, approved policy, Stage 4 evidence, final-review.md and append-only progress.md. Verify active worktree branch/HEAD/status and repository guidance; preserve all historical originals, uploaded attachment and hacs-versioning checkout. Lead remains coordinator, with user-requested GPT-6.1 Sol low-reasoning subagents and shared-file ownership. Do not reopen completed Stages 2B–4 local work or request their approval again.

Local release handoff/carrier-trial packet preparation and review are complete and accepted by the coordinator. Read them with native-assist-ha-compatibility.md and the coordinator 2026.9.4 result/proof; read the recorded final spec/quality acceptance in `.superpowers/sdd/textbelt-native-assist-handoff/next-step-review.md`. The actual 2026.9.4 offline smoke passed. The earlier read-only readiness observation recorded start_conversation absent; it is historical and must not be treated as current while HA access is unavailable. Resume local development/acceptance reconciliation using disposable isolated HA and the deterministic stub; live-HA access and recovery-key availability are not prerequisites for current work. Preserve the preferred ChatGPT Brina Assistant pipeline. Prepare only authorized local acceptance/release materials. Before any live send require a user-designated destination, authorized key mechanism and new explicit credit/send cap; do not read historical secrets or reuse the five-credit buffer. Actual HTTPS reachability, provider acknowledgment/retry/capacity compatibility, live reply lifecycle and T-Mobile/Starlink delivery remain acceptance dependencies. Record three separate API/carrier/received-text verdicts and stop on ambiguous POSTs. Follow the already-open PR #104 CI and fix actual failures locally under the latest explicit user authorization; verify the latest published head, with no user-HA prerequisite. Merge/release still require separate authorization; local 0.3.0 version-only/release-copy preparation and acceptance reconciliation are independently reviewed and root accepted, while published v0.2.0 is unchanged. Read `docs/research/native-assist-remaining-acceptance.md` and completion-release-report.md. Use the frozen completion-candidate receipt, helper review and transport-v2 report; do not regenerate or substitute the ZIP/helper or treat the capped remote check-only attempt as success. These are frozen historical preparation artifacts, not a live-HA resume path. Do not recover/probe/connect to, back up, run the check-only helper on, install on, restart or enable native Assist on the user live HA for this work. Continue only local acceptance/release documentation and any independently justified future development validation in disposable isolated HA with the deterministic stub; Run the final local suite and required checks for the explicitly requested PR; reuse completed smoke/helper/filter evidence unless code changes, failures or CI requirements justify repeating it. The old live-HA access/recovery-key questions need no answer. Future live-provider/carrier acceptance and publication execution remain pending and require their separate inputs/authority; no success or waiver is inferred. Pending phone/key mechanism/new numeric paid exposure questions remain unanswered; historical 33-credit allowance stays closed.
Recorded validation environment: WSL Ubuntu CPython 3.14.2; /home/drew/.cache/textbelt-stage0-validation/bin/python; Linux repo /mnt/c/Users/dstro/.codex/worktrees/textbelt-assist-stage0/Textbelt. Full checks: python -m pytest -q; python -m ruff check .; python -m ruff format --check .; focused pytest --no-cov. Recorded Stage 4 local smoke: TMPDIR=/home/drew/.cache/textbelt-local-validation/tmp LIVE_SMOKE=0 bash tests/smoke/run.sh; see stage4-local-validation.md for the controlled environment and full commands. WSL/worktree writes need require_escalated. No implementation tests rerun for this documentation edit.
