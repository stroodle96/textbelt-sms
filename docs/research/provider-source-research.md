# Current primary-source Textbelt research

Retrieved 2026-09-30 using web retrieval. Scope: Stage 0A/0B documentation only. No provider API
calls, credentials, SMS, quota spending, or product changes. This supersedes the access
limitation in the bundled research for the pages below; it supplies documentation evidence, not
measured acceptance or delivery.

## Send, test, and replies

Source: https://docs.textbelt.com/ (Getting started; Response; Testing this API; Receiving SMS
replies; Verifying the webhook; Including custom data).

- POST `https://textbelt.com/text`: required `phone`, `message`, `key`; optional `sender`, `replyWebhookUrl`, `webhookData`. Examples support URL-encoded forms and JSON.
- Response: boolean `success`, `quotaRemaining`, successful `textId`, failed `error`. Examples include `Out of quota` and `Incomplete request`; no complete HTTP/error-code taxonomy.
- Append `_test` to the key on `/text`: documented key validation and no credit deduction; conditional wording implies no delivery but does not explicitly guarantee it. Content/length-validation scope and test-specific throttling remain unspecified.
- Replies: U.S. numbers only; unavailable with free `textbelt` key. Start through outbound SMS with `replyWebhookUrl`. JSON POST fields: original conversation `textId`, `fromNumber`, `text`; optional `data` echoes `webhookData` (maximum 100 characters).
- `X-textbelt-signature`: hexadecimal HMAC-SHA256 keyed by API key, over timestamp string concatenated directly with raw JSON payload. Python example UTF-8 encodes key and concatenation; compare safely. `X-textbelt-timestamp`: UNIX seconds; reject more than 15 minutes old. Never reserialize JSON for verification.
- No documented unique inbound reply ID, reply lifetime, acknowledgment requirements, retry schedule, or future-clock bound in this page.

## Formats, encoding, length, billing, and rate

Source: https://docs.textbelt.com/faq/sending-and-receiving-messages (phone formats; countries;
rate limiting; long texts; quota).

- E.164 preferred; U.S./Canada accept ten digits and formatted strings. Encode `+` in form data. Outbound coverage stated as 221 countries; no exhaustive country/account matrix provided here. Shared sending-number pool; stable number attempted when possible, not guaranteed.
- Advice: at most 1–2 SMS/second; no strict API cutoff promised, but exceeding advice can harm carrier delivery. Multiple recipients/messages require multiple requests.
- Long-text paragraph describes automatic segmentation up to a length stated as 256 bytes, with carrier-dependent segment length usually 120, delivered as multiple texts. This is not an unambiguous current hard request limit or byte-count definition.
- Separate paragraph gives SMS capacity 140 bytes, 160 GSM-7 characters or potentially 70 Unicode characters. These are segment capacities, not a demonstrated request maximum.
- Quota counts carrier SMS segments. Failed delivery still consumes quota; refunds are not automatic. Exact extension-character, surrogate-pair, concatenation-header, and appended-text charging remain unmeasured.

## Status and quota

Source: https://docs.textbelt.com/other-api-endpoints.

- GET `/status/:textId`: JSON `status`; documented states `DELIVERED`, `SENT`, `SENDING`, `FAILED`, `UNKNOWN`. `DELIVERED` means carrier confirmation, whose semantics differ by carrier; it is not proof of exact handset text. `SENT` may lack confirmation; `SENDING` is queued/dispatched; `FAILED` is not received; `UNKNOWN` indeterminate.
- Status available up to one week after sending. No polling cadence or status rate limit specified.
- GET `/quota/:key`: `success` plus `quotaRemaining`. Avoid logging key-bearing URLs.

## Content/account restrictions and opt-outs

Sources: https://docs.textbelt.com/compliance ;
https://docs.textbelt.com/faq/textbelt-platform-and-policies ;
https://docs.textbelt.com/faq/troubleshooting.

- Compliance: every conversation includes sender identification. First-contact messages may automatically gain sender name if absent. `sender` does not change the originating phone number. First-contact opt-out instructions automatically appended unless STOP already appears; follow-up suppression described. These transformations must be measured before choosing request budgets.
- STOP opt-out handled automatically. Recipient must reply START to opt back in; sender cannot force opt-in. HELP handling, whether STOP/START also reach callbacks, and rejected-destination response schema unspecified.
- Platform policy: recipient consent required; spam/harassment/illegal messages prohibited. URLs require account whitelist permission. New-account phone/content records may be retained for 60 days. Quota purchased after April 14, 2017 expires after 365 days without key usage.
- Troubleshooting says VOIP destinations unsupported. No finite character allowlist, Unicode normalization guarantee, non-BMP guarantee, or POST idempotency mechanism found in retrieved pages. Preserve these as unknown, not unsupported-character conclusions.

## Primary telecom standards

The corpus is independently reviewed against matching pinned Release 18 editions in
[gsm-standards-review.md](gsm-standards-review.md). The editions below are additional
corroboration, not the corpus pins.

- https://www.etsi.org/deliver/etsi_ts/123000_123099/123038/19.00.00_60/ts_123038v190000p.pdf — ETSI TS 123 038 V19.0.0 (2025-10), sections 6.2.1 and 6.2.1.1, printed pages 20–22. Default GSM alphabet contains LF and CR; each default symbol uses a septet. Extension symbols use escape plus symbol: caret, braces, backslash, brackets, tilde, vertical bar, euro, and page break/form feed. Raw ESC and reserved extension entries are protocol cases, not ordinary output characters. National language tables are separate and must not silently enter the default table.
- https://etsi.org/deliver/etsi_ts/123000_123099/123040/16.00.00_60/ts_123040v160000p.pdf — ETSI TS 123 040 V16.0.0 (2020-07), section 9.2.3.24, printed pages 73–76: user-data headers consume user-data capacity, apply to 7-bit, 8-bit, and UCS2 data, and include concatenation mechanisms. Common six-octet-header arithmetic yields 153 septets or 67 16-bit units from 140 octets. This arithmetic is a transport hypothesis, not verified Textbelt segmentation. Actual header, encoding and carrier behavior remain unknown.

## Controlled next checks and stage gates

1. Obtain only the user-authorized key mechanism, designated recipient, and explicit
request/send/credit budget. No credentials were discovered here. 2. Before sweeping, run `_test`
positive control and missing/empty message, invalid phone, clearly excessive content, and
unsupported-content negative controls. Record sanitized HTTP/body results. Treat 255/256/257
UTF-8 bytes as exploratory boundaries, not a confirmed API-max control. A bypassed validator
proves nothing about content. 3. Seek provider clarification of byte definition/current hard
max, `_test` validation path, reply lifetime/inbound IDs/retries/acknowledgment, HELP/callback
opt-out behavior, polling limits and idempotency. Documentation absence does not prove
nonexistence. 4. Run the plan's raw finite character/length sweep only after establishing
relevant test-mode validation. Keep API acceptance, carrier outcome and received-text fidelity
separate. Include URLs only with confirmed account whitelist capability. 5. Carrier trial must
measure every proposed output character, appended sender/STOP text, segment credit deltas,
ordering, exact received text and reply correlations within approved budget. No uncertain POST
retry. 6. Offline signature fixtures can now use the documented canonicalization; actual signed
callback remains a separate check. Do not freeze production allowlist/ProviderPolicy or advance
to Stage 1 from documentation alone.

Unavailable targets: `https://docs.textbelt.com/sms-replies` and `/llms.txt` did not retrieve
through this tool. The root page itself contains the reply/signature specification. No
replies-window value was located.
