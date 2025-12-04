---
applyTo: '**'
---
# Project Overview
This is a Home Assistant custom component that integrates the Textbelt SMS API for sending SMS messages. The component is distributed via HACS and follows Home Assistant's integration blueprint structure.

## Architecture
- **Entry Point**: `custom_components/textbelt_sms/__init__.py` handles integration setup, service registration, and webhook management
- **API Client**: `api.py` wraps the Textbelt REST API with custom exception hierarchy (`TextbeltApiClientError`, `TextbeltApiClientAuthenticationError`, `TextbeltApiClientCommunicationError`)
- **Config Flow**: `config_flow.py` provides UI-based configuration (API key input only)
- **Service**: `send_sms` service defined in `services.yaml` accepts `phone` (international format) and `message` parameters
- **Webhook**: Registers `/api/webhook/textbelt_sms_reply` endpoint that fires `textbelt_sms_reply` events for incoming SMS replies

## Key Integration Points
- Uses `homeassistant.helpers.aiohttp_client.async_get_clientsession()` for HTTP requests (do NOT create separate aiohttp sessions)
- Stores API client in `hass.data[DOMAIN][entry.entry_id]` 
- Webhook URL auto-constructed from `hass.config.api.base_url` (requires public HA instance for reply functionality)
- Service registered per config entry in `async_setup_entry()`, not in `async_setup()`

## Development Workflow
```bash
# Setup (install dependencies including Home Assistant)
./scripts/setup

# Lint and auto-fix (uses ruff)
./scripts/lint

# Run local HA instance with component loaded
./scripts/develop
# This sets PYTHONPATH to include custom_components/ and starts HA in debug mode
# Config directory: ./config/
```

## Critical Patterns
- **PYTHONPATH Trick**: `scripts/develop` exports `PYTHONPATH` to load component without symlinks
- **Logging**: Use `LOGGER` from `const.py` (already configured), not standalone loggers
- **API Key Validation**: Must use `_validate_api_key()` helper which raises `ValueError` on invalid keys
- **Webhook Lifecycle**: Register in `async_setup_entry()`, unregister in `async_unload_entry()` using constant `WEBHOOK_ID = "textbelt_sms_reply"`
- **Service Parameters**: Use `call.data.get()` pattern, validate before calling API

## Home Assistant Specifics
- Minimum HA version: `2025.2.4` (defined in `hacs.json` and `requirements.txt`)
- IoT class: `cloud_polling` (manifest.json)
- Config flow version: `1` (increment when changing config schema)
- Domain constant: `"textbelt_sms"` (must match directory name and manifest)

## External Dependencies
- **Textbelt API**: https://docs.textbelt.com/ - Use test key `"textbelt"` for development (1 free message)
- **HACS Publishing**: https://hacs.xyz/docs/publish/ - Follows HACS repository requirements
- **Blueprint Template**: https://github.com/ludeeus/integration_blueprint - Original structure source

## Code Style
- Use `ruff` for formatting and linting (run `./scripts/lint`)
- Type hints required (uses `from __future__ import annotations`)
- Async functions: prefix with `async_` (HA convention)
- Docstrings: Google style with Args/Returns/Raises sections

## Communication
Explain code changes educationally. If requirements are unclear, ask before implementing.