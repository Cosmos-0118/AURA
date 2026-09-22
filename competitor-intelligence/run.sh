#!/usr/bin/env bash

set -Eeuo pipefail

MODULE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$MODULE_DIR"
COMPOSE=(docker compose --profile discovery --profile social)
if [[ -f "$MODULE_DIR/../.env" ]]; then
  COMPOSE=(docker compose --env-file "$MODULE_DIR/../.env" --profile discovery --profile social)
fi

MODE="docker"
NO_CACHE=1
START_WORKER=1
START_DISCOVERY=1
PORT="${INTEL_PORT:-8787}"
HOST="${INTEL_HOST:-127.0.0.1}"
RUN_DIR="$MODULE_DIR/.run"
SERVER_PID_FILE="$RUN_DIR/server.pid"
WORKER_PID_FILE="$RUN_DIR/worker.pid"
WORKER_LOG="$RUN_DIR/worker.log"
FEEDS_PATH="$MODULE_DIR/config/feeds.json"

log() {
  printf '[competitor-intelligence] %s\n' "$*"
}

usage() {
  cat <<'EOF'
Usage: ./run.sh [options]

Starts the competitor-intelligence dashboard and worker.
By default also starts SearXNG (8080) and RSSHub (1200).

Options:
  --docker         Stop, rebuild, and start the Docker Compose services (default).
  --local          Run the dashboard and worker with Python; still starts
                   SearXNG/RSSHub in Docker when available.
  --cached         Allow Docker to reuse build cache.
  --no-worker      Start only the dashboard server in local mode.
  --no-discovery   Skip SearXNG and RSSHub.
  -h, --help       Show this help.

Examples:
  ./run.sh
  ./run.sh --local
  ./run.sh --docker
  ./run.sh --docker --cached
  ./run.sh --local --no-discovery
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
  local attempts="${3:-30}"
  local i
  for ((i = 1; i <= attempts; i++)); do
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

require_docker() {
  command -v docker >/dev/null 2>&1 || {
    log "Docker is required."
    exit 1
  }
  docker compose version >/dev/null 2>&1 || {
    log "Docker Compose is required."
    exit 1
  }
}

warn_empty_feeds() {
  if [[ ! -f "$FEEDS_PATH" ]]; then
    log "No config/feeds.json yet; RSSHub will stay idle until feeds are added."
    return
  fi
  if python3 - "$FEEDS_PATH" <<'PY' 2>/dev/null
import json, sys
path = sys.argv[1]
raw = json.loads(open(path, encoding="utf-8").read())
raise SystemExit(0 if isinstance(raw, list) and any(isinstance(i, dict) and i.get("url") for i in raw) else 1)
PY
  then
    return
  fi
  log "config/feeds.json has no feed URLs yet; RSSHub is up but nothing will be polled."
  log "Add entries with competitor_id + url, then POST /api/poll-feeds or wait for the worker."
}

start_discovery_services() {
  local searxng_url="$1"
  if [[ "$START_DISCOVERY" != 1 ]]; then
    log "Skipping SearXNG and RSSHub (--no-discovery)."
    return 0
  fi
  if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    log "Docker is unavailable; SearXNG and RSSHub were not started."
    return 0
  fi

  log "Starting SearXNG and RSSHub."
  "${COMPOSE[@]}" up -d searxng rsshub
  if ! wait_for_url "http://127.0.0.1:8080/" "SearXNG" 45; then
    "${COMPOSE[@]}" logs --tail=40 searxng || true
    log "Continuing without a healthy SearXNG."
  else
    export SEARXNG_URL="${SEARXNG_URL:-$searxng_url}"
    log "SEARXNG_URL=${SEARXNG_URL}"
  fi
  if ! wait_for_url "http://127.0.0.1:1200/" "RSSHub" 45; then
    "${COMPOSE[@]}" logs --tail=40 rsshub || true
    log "Continuing without a healthy RSSHub."
  fi
  warn_empty_feeds
}

start_local() {
  check_python
  start_discovery_services "http://127.0.0.1:8080"
  load_local_changedetection_key
  if [[ -n "${CHANGEDETECTION_API_KEY:-}" && -z "${CHANGEDETECTION_API_URL:-}" ]]; then
    export CHANGEDETECTION_API_URL=http://127.0.0.1:5001
  fi
  if [[ -z "${SEARXNG_URL:-}" && "$START_DISCOVERY" == 1 ]]; then
    export SEARXNG_URL=http://127.0.0.1:8080
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
  log "SearXNG http://127.0.0.1:8080 · RSSHub http://127.0.0.1:1200 · changedetection http://127.0.0.1:5001"
  log "Press Ctrl-C to stop the dashboard and worker (Docker collectors keep running)."
  log "Worker log: $WORKER_LOG"
  python3 -m competitor_intelligence serve --host "$HOST" --port "$PORT"
}

start_docker() {
  require_docker

  stop_local_processes
  if [[ "$START_DISCOVERY" == 1 ]]; then
    # Inside Compose, Intelligence must reach SearXNG by service name.
    export SEARXNG_URL=http://searxng:8080
  fi
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
  start_discovery_services "http://searxng:8080"
  load_local_changedetection_key
  log "Starting intelligence and collector worker."
  # Re-assert after discovery start so compose interpolation cannot pick up a
  # localhost value from the developer shell or root .env.
  if [[ "$START_DISCOVERY" == 1 ]]; then
    export SEARXNG_URL=http://searxng:8080
  fi
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
  log "Dashboard http://127.0.0.1:${PORT} · SearXNG http://127.0.0.1:8080 · RSSHub http://127.0.0.1:1200 · changedetection http://127.0.0.1:5001"
  if [[ -n "${SEARXNG_URL:-}" ]]; then
    log "Intelligence container SEARXNG_URL=${SEARXNG_URL}"
  fi
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
    --no-discovery)
      START_DISCOVERY=0
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
