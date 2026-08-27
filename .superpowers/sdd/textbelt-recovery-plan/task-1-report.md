# Task 1 implementation report

## Implementation

- Added the pinned test stack in `requirements_test.txt` (`homeassistant==2026.8.2`, `pytest-homeassistant-custom-component==0.13.356`, and coverage) while keeping ordinary development requirements separate and Ruff pinned at 0.15.15.
- Added HA-aware pytest configuration (`asyncio_mode = auto`, coverage XML, and an 80% floor) and tests covering config flow, single-instance setup, API payload/error handling, service registration/errors, lifecycle cleanup, and reply events.
- Added `CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)`, translation description placeholders, and keyed config-flow validation errors.
- Made the API endpoint derive only from `TEXTBELT_SMS_API_BASE_URL`, normalize trailing slashes, default to `https://textbelt.com`, and consistently classify authentication, API, HTTP, communication/timeout, and malformed-response failures.
- Registered a real `send_sms` service schema, surfaced invalid calls and Textbelt failures as `HomeAssistantError`, omitted sensitive payload logging, and removed service/webhook/client state on unload.
- Added unit-test, real-HA smoke, and protected live-smoke workflows with immutable action SHAs and least-privilege permissions.
- Added a Docker Compose real-HA harness with Home Assistant 2026.8.2, a deterministic local Textbelt stub, config validation, success/failure/restart/webhook exercise paths, request assertions, and failure log collection.
- Documented exact local unit and smoke commands in `CONTRIBUTING.md`.

## Files changed

`custom_components/textbelt_sms/{__init__.py,api.py,config_flow.py,const.py,translations/en.json}`; `requirements.txt`; `requirements_test.txt`; `pytest.ini`; `.ruff.toml`; `tests/`; `.github/workflows/{unit-test.yml,ha-smoke.yml,live-smoke.yml}`; `CONTRIBUTING.md`.

## Commands and results

- `python -m pip install -r requirements_test.txt` — blocked locally: the bundled Python is 3.12.13 and HA 2026.8.2 requires Python >=3.14.2. The exact pin remains in CI.
- `python -m ruff check . --no-cache` — passed (`All checks passed!`).
- `python -m ruff format . --check --no-cache` — passed (`10 files already formatted`).
- `python -c "...ast.parse..."` — passed (`AST OK: 6 files`).
- JSON parse of `manifest.json` and `translations/en.json` — passed (`JSON OK`).
- `python -m pytest tests --collect-only -q` — not executable locally because the pinned Home Assistant/plugin stack cannot be installed under Python 3.12.13; no HA test result is claimed.

## TDD RED/GREEN evidence

Tests were written before the production behavior edits. The requested RED/GREEN pytest execution could not be completed locally because the required HA package rejects Python 3.12.13 before test collection. The CI unit job runs the full pinned stack on Python 3.14, where the tests are intended to provide the authoritative RED/GREEN and coverage evidence.

## Self-review

- No API key or message body is logged.
- The public service remains `textbelt_sms.send_sms` with required `phone` and `message` fields.
- The live workflow has no pull-request trigger, uses the `_test` secret name, and intentionally sends no SMS.
- The real smoke path uses only the local stub endpoint and collects compose logs on every exit.
- No Docker or GitHub state was changed locally.

## Concerns

The local environment has no Python 3.14.2 runtime and Docker is not installed, so HA pytest and the real-container smoke harness were not runnable here. CI must provide Python 3.14 and Docker; the configured smoke workflow also expects the protected `HA_SMOKE_TOKEN` secret. The live workflow skips its verification step when `TEXTBELT_API_KEY_test` is absent.
