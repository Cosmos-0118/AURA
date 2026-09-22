#!/usr/bin/env bash

set -Eeuo pipefail

MODULE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$MODULE_DIR"
COMPOSE=(docker compose)
if [[ -f "$MODULE_DIR/../.env" ]]; then
  COMPOSE=(docker compose --env-file "$MODULE_DIR/../.env")
fi

MODE="docker"
NO_CACHE=1
START_WORKER=1
PORT="${INTEL_PORT:-8787}"
HOST="${INTEL_HOST:-127.0.0.1}"
RUN_DIR="$MODULE_DIR/.run"
SERVER_PID_FILE="$RUN_DIR/server.pid"
WORKER_PID_FILE="$RUN_DIR/worker.pid"
WORKER_LOG="$RUN_DIR/worker.log"

log() {
  printf '[competitor-intelligence] %s\n' "$*"
}

usage() {
  cat <<'EOF'
Usage: ./run.sh [options]

Starts the competitor-intelligence dashboard and worker.

Options:
  --docker      Stop, rebuild, and start the Docker Compose services (default).
  --local       Run only the dashboard and worker directly with Python.
  --cached      Allow Docker to reuse build cache.
  --no-worker   Start only the dashboard server in local mode.
  -h, --help    Show this help.

Examples:
  ./run.sh
  ./run.sh --local
  ./run.sh --docker
  ./run.sh --docker --cached
EOF
}

process_command() {
  ps -p "$1" -o command= 2>/dev/null || true
}

is_module_process() {
  local pid="$1"
  local command
  command="$(process_command "$pid")"
  [[ "$command" == *"competitor_intelligence"* ]]
}

stop_pid() {
  local pid="$1"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 0
  kill -0 "$pid" 2>/dev/null || return 0

  if ! is_module_process "$pid"; then
    log "Leaving unrelated process $pid running."
    return 0
  fi

  log "Stopping process $pid."
  kill "$pid" 2>/dev/null || true
  for _ in 1 2 3 4 5; do
    kill -0 "$pid" 2>/dev/null || return 0
    sleep 1
  done
  log "Process $pid did not stop gracefully; terminating it."
  kill -KILL "$pid" 2>/dev/null || true
}

stop_pid_file() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] || return 0
  local pid
  pid="$(<"$pid_file")"
  stop_pid "$pid"
  rm -f -- "$pid_file"
}

stop_local_processes() {
  stop_pid_file "$SERVER_PID_FILE"
  stop_pid_file "$WORKER_PID_FILE"

  if command -v lsof >/dev/null 2>&1; then
    while IFS= read -r pid; do
      [[ -n "$pid" ]] || continue
      stop_pid "$pid"
    done < <(lsof -nP -t -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)
  fi

  if command -v pgrep >/dev/null 2>&1; then
    while IFS= read -r pid; do
      [[ -n "$pid" ]] || continue
      stop_pid "$pid"
    done < <(pgrep -f 'python(3)? -m competitor_intelligence worker' 2>/dev/null || true)
  fi
}

clear_local_builds() {
  log "Clearing Python cache artifacts."
  for directory in \
    "$MODULE_DIR/competitor_intelligence" \
    "$MODULE_DIR/tests" \
    "$MODULE_DIR/changedetection-ui"; do
    [[ -d "$directory" ]] || continue
    find "$directory" -type d \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf -- {} +
  done
  rm -rf -- "$MODULE_DIR/.pytest_cache"
}

check_python() {
  command -v python3 >/dev/null 2>&1 || {
    log "python3 is required for local mode."
    exit 1
  }
  python3 - <<'PY'
import sys

if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11 or newer is required.")
PY
}

load_local_changedetection_key() {
  if [[ -n "${CHANGEDETECTION_API_KEY:-}" ]]; then
    return
  fi
  if ! command -v docker >/dev/null 2>&1; then
    return
  fi
  local token
  token="$("${COMPOSE[@]}" exec -T changedetection python -c 'import json; print(json.load(open("/datastore/changedetection.json"))["settings"]["application"]["api_access_token"])' 2>/dev/null)" || return
  [[ -n "$token" ]] || return
  export CHANGEDETECTION_API_KEY="$token"
  log "Loaded the local changedetection API credential."
}

