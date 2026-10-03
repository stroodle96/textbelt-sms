

## What?

This repository contains multiple files, here is a overview:

File | Purpose | Documentation
-- | -- | --
`.devcontainer.json` | Used for development/testing with Visual Studio Code. | [Documentation](https://code.visualstudio.com/docs/remote/containers)
`.github/ISSUE_TEMPLATE/*.yml` | Templates for the issue tracker | [Documentation](https://help.github.com/en/github/building-a-strong-community/configuring-issue-templates-for-your-repository)
`custom_components/textbelt_sms/*` | Integration files, this is where everything happens. | [Documentation](https://developers.home-assistant.io/docs/creating_component_index)
`CONTRIBUTING.md` | Guidelines on how to contribute. | [Documentation](https://help.github.com/en/github/building-a-strong-community/setting-guidelines-for-repository-contributors)
`LICENSE` | The license file for the project. | [Documentation](https://help.github.com/en/github/creating-cloning-and-archiving-repositories/licensing-a-repository)
`README.md` | The file you are reading now, should contain info about the integration, installation and configuration instructions. | [Documentation](https://help.github.com/en/github/writing-on-github/basic-writing-and-formatting-syntax)
`requirements.txt` | Python packages used for development/lint/testing this integration. | [Documentation](https://pip.pypa.io/en/stable/user_guide/#requirements-files)

## How?

1. Create a new repository in GitHub, using this repository as a template by clicking the "Use this template" button in the GitHub UI.
1. Open your new repository in Visual Studio Code devcontainer (Preferably with the "`Dev Containers: Clone Repository in Named Container Volume...`" option).
1. Rename all instances of `textbelt_sms` to `<your_integration_domain>` (e.g. `awesome_integration`).
1. Rename all instances of the `Integration Blueprint` to `<Your Integration Name>` (e.g. `Awesome Integration`).
1. Run the `scripts/develop` to start HA and test out your new integration.

## Next steps

These are some next steps you may want to look into:
- Add tests to your integration, [`pytest-homeassistant-custom-component`](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component) can help you get started.
- Add brand images (logo/icon) to https://github.com/home-assistant/brands.
- Create your first release.
- Share your integration on the [Home Assistant Forum](https://community.home-assistant.io/).
- Submit your integration to [HACS](https://hacs.xyz/docs/publish/start).

# Textbelt SMS for Home Assistant

This custom component integrates the [Textbelt SMS API](https://textbelt.com/) into Home Assistant, allowing you to send SMS messages through your automations and scripts.

## Features

- Send SMS messages from Home Assistant
- Simple configuration through the UI
- Error handling and logging

## Installation

### HACS custom repository (recommended)

Requires **Home Assistant 2026.8.2 or newer** and **HACS 2.0.1 or newer**.

Selectable versions come from [published GitHub releases](https://github.com/stroodle96/textbelt-sms/releases).
A version bump merged into the repository becomes available as a release only after
the maintainer runs the [Release workflow](https://github.com/stroodle96/textbelt-sms/actions/workflows/release.yml).

1. Install and configure [HACS](https://www.hacs.xyz/) if it is not already available.
2. Open HACS, open the menu, and select **Custom repositories**.
3. Enter `https://github.com/stroodle96/textbelt-sms`, select **Integration**, and add the repository.
4. Open **Textbelt SMS** and select **Download**.
5. Under **Need a different version?**, choose the release to install.
6. Restart Home Assistant after installation or a version change.

#### Installing a prerelease

HACS excludes GitHub prereleases from normal update selection by default. To enable prerelease updates for Textbelt SMS:

1. Go to **Settings → Devices & services → HACS → Entities**.
2. Show disabled entities and enable the prerelease switch associated with Textbelt SMS.
3. Turn the switch on.
4. In HACS, open Textbelt SMS and select **Update information**.
5. Download Textbelt SMS and select the desired published prerelease under **Need a different version?**.

Stable releases do not require the prerelease switch.

#### A published version is missing

Check the [Releases page](https://github.com/stroodle96/textbelt-sms/releases) first.
If the version has not been published, refreshing HACS cannot make it available.
If it exists, open Textbelt SMS, select **Update information** from its three-dot
menu, then reopen **Download** or **Redownload**. Check prerelease access and the
minimum Home Assistant/HACS versions if it is still missing.

#### Rolling back

Open Textbelt SMS in HACS, open its three-dot menu, select **Redownload**, and
choose an earlier release under **Need a different version?**. Restart Home
Assistant afterward. Use **Update information** first if the expected release is
not listed. The historical `v0.1.0` release is marked as a prerelease, so beta
access may be needed to select it.

### Manual Installation

1. Copy the `custom_components/textbelt_sms` directory to your Home Assistant `/config/custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings -> Devices & Services
2. Click the "+ ADD INTEGRATION" button
3. Search for "Textbelt SMS"
4. Enter your Textbelt API key
   - Get an API key from [Textbelt](https://textbelt.com/)
   - Testing key available: "textbelt"

## Usage

### Service

The integration provides a service `textbelt_sms.send_sms` with the following parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| phone     | Yes      | Phone number in international format (e.g., +1234567890) |
| message   | Yes      | The message text to send |

### Remaining SMS quota

`sensor.textbelt_sms_quota_remaining` shows the remaining SMS credits for the API
key configured in this integration. It reads Textbelt's
[credit balance endpoint](https://docs.textbelt.com/other-api-endpoints#checking-your-credit-balance)
at startup, every five minutes, and after an SMS send attempt. Closely spaced
refresh requests are coalesced by Home Assistant and may take a few seconds.
Quota checks do not send an SMS.

The sensor uses the unit `credits`; a value of `0` means no credits remain. If the
lookup fails, the sensor becomes `unavailable` and retries automatically. SMS
sending and delivery-status tracking remain operational. The API key is not
included in the entity ID, attributes, or quota error messages.

Use this sensor in dashboards or a numeric-state automation to alert when credits
run low. To refresh after purchasing credits, call `homeassistant.update_entity`
with `entity_id: sensor.textbelt_sms_quota_remaining`.

### Example Automation

```yaml
automation:
  - alias: "Low Battery Notification"
    trigger:
      - platform: numeric_state
        entity_id: sensor.phone_battery
        below: 20
    action:
      - service: textbelt_sms.send_sms
        data:
          phone: "+1234567890"
          message: "Your phone battery is low!"
```

## API Key Options

- **Testing**: Use `textbelt` as your API key (limited to 1 message)
- **Pay-as-you-go**: Purchase credits from [Textbelt](https://textbelt.com/)

## Troubleshooting

Check Home Assistant logs for detailed error messages. Common issues:

- Invalid API key
- Invalid phone number format
- API quota exceeded

## Support

- Report issues on [GitHub](https://github.com/stroodle96/textbelt-sms/issues)
- Textbelt API documentation: [docs.textbelt.com](https://docs.textbelt.com/)

## License

This project is licensed under MIT License - see the [LICENSE](LICENSE) file for details.

### Message preparation and long alerts

The `textbelt_sms.send_sms` action preserves newlines and prepares readable
Markdown/HTML text using the reviewed 124-character GSM policy. Smart quotes,
bullets and long dashes receive readable substitutions; unsupported content
(such as emoji or unreviewed scripts) produces a visible action error before
sending. Empty messages also fail before sending.

Long alerts split at sentence or word boundaries where possible, with `(1/N)`
labels. Each part includes at most 160 GSM septets, including labels, and one
alert may use at most five parts. Larger automation alerts fail before any part
is sent. Extension characters count as two septets. These are integration
budgets; Textbelt's true request maximum remains unknown. Textbelt may append
sender or STOP text and charge additional credits. The observed character
trial covered one account and US/T-Mobile, not all carriers.

### Standard notification targets

Open **Settings → Devices & services → Textbelt SMS → Configure** and enter one
notification recipient per line. Use explicit international numbers beginning
with `+` and a country code; spaces, hyphens, dots, and parentheses are normalized.
Numbers must contain 2–15 ASCII digits after `+`; validation checks syntax, not
whether the number is assigned or deliverable. Duplicate numbers create one target.
Leave the list empty to keep the existing outbound action only.

Each recipient creates a `notify` entity with a masked last-four-digit name and
a hashed entity ID. Rename it in Home Assistant's entity settings if desired.
Removing a recipient leaves its registry entry unavailable; re-adding the same
number restores its identity and custom name. Recipient order does not change identity.
Recipients do not authorize incoming Assist requests. Alerts work without an
external callback or Assist configuration.

Select your actual entity in the action editor:

```yaml
action: notify.send_message
target:
  entity_id: notify.my_phone
data:
  title: Water leak
  message: Water was detected in the utility room.
```

Title and message use the shared preparation and multipart sender. Provider
rejection, partial acceptance, or uncertain submission raises an action error
and does not advance the successful-notification timestamp. Acceptance is not
carrier delivery confirmation. Quota refresh runs independently after attempts.
The `textbelt_sms.send_sms` action remains available for dynamic destinations.

### Native Assist over SMS

Native Assist is opt-in. In **Settings → Devices & services → Textbelt SMS →
Configure**, enable Assist and enter authorized senders using explicit
international `+` numbers, one per line. Notification recipients are independent
and do not grant permission to control Home Assistant. Select an Assist pipeline
or leave it on **preferred**; preferred is resolved for each incoming turn, so
changing Home Assistant's preferred pipeline takes effect without editing this
integration. Configure the conversation inactivity timeout (default 1800 seconds).

Configure Home Assistant's external URL as public HTTPS, and make its generated
`/api/webhook/<random-entry-ID>` callback reachable by Textbelt. The ID persists
across reloads and restarts. URL validation does not prove external reachability.
Use a paid, reply-capable Textbelt account; Textbelt documents replies for US
numbers and non-free keys. The public `textbelt` key and keys ending in `_test`
cannot enable Assist or authenticate replies. Number syntax validation does not
establish country, carrier, account eligibility or satellite delivery.

Disable old SMS-to-Assist routing automations/scripts before enabling native
Assist, including consumers of `textbelt_sms_reply` that invoke home actions.
The compatibility event still exists; leaving a second router enabled can cause
a second action. Native routing needs no user automation or script.

Start a thread from Home Assistant:

```yaml
action: textbelt_sms.start_conversation
data:
  phone: "+15551234567"  # replace with an authorized, real international number
```

The greeting creates an accepted outgoing ID to which replies can correlate.
Reply to that thread to use the selected pipeline. Context is isolated by sender
and resolved pipeline. `/new` resets that sender's conversations and sends a
confirmation without running Assist. Exact trimmed `STOP`, `START` and `HELP`
are excluded from native execution and receive no automatic integration reply;
provider opt-out handling remains separate. A pipeline change, timeout, reload,
disable or restart clears volatile conversation context. Start a new thread if
an old reply no longer correlates.

Replies require Textbelt's timestamp/HMAC signature and correlation with a known
accepted outgoing ID and its recipient. Native execution additionally checks the
current authorized-sender list. Local metadata expires after seven days; an
identical admitted body is suppressed for two minutes even with a fresh
signature. These are integration policies, not documented provider reply/retry
windows or an exactly-once guarantee. Unauthorized and malformed callbacks are
rejected without running Assist. Admitted work lost during shutdown is not replayed.

Existing installations migrate with native Assist disabled, preserving the API
key, recipient options and sensor identities. The signed fixed
`/api/webhook/textbelt_sms_reply` endpoint remains **events only**, including
outstanding older replies; it never executes native Assist. The dynamic
`textbelt_sms.send_sms` service still accepts documented legacy phone strings.
If such a destination cannot be normalized as explicit international format, its
send uses the fixed signed events-only callback and skips native correlation
metadata. Canonical dynamic, notify and native sends use the generated endpoint.
Use explicit international numbers and `start_conversation` for native threads.

### Delivery, cost and privacy boundaries

Native greetings and replies share the reviewed 124-character GSM repertoire,
160-septet prepared-part limit (including multipart labels) and five-prepared-part
cap with dynamic sends and notification entities. Long native speech may be
compacted/truncated to the bounded budget; unsupported or empty speech receives a
safe explanatory response. The character observations cover one account and
US/T-Mobile only; they do not establish every-carrier or every-character delivery
fidelity. Provider request maxima, appended content and carrier segment charging
remain separate. Five prepared parts is a submission cap, **not a guaranteed
five-credit maximum**. A greeting, `/new` confirmation and each reply can consume
credits. Check the quota sensor and Textbelt's account balance.

Partial acceptance and an accepted-then-disconnected request are visible failures.
Known accepted part IDs remain available for delivery tracking; uncertain parts
cannot safely be claimed accepted. Sending stops at the first failure and does
not retry automatically. A failed response does not rerun the Assist pipeline.
After an Assist timeout/error, check Home Assistant before resending: an action
may already have completed. Provider acceptance does not prove delivery. Quota
and status lookup failures do not cause additional SMS sends.

The integration's reply-state Store retains metadata only: outgoing IDs,
normalized recipients, timestamps and replay digests. Its conversation mappings,
transcripts and queued turns are not persisted by this implementation. The
existing last-message sensor still exposes outgoing message attributes, and Home
Assistant Recorder/history may retain that outgoing text. Authenticated reply
events expose inbound text to configured listeners, and selected conversation
agents may have their own storage policies. Do not interpret the metadata-only
Store as a blanket claim that Home Assistant retains no SMS content.

Local fixture tests cannot establish real provider/carrier delivery, satellite
behavior, callback retry/acknowledgment rules, inbound-message IDs or reply windows.
See [local validation evidence](docs/research/stage4-local-validation.md).
