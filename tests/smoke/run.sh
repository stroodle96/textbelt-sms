#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
smoke_dir="$root/tests/smoke"
mkdir -p "$smoke_dir/ha-config"
cat > "$smoke_dir/ha-config/configuration.yaml" <<'EOF'
default_config:
http:
  server_port: 8123
EOF

cleanup() {
  docker compose -f "$smoke_dir/docker-compose.yml" logs --no-color > "$smoke_dir/ha-smoke.log" || true
  docker compose -f "$smoke_dir/docker-compose.yml" down -v || true
}
trap cleanup EXIT

docker compose -f "$smoke_dir/docker-compose.yml" up -d
docker compose -f "$smoke_dir/docker-compose.yml" exec -T homeassistant python -m homeassistant --script check_config --config /config

if [[ -z "${HA_TOKEN:-}" ]]; then
  echo "HA_TOKEN is required to run the real config-flow smoke test" >&2
  exit 2
fi

python3 "$smoke_dir/exercise_api.py" --token "$HA_TOKEN"

stub='http://127.0.0.1:8080'
python3 -c 'import json,sys,urllib.request; data=json.load(urllib.request.urlopen(sys.argv[1] + "/requests"))["requests"]; assert len(data) == 1, data; assert data[0]["phone"] == "+15551234567"; assert data[0]["message"] == "smoke"; assert data[0]["key"] == "smoke-test-key"' "$stub"
curl --fail --silent -X POST "$stub/mode/failure" >/dev/null
python3 "$smoke_dir/exercise_api.py" --token "$HA_TOKEN" --failure
curl --fail --silent -X POST "$stub/mode/success" >/dev/null
docker compose -f "$smoke_dir/docker-compose.yml" restart homeassistant
python3 "$smoke_dir/exercise_api.py" --token "$HA_TOKEN" --webhook-only
