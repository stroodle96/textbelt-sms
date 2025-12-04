

## What?

This repository contains multiple files, here is a overview:

File | Purpose | Documentation
-- | -- | --
`.devcontainer.json` | Used for development/testing with Visual Studio Code. | [Documentation](https://code.visualstudio.com/docs/remote/containers)
`.github/ISSUE_TEMPLATE/*.yml` | Templates for the issue tracker | [Documentation](https://help.github.com/en/github/building-a-strong-community/configuring-issue-templates-for-your-repository)
`custom_components/textbelt-sms/*` | Integration files, this is where everything happens. | [Documentation](https://developers.home-assistant.io/docs/creating_component_index)
`CONTRIBUTING.md` | Guidelines on how to contribute. | [Documentation](https://help.github.com/en/github/building-a-strong-community/setting-guidelines-for-repository-contributors)
`LICENSE` | The license file for the project. | [Documentation](https://help.github.com/en/github/creating-cloning-and-archiving-repositories/licensing-a-repository)
`README.md` | The file you are reading now, should contain info about the integration, installation and configuration instructions. | [Documentation](https://help.github.com/en/github/writing-on-github/basic-writing-and-formatting-syntax)
`requirements.txt` | Python packages used for development/lint/testing this integration. | [Documentation](https://pip.pypa.io/en/stable/user_guide/#requirements-files)

## How?

1. Create a new repository in GitHub, using this repository as a template by clicking the "Use this template" button in the GitHub UI.
1. Open your new repository in Visual Studio Code devcontainer (Preferably with the "`Dev Containers: Clone Repository in Named Container Volume...`" option).
1. Rename all instances of the `textbelt-sms` to `custom_components/<your_integration_domain>` (e.g. `custom_components/awesome_integration`).
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

### HACS (Recommended)

1. Make sure [HACS](https://hacs.xyz) is installed
2. Add this repository through HACS
3. Search for "Textbelt SMS" in HACS and install
4. Restart Home Assistant

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

## Testing

This repository ships with a pytest suite powered by
[`pytest-homeassistant-custom-component`](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component).
Install the developer requirements and run `pytest` from the project root to exercise
the config flow and service layers without starting Home Assistant.

## Support

- Report issues on [GitHub](https://github.com/stroodle96/textbelt-sms/issues)
- Textbelt API documentation: [docs.textbelt.com](https://docs.textbelt.com/)

## License

This project is licensed under MIT License - see the [LICENSE](LICENSE) file for details.
