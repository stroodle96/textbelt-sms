#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
smoke_dir="$root/tests/smoke"
project="textbelt-sms-smoke-${GITHUB_RUN_ID:-local}-${RANDOM}"
config_parent="$(realpath -- "${TMPDIR:-/tmp}")"
config_dir="$(mktemp -d "$config_parent/textbelt-ha-config.XXXXXX")"
artifact_dir="$(mktemp -d "${TMPDIR:-/tmp}/textbelt-ha-artifacts-XXXXXX")"
export HA_CONFIG_DIR="$config_dir" COMPOSE_PROJECT_NAME="$project"
export LIVE_SMOKE="${LIVE_SMOKE:-0}"
case "$LIVE_SMOKE" in 0|1) ;; *) printf "LIVE_SMOKE must be 0 or 1\n" >&2; exit 2 ;; esac
if [[ "$LIVE_SMOKE" == 0 ]]; then
  # An inherited endpoint/key must never turn an offline check into a provider send.
  export TEXTBELT_SMS_API_BASE_URL='http://textbelt:8080'
  export TEXTBELT_API_KEY='smoke-test-key'
  export TEXTBELT_STUB_URL='http://127.0.0.1:8080'
fi
compose() { docker compose -p "$project" -f "$smoke_dir/docker-compose.yml" "$@"; }
printf %s "$project" > "$config_dir/.textbelt-smoke-fixture"
cat > "$config_dir/configuration.yaml" <<'EOF'
default_config:
homeassistant:
  external_url: https://ha.example.com
http:
  server_port: 8123
EOF
cleanup() {
  result=$?
  printf 'compose_project=%s\nlive_smoke=%s\nexit_code=%s\n' "$project" "$LIVE_SMOKE" "$result" > "$artifact_dir/smoke-report.txt"
  compose stop homeassistant || true
  compose ps -a > "$artifact_dir/compose-ps.txt" || true
  compose config > "$artifact_dir/compose-config.yml" || true
  compose logs --no-color > "$artifact_dir/compose.log" || true
  compose logs --no-color homeassistant > "$artifact_dir/homeassistant.log" || true
  compose logs --no-color textbelt > "$artifact_dir/textbelt.log" || true
  compose cp textbelt:/data/requests.json "$artifact_dir/stub-requests.json" || true
  compose cp textbelt:/data/outcomes.json "$artifact_dir/stub-outcomes.json" || true
  for file in stage4-state.json stage4-evidence.json configuration.yaml; do
    compose cp "homeassistant:/config/$file" "$artifact_dir/$file" || true
  done
  if [[ "$LIVE_SMOKE" == 0 ]]; then
    compose cp homeassistant:/config/.storage/core.config_entries "$artifact_dir/migrated-entries.json" || true
    entry_id="$(python3 -c 'import json,sys; print(next(e["entry_id"] for e in json.load(open(sys.argv[1]))["data"]["entries"] if e["domain"] == "textbelt_sms"))' "$artifact_dir/migrated-entries.json" 2>/dev/null || true)"
    if [[ "$entry_id" =~ ^[A-Za-z0-9_-]+$ ]]; then
      compose cp "homeassistant:/config/.storage/textbelt_sms.reply.$entry_id" "$artifact_dir/textbelt_sms.reply.$entry_id" || true
    fi
  fi
  compose down -v --remove-orphans || true
  # Verify the resolved mktemp target before mounting it into a cleanup-only helper.
  if [[ ! -L "$config_dir" && "$(realpath -- "$config_dir")" == "$config_dir" && "$(dirname -- "$config_dir")" == "$config_parent" && "$(basename -- "$config_dir")" =~ ^textbelt-ha-config\.[A-Za-z0-9]+$ ]]; then
    if docker run --rm --network none \
      --mount "type=bind,source=$config_dir,target=/fixture" \
      --mount "type=bind,source=$smoke_dir/fixture_files.py,target=/fixture_files.py,readonly" \
      python:3.14.2-alpine python /fixture_files.py "$project"; then
      rmdir -- "$config_dir"
    else
      printf 'Fixture cleanup failed; retained verified config: %s\n' "$config_dir" >&2
    fi
  else
    printf 'Refusing unverified fixture cleanup: %s\n' "$config_dir" >&2
  fi
  printf 'Smoke artifacts: %s\n' "$artifact_dir"
}
trap cleanup EXIT
compose up -d
token="$(python3 "$smoke_dir/exercise_api.py")"
compose exec -T homeassistant python -m homeassistant --script check_config --config /config
if [[ "$LIVE_SMOKE" == 0 ]]; then
  curl --fail --silent -X POST http://127.0.0.1:8080/mode/failure >/dev/null
  python3 "$smoke_dir/exercise_api.py" --token "$token" --failure
  curl --fail --silent -X POST http://127.0.0.1:8080/mode/success >/dev/null