wait_for_url() {
  local url="$1"
  local label="$2"
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    if command -v curl >/dev/null 2>&1 && curl -fsSL --max-time 2 "$url" >/dev/null 2>&1; then
      log "$label is ready at $url"
      return 0
    fi
    sleep 1
  done
  log "$label did not become ready at $url."
  return 1
}

wait_for_health() {
  local check_port="${1:-$PORT}"
  wait_for_url "http://127.0.0.1:${check_port}/api/health" "Intelligence dashboard"
}

start_local() {
  check_python
  load_local_changedetection_key
  if [[ -n "${CHANGEDETECTION_API_KEY:-}" && -z "${CHANGEDETECTION_API_URL:-}" ]]; then
    export CHANGEDETECTION_API_URL=http://127.0.0.1:5001
  fi
  stop_local_processes
  clear_local_builds
  mkdir -p -- "$RUN_DIR"
  : > "$WORKER_LOG"

  local worker_pid=""
  if [[ "$START_WORKER" == 1 ]]; then
    log "Starting collector worker."
    python3 -m competitor_intelligence worker \
      >"$WORKER_LOG" 2>&1 < /dev/null &
    worker_pid="$!"
    echo "$worker_pid" > "$WORKER_PID_FILE"
    sleep 1
    if ! kill -0 "$worker_pid" 2>/dev/null; then
      log "Collector worker failed to start."
      cat "$WORKER_LOG"
      rm -f -- "$WORKER_PID_FILE"
      exit 1
    fi
  fi

  cleanup() {
    if [[ -n "$worker_pid" ]]; then
      stop_pid "$worker_pid"
    fi
    rm -f -- "$WORKER_PID_FILE"
  }
  trap cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM

  log "Dashboard is running at http://127.0.0.1:${PORT}"
  log "Press Ctrl-C to stop the dashboard and worker."
  log "Worker log: $WORKER_LOG"
  python3 -m competitor_intelligence serve --host "$HOST" --port "$PORT"
}

start_docker() {
  command -v docker >/dev/null 2>&1 || {
    log "Docker is required for Docker mode."
    exit 1
  }
  docker compose version >/dev/null 2>&1 || {
    log "Docker Compose is required for Docker mode."
    exit 1
  }

  stop_local_processes
  log "Stopping existing Compose services without deleting intelligence data."
  "${COMPOSE[@]}" down --remove-orphans
  if [[ "$NO_CACHE" == 1 ]]; then
    log "Rebuilding Docker images without cache."
    "${COMPOSE[@]}" build --no-cache
  else
    log "Rebuilding Docker images using available cache."
    "${COMPOSE[@]}" build
  fi
  log "Starting changedetection."
  "${COMPOSE[@]}" up -d changedetection
  if ! wait_for_url "http://127.0.0.1:5001/" "changedetection UI"; then
    "${COMPOSE[@]}" logs --tail=50 changedetection
    exit 1
  fi
  load_local_changedetection_key
  log "Starting intelligence and collector worker."
  "${COMPOSE[@]}" up -d intelligence worker
  if ! wait_for_health 8787; then
    "${COMPOSE[@]}" logs --tail=50 intelligence
    exit 1
  fi
  if ! wait_for_url "http://127.0.0.1:5001/" "changedetection UI"; then
    "${COMPOSE[@]}" logs --tail=50 changedetection
    exit 1
  fi
  log "Docker services are running."
}

while (($# > 0)); do
  case "$1" in
    --local)
      MODE="local"
      ;;
    --docker)
      MODE="docker"
      ;;
    --cached)
      NO_CACHE=0
      ;;
    --no-worker)
      START_WORKER=0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      log "Unknown option: $1"
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [[ "$MODE" == "docker" ]]; then
  start_docker
else
  start_local
fi
