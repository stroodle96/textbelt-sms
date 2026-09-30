# Stage 0 local validation

Validated 2026-09-30 in an isolated branch based on upstream `b1e7c8f1ef4c90741c8d25134fc1fe3800d76895`. Product files were unchanged.

Environment: Ubuntu WSL2, CPython 3.14.2, Docker Engine 28.2.2, repository-pinned Home Assistant 2026.8.2, pytest-homeassistant-custom-component 0.13.356, pytest-cov 7.1.0, and Ruff 0.16.8. Dependencies were installed in an isolated environment using `uv pip install --python <venv>/bin/python -r requirements_test.txt`. Unit CI uses Python 3.14; lint CI uses Python 3.13. The pinned Ruff tool was run locally under Python 3.14.

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests/provider -v` | 6 passed |
| `python -m compileall -q scripts/provider_probe.py tests/provider` | Passed |
| `python scripts/provider_probe.py /tmp/textbelt-stage0-reproduced.jsonl --overwrite` followed by `cmp docs/research/probes/v1-inputs-and-pending-results.jsonl /tmp/textbelt-stage0-reproduced.jsonl` | Byte-identical 177-probe corpus |
| `python -m pytest -q` | 99 passed in 14.19 seconds; integration coverage 95.78%, exceeding required 80% |
| `python -m ruff check .` | Passed |
| `python -m ruff format --check .` | 30 files already formatted |
| `bash tests/smoke/run.sh` with `LIVE_SMOKE` and `TEXTBELT_SMS_API_BASE_URL` unset | Passed, exit 0 |
| Native Windows Git `git diff --check` | Passed |

The deterministic smoke used Home Assistant and the local Textbelt stub. It checked successful sending, simulated rejection, HA configuration, restart, delivery-status refresh, and webhook behavior. The preserved stub ledger contains exactly three requests using synthetic numbers and the local smoke key; its report records `live_smoke=0`. No Textbelt provider POST or SMS occurred. Docker containers/network/volume were removed. Task-created root-owned temporary HA configuration was removed after the harness cleanup warning.

Raw validation logs and safe stub request/report evidence are retained in the local handoff folder, outside the committed research artifacts. Generated authentication storage was not copied into the handoff.

These checks establish offline preparation and regression coverage. They do not establish provider validation, carrier delivery, received-text fidelity, satellite delivery, or an empirically supported production allowlist. Every empirical probe remains pending; Stage 0 is incomplete and Stage 1 requires its checkpoint approval.