fi
compose restart homeassistant
python3 "$smoke_dir/exercise_api.py" --token "$token" --verify-runtime
if [[ "$LIVE_SMOKE" == 0 ]]; then
  curl --fail --silent -X POST http://127.0.0.1:8080/status/delivered >/dev/null
  python3 "$smoke_dir/exercise_api.py" --token "$token" --refresh-only
  python3 "$smoke_dir/exercise_api.py" --token "$token" --webhook-only
  python3 "$smoke_dir/exercise_api.py" --token "$token" --notify-only
  # Only disposable stopped HA storage is changed to emulate an old key-only entry.
  compose stop homeassistant
  compose cp homeassistant:/config/.storage/core.config_entries "$artifact_dir/premigration-entries.json"
  compose cp homeassistant:/config/.storage/core.entity_registry "$artifact_dir/premigration-registry.json"
  python3 - "$artifact_dir" <<'PY'
import json, pathlib, shutil, sys
artifact = pathlib.Path(sys.argv[1])
p = artifact / 'migration-input.json'
shutil.copy2(artifact / 'premigration-entries.json', p)
s = json.loads((artifact / 'premigration-entries.json').read_text())
entry = next(e for e in s['data']['entries'] if e['domain'] == 'textbelt_sms')
entry['version'] = 1
entry['data'] = {'api_key': 'smoke-test-key'}
entry['options']['smoke_unrelated'] = 'preserved'
p.write_text(json.dumps(s))
PY
  compose cp "$artifact_dir/migration-input.json" homeassistant:/config/.storage/core.config_entries
  compose start homeassistant
  python3 - "$smoke_dir" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from exercise_api import wait_for_ha
wait_for_ha('http://127.0.0.1:8123')
PY
  printf '%s\n' "$token" | compose exec -T homeassistant python /smoke/exercise_native.py --phase initial
  compose cp homeassistant:/config/.storage/core.config_entries "$artifact_dir/migrated-entries.json"
  compose cp homeassistant:/config/.storage/core.entity_registry "$artifact_dir/migrated-registry.json"
  python3 - "$artifact_dir" <<'PY'
import json, pathlib, sys
artifact = pathlib.Path(sys.argv[1])
s = json.loads((artifact / 'migrated-entries.json').read_text())
e = next(e for e in s['data']['entries'] if e['domain'] == 'textbelt_sms')
assert e['version'] == 2 and len(e['data']['webhook_id']) == 64
assert e['options']['smoke_unrelated'] == 'preserved'
old = json.loads((artifact / 'premigration-registry.json').read_text())
new = json.loads((artifact / 'migrated-registry.json').read_text())
ids = lambda v: {(e['entity_id'], e['unique_id']) for e in v['data']['entities'] if e.get('platform') == 'textbelt_sms'}
assert ids(old) == ids(new), 'Migration changed entity identities'
PY
  printf '%s\n' "$token" | compose exec -T homeassistant python /smoke/exercise_native.py --phase hold
  compose restart homeassistant
  python3 - "$smoke_dir" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from exercise_api import wait_for_ha
wait_for_ha('http://127.0.0.1:8123')
PY
  printf '%s\n' "$token" | compose exec -T homeassistant python /smoke/exercise_native.py --phase restart
fi
