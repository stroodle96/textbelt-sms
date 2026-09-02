#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
smoke_dir="$root/tests/smoke"
run_id="${GITHUB_RUN_ID:-local}-${RANDOM}"
project="textbelt-sms-smoke-${run_id}"
config_dir="$(mktemp -d "${TMPDIR:-/tmp}/textbelt-ha-config.XXXXXX")"
artifact_dir="$(mktemp -d "${TMPDIR:-/tmp}/textbelt-ha-artifacts-XXXXXX")"
export HA_CONFIG_DIR="$config_dir"
export COMPOSE_PROJECT_NAME="$project"
mkdir -p "$config_dir"
cat > "$config_dir/configuration.yaml" <<'EOF'
default_config:
homeassistant:
  external_url: http://homeassistant:8123
http:
  server_port: 8123
EOF

cleanup() {
  printf 'compose_project=%s\nlive_smoke=%s\n' "$project" "${LIVE_SMOKE:-0}" > "$artifact_dir/smoke-report.txt"
  docker compose -p "$project" -f "$smoke_dir/docker-compose.yml" ps -a > "$artifact_dir/compose-ps.txt" || true
  docker compose -p "$project" -f "$smoke_dir/docker-compose.yml" config > "$artifact_dir/compose-config.yml" || true
  docker compose -p "$project" -f "$smoke_dir/docker-compose.yml" logs --no-color > "$artifact_dir/compose.log" || true
  docker compose -p "$project" -f "$smoke_dir/docker-compose.yml" logs --no-color homeassistant > "$artifact_dir/homeassistant.log" || true
  docker compose -p "$project" -f "$smoke_dir/docker-compose.yml" logs --no-color textbelt > "$artifact_dir/textbelt.log" || true
  docker compose -p "$project" -f "$smoke_dir/docker-compose.yml" cp textbelt:/data/requests.json "$artifact_dir/stub-requests.json" || true
  docker compose -p "$project" -f "$smoke_dir/docker-compose.yml" cp textbelt:/data/mode "$artifact_dir/stub-mode" || true
  cp "$config_dir/configuration.yaml" "$artifact_dir/configuration.yaml" 2>/dev/null || true
  docker compose -p "$project" -f "$smoke_dir/docker-compose.yml" down -v --remove-orphans || true
  rm -rf "$config_dir" || true
}
trap cleanup EXIT

docker compose -p "$project" -f "$smoke_dir/docker-compose.yml" up -d
token="$(python3 "$smoke_dir/exercise_api.py")"
docker compose -p "$project" -f "$smoke_dir/docker-compose.yml" exec -T homeassistant python -m homeassistant --script check_config --config /config

stub='http://127.0.0.1:8080'
if [[ "${LIVE_SMOKE:-0}" != 1 ]]; then
  python3 -c 'import json,sys,urllib.request; data=json.load(urllib.request.urlopen(sys.argv[1] + "/requests"))["requests"]; assert len(data) == 1, data; assert data[0] == {"phone":"+15551234567","message":"smoke","key":"smoke-test-key","replyWebhookUrl":"http://homeassistant:8123/api/webhook/textbelt_sms_reply"}, data' "$stub"
  curl --fail --silent -X POST "$stub/mode/failure" >/dev/null
  python3 "$smoke_dir/exercise_api.py" --token "$token" --failure
  python3 -c 'import json,sys,urllib.request; data=json.load(urllib.request.urlopen(sys.argv[1] + "/requests"))["requests"]; assert len(data) == 2, data; assert data[1] == {"phone":"+15551234567","message":"smoke","key":"smoke-test-key","replyWebhookUrl":"http://homeassistant:8123/api/webhook/textbelt_sms_reply"}, data' "$stub"
  curl --fail --silent -X POST "$stub/mode/success" >/dev/null
fi
docker compose -p "$project" -f "$smoke_dir/docker-compose.yml" restart homeassistant
python3 "$smoke_dir/exercise_api.py" --token "$token" --verify-runtime
if [[ "${LIVE_SMOKE:-0}" != 1 ]]; then
  python3 -c 'import json,sys,urllib.request; data=json.load(urllib.request.urlopen(sys.argv[1] + "/requests"))["requests"]; assert len(data) == 3, data; assert data[2] == {"phone":"+15551234567","message":"restart-smoke","key":"smoke-test-key","replyWebhookUrl":"http://homeassistant:8123/api/webhook/textbelt_sms_reply"}, data' "$stub"
  curl --fail --silent -X POST "$stub/status/delivered" >/dev/null
  python3 "$smoke_dir/exercise_api.py" --token "$token" --refresh-only
fi
python3 "$smoke_dir/exercise_api.py" --token "$token" --webhook-only
