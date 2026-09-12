#!/usr/bin/env bash
set -euo pipefail

API_URL="${RUPTURELAB_API_URL:-http://127.0.0.1:8000}"
PROXY_URL="${RUPTURELAB_PROXY_URL:-http://127.0.0.1:8080}"
TARGET_URL="${RUPTURELAB_TARGET_URL:-http://127.0.0.1:9000}"
FRONTEND_URL="${RUPTURELAB_FRONTEND_URL:-http://127.0.0.1:3000}"

wait_for_url() {
  local url="$1"
  local attempts="${2:-60}"

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      printf 'PASS  %s\n' "$url"
      return 0
    fi
    sleep 1
  done

  printf 'FAIL  %s\n' "$url" >&2
  return 1
}


printf '\n=== RuptureLab system smoke ===\n'
wait_for_url "$TARGET_URL/demo/health"
wait_for_url "$PROXY_URL/_rupturelab/health"
wait_for_url "$API_URL/health"
wait_for_url "$API_URL/ready"
wait_for_url "$FRONTEND_URL"

for service in demo-target fault-proxy api frontend; do
  uid="$(docker compose exec -T "$service" id -u)"
  if [[ "$uid" == "0" ]]; then
    printf 'Service %s is running as root\n' "$service" >&2
    exit 1
  fi
  printf 'PASS  %s runs as non-root uid %s\n' "$service" "$uid"
done

run_name="compose-concurrency-$(date +%s)"
start_response="$({
  curl -fsS \
    -H 'Content-Type: application/json' \
    -d "{
      \"name\": \"$run_name\",
      \"method\": \"GET\",
      \"path\": \"/demo/products\",
      \"requests_per_phase\": 5,
      \"interval_ms\": 200,
      \"fault\": {
        \"enabled\": true,
        \"path_prefix\": \"/demo/products\",
        \"methods\": [\"GET\"],
        \"probability\": 1.0,
        \"error_status\": 503
      },
      \"contract\": {
        \"name\": \"compose smoke contract\",
        \"baseline\": {\"min_success_rate\": 1.0},
        \"fault\": {\"min_fault_rate\": 1.0},
        \"recovery\": {\"min_success_rate\": 1.0}
      }
    }" \
    "$API_URL/experiments/start"
})"

experiment_id="$(printf '%s' "$start_response" | python3 -c 'import json,sys; print(json.load(sys.stdin)["experiment_id"])')"
printf 'Started %s (%s)\n' "$run_name" "$experiment_id"

busy_status="$({
  curl -sS -o /tmp/rupturelab-busy.json -w '%{http_code}' \
    -H 'Content-Type: application/json' \
    -d "{
      \"name\": \"overlap-check\",
      \"method\": \"GET\",
      \"path\": \"/demo/products\",
      \"requests_per_phase\": 1,
      \"fault\": {
        \"enabled\": true,
        \"path_prefix\": \"/demo/products\",
        \"methods\": [\"GET\"],
        \"probability\": 1.0,
        \"error_status\": 503
      }
    }" \
    "$API_URL/experiments/start"
})"

if [[ "$busy_status" != "409" ]]; then
  printf 'Expected overlapping experiment to return 409, got %s\n' "$busy_status" >&2
  cat /tmp/rupturelab-busy.json >&2
  exit 1
fi
printf 'PASS  overlapping experiment rejected with 409\n'

result_file="/tmp/rupturelab-system-result.json"
for _ in {1..60}; do
  status="$(curl -sS -o "$result_file" -w '%{http_code}' "$API_URL/experiments/$experiment_id")"
  if [[ "$status" == "200" ]]; then
    break
  fi
  if [[ "$status" != "404" ]]; then
    printf 'Unexpected result status: %s\n' "$status" >&2
    cat "$result_file" >&2
    exit 1
  fi
  sleep 1
done

python3 - "$result_file" "$experiment_id" "$run_name" <<'PY'
import json
import sys

result_file, experiment_id, run_name = sys.argv[1:]
with open(result_file, encoding="utf-8") as handle:
    result = json.load(handle)
assert result["experiment_id"] == experiment_id
assert result["name"] == run_name
assert result["contract_evaluation"]["passed"] is True
assert [phase["phase"] for phase in result["phases"]] == ["baseline", "fault", "recovery"]
assert sum(len(phase["measurements"]) for phase in result["phases"]) == 15
print("PASS  background experiment completed and persisted")
PY

printf '\nRestarting control API...\n'
docker compose restart api >/dev/null
wait_for_url "$API_URL/ready"

curl -fsS "$API_URL/experiments/$experiment_id" > /tmp/rupturelab-system-after-restart.json
python3 - /tmp/rupturelab-system-after-restart.json "$experiment_id" <<'PY'
import json
import sys

result_file, experiment_id = sys.argv[1:]
with open(result_file, encoding="utf-8") as handle:
    result = json.load(handle)
assert result["experiment_id"] == experiment_id
assert result["contract_evaluation"]["passed"] is True
print("PASS  persisted experiment survived API restart")
PY

printf '\nRestarting target and fault proxy...\n'
docker compose restart demo-target fault-proxy >/dev/null
wait_for_url "$TARGET_URL/demo/health"
wait_for_url "$PROXY_URL/_rupturelab/health"
wait_for_url "$API_URL/ready"

recovery_response="$({
  curl -fsS \
    -H 'Content-Type: application/json' \
    -d '{
      "name": "compose-service-recovery",
      "method": "GET",
      "path": "/demo/products",
      "requests_per_phase": 1,
      "fault": {
        "enabled": true,
        "path_prefix": "/demo/products",
        "methods": ["GET"],
        "probability": 1.0,
        "error_status": 503
      }
    }' \
    "$API_URL/experiments/run"
})"
printf '%s' "$recovery_response" | python3 -c '
import json, sys
result = json.load(sys.stdin)
phases = {phase["phase"]: phase for phase in result["phases"]}
assert phases["baseline"]["successful_requests"] == 1
assert phases["fault"]["faulted_requests"] == 1
assert phases["recovery"]["successful_requests"] == 1
print("PASS  experiment execution recovered after target/proxy restart")
'

rows="$(
  docker compose exec -T postgres \
    psql -U rupturelab -d rupturelab -Atc \
    "SELECT COUNT(*) FROM experiment_runs WHERE id = '$experiment_id';"
)"
[[ "$rows" == "1" ]] || {
  printf 'Expected one persisted experiment row, got %s\n' "$rows" >&2
  exit 1
}
printf 'PASS  PostgreSQL contains persisted experiment\n'

persisted_before="$(
  docker compose exec -T postgres \
    psql -U rupturelab -d rupturelab -Atc \
    "SELECT COUNT(*) FROM experiment_runs WHERE name LIKE 'compose-concurrency-%';"
)"

printf '\nRecreating the full stack without deleting its named volume...\n'
docker compose down >/dev/null
docker compose up -d --wait --wait-timeout 120 >/dev/null
wait_for_url "$FRONTEND_URL"
wait_for_url "$API_URL/ready"

persisted_after="$(
  docker compose exec -T postgres \
    psql -U rupturelab -d rupturelab -Atc \
    "SELECT COUNT(*) FROM experiment_runs WHERE name LIKE 'compose-concurrency-%';"
)"

if (( persisted_before < 1 || persisted_after < persisted_before )); then
  printf 'Named-volume persistence check failed: before=%s after=%s\n' \
    "$persisted_before" "$persisted_after" >&2
  exit 1
fi
printf 'PASS  PostgreSQL history survived full Compose recreation\n'

printf '\nPASS: RuptureLab Compose system smoke completed.\n'
