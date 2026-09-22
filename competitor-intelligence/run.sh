#!/usr/bin/env bash

set -Eeuo pipefail

MODULE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$MODULE_DIR"
COMPOSE=(docker compose --profile discovery --profile social)
if [[ -f "$MODULE_DIR/../.env" ]]; then
  COMPOSE=(docker compose --env-file "$MODULE_DIR/../.env" --profile discovery --profile social)
fi

MODE="docker"
# Reusing layers prevents every restart from leaving another 1.5 GB
# changedetection image behind. Use --no-cache only when deliberately forcing a
# clean image rebuild.
NO_CACHE=0
START_WORKER=1
START_DISCOVERY=1
DO_STOP=0
PORT="${INTEL_PORT:-8787}"
HOST="${INTEL_HOST:-127.0.0.1}"
RUN_DIR="$MODULE_DIR/.run"
SERVER_PID_FILE="$RUN_DIR/server.pid"
WORKER_PID_FILE="$RUN_DIR/worker.pid"
WORKER_LOG="$RUN_DIR/worker.log"
CLEANUP_SCRIPT="$MODULE_DIR/scripts/cleanup-docker.sh"
CLEANUP_PID_FILE="$RUN_DIR/cleanup.pid"
CLEANUP_LOG="$RUN_DIR/cleanup.log"
FEEDS_PATH="$MODULE_DIR/config/feeds.json"

log() {
  printf '[competitor-intelligence] %s\n' "$*"
}

usage() {
  cat <<'EOF'
Usage: ./run.sh [options]

Starts the competitor-intelligence dashboard and worker.
By default also starts SearXNG (8080) and RSSHub (1200).
Ctrl-C (or --stop) shuts everything down and clears runtime junk.

Options:
  --docker         Stop, rebuild, and start the Docker Compose services (default).
  --local          Run the dashboard and worker with Python; still starts
                   SearXNG/RSSHub in Docker when available.
  --stop           Stop local processes and Compose services, then exit.
  --cached         Allow Docker to reuse build cache (default).
  --no-cache       Rebuild Docker images without using the build cache.
  --no-worker      Start only the dashboard server in local mode.
  --no-discovery   Skip SearXNG and RSSHub.
  -h, --help       Show this help.

Examples:
  ./run.sh
  ./run.sh --local
  ./run.sh --stop
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
    done < <(pgrep -f 'python(3)? -m competitor_intelligence (worker|serve)' 2>/dev/null || true)
  fi
}

clear_runtime_junk() {
  log "Clearing runtime pid/log junk."
  mkdir -p -- "$RUN_DIR"
  rm -f -- \
    "$SERVER_PID_FILE" \
    "$WORKER_PID_FILE" \
    "$CLEANUP_PID_FILE" \
    "$WORKER_LOG" \
    "$CLEANUP_LOG"
  rm -rf -- "$RUN_DIR/cleanup.lock" "$MODULE_DIR/.pytest_cache"
  clear_local_builds
}

stop_compose_services() {
  if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    return 0
  fi
  log "Stopping Compose services (volumes and watch history kept)."
  "${COMPOSE[@]}" down --remove-orphans || true
}

run_project_image_cleanup() {
  [[ -x "$CLEANUP_SCRIPT" ]] || return 0
  if ! command -v docker >/dev/null 2>&1; then
    return 0
  fi
  log "Removing dangling project Docker images."
  "$CLEANUP_SCRIPT" --once || true
}

shutdown_all() {
  log "Shutting down competitor-intelligence."
  stop_cleanup_scheduler
  stop_local_processes
  stop_compose_services
  run_project_image_cleanup
  clear_runtime_junk
  log "Shutdown complete."
}

start_cleanup_scheduler() {
  [[ -x "$CLEANUP_SCRIPT" ]] || {
    log "Cleanup script is unavailable; skipping the periodic cleanup scheduler."
    return 0
  }
  local interval="${CLEANUP_INTERVAL_SECONDS:-21600}"
  [[ "$interval" =~ ^[0-9]+$ ]] || {
    log "Invalid CLEANUP_INTERVAL_SECONDS=$interval; using 21600 seconds."
    interval=21600
  }
  if [[ "$interval" == "0" ]]; then
    stop_cleanup_scheduler
    log "Periodic Docker cleanup disabled (CLEANUP_INTERVAL_SECONDS=0)."
    return 0
  fi

  if [[ -f "$CLEANUP_PID_FILE" ]]; then
    local existing_pid
    existing_pid="$(<"$CLEANUP_PID_FILE")"
    if [[ "$existing_pid" =~ ^[0-9]+$ ]] && kill -0 "$existing_pid" 2>/dev/null; then
      local existing_command
      existing_command="$(process_command "$existing_pid")"
      if [[ "$existing_command" == *"$CLEANUP_SCRIPT --daemon"* ]]; then
        log "Periodic cleanup scheduler already running (pid $existing_pid)."
        return 0
      fi
    fi
    rm -f -- "$CLEANUP_PID_FILE"
  fi

  mkdir -p -- "$RUN_DIR"
  log "Starting periodic Docker cleanup every ${interval}s."
  nohup env CLEANUP_INTERVAL_SECONDS="$interval" "$CLEANUP_SCRIPT" --daemon \
    >"$CLEANUP_LOG" 2>&1 < /dev/null &
  echo "$!" > "$CLEANUP_PID_FILE"
}

stop_cleanup_scheduler() {
  [[ -f "$CLEANUP_PID_FILE" ]] || return 0
  local existing_pid
  existing_pid="$(<"$CLEANUP_PID_FILE")"
  if [[ "$existing_pid" =~ ^[0-9]+$ ]] && kill -0 "$existing_pid" 2>/dev/null; then
    local existing_command
    existing_command="$(process_command "$existing_pid")"
    if [[ "$existing_command" == *"$CLEANUP_SCRIPT --daemon"* ]]; then
      log "Stopping periodic Docker cleanup scheduler (pid $existing_pid)."
      kill "$existing_pid" 2>/dev/null || true
      for _ in 1 2 3 4 5; do
        kill -0 "$existing_pid" 2>/dev/null || break
        sleep 1
      done
      if kill -0 "$existing_pid" 2>/dev/null; then
        log "Cleanup scheduler did not stop gracefully; terminating it."
        kill -KILL "$existing_pid" 2>/dev/null || true
      fi
    else
      log "Leaving unrelated process $existing_pid running; removing stale cleanup pid file."
    fi
  fi
  rm -f -- "$CLEANUP_PID_FILE"
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
    return 0
  fi
  if ! command -v docker >/dev/null 2>&1; then
    return 0
  fi
  local token
  if ! token="$("${COMPOSE[@]}" exec -T changedetection python -c 'import json; print(json.load(open("/datastore/changedetection.json"))["settings"]["application"]["api_access_token"])' 2>/dev/null)"; then
    log "Changedetection is unavailable; continuing without its local API credential."
    return 0
  fi
  [[ -n "$token" ]] || return 0
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

  log "Starting SearXNG, RSSHub, and RSSHub Redis."
  "${COMPOSE[@]}" up -d searxng rsshub-redis rsshub
  if ! wait_for_url "http://127.0.0.1:8080/" "SearXNG" 45; then
    "${COMPOSE[@]}" logs --tail=40 searxng || true
    log "Continuing without a healthy SearXNG."
  else
    export SEARXNG_URL="${SEARXNG_URL:-$searxng_url}"
    log "SEARXNG_URL=${SEARXNG_URL}"
  fi
  if ! wait_for_url "http://127.0.0.1:1200/healthz" "RSSHub" 60; then
    "${COMPOSE[@]}" logs --tail=40 rsshub || true
    log "Continuing without a healthy RSSHub."
  fi
  warn_empty_feeds
}

start_changedetection_services() {
  local required="${1:-0}"
  if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    log "Docker is unavailable; changedetection was not started."
    [[ "$required" == 1 ]] && return 1
    return 0
  fi

  log "Starting changedetection (and browser-chrome)."
  "${COMPOSE[@]}" up -d changedetection
  if ! wait_for_url "http://127.0.0.1:5001/" "changedetection UI"; then
    "${COMPOSE[@]}" logs --tail=50 changedetection || true
    if [[ "$required" == 1 ]]; then
      return 1
    fi
    log "Continuing without a healthy changedetection UI on :5001."
    return 0
  fi
}

start_local() {
  check_python
  # Bring collectors back up after a previous --stop / Ctrl-C shutdown.
  start_changedetection_services 0 || true
  start_discovery_services "http://127.0.0.1:8080"
  load_local_changedetection_key
  if [[ -n "${CHANGEDETECTION_API_KEY:-}" && -z "${CHANGEDETECTION_API_URL:-}" ]]; then
    export CHANGEDETECTION_API_URL=http://127.0.0.1:5001
  fi
  # Let changedetection containers reach the host Python dashboard for webhooks.
  export INTEL_WEBHOOK_HOST="${INTEL_WEBHOOK_HOST:-host.docker.internal:${PORT}}"
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
    # Avoid running shutdown twice when INT/TERM already triggered exit.
    trap - EXIT INT TERM
    if [[ -n "$worker_pid" ]]; then
      stop_pid "$worker_pid"
      worker_pid=""
    fi
    shutdown_all
  }
  trap cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM

  log "Dashboard is running at http://127.0.0.1:${PORT}"
  log "SearXNG http://127.0.0.1:8080 · RSSHub http://127.0.0.1:1200 · changedetection http://127.0.0.1:5001"
  log "Press Ctrl-C to stop everything (Python + Compose collectors) and clear runtime junk."
  log "Worker log: $WORKER_LOG"
  start_cleanup_scheduler
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
  start_changedetection_services 1 || exit 1
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
  start_cleanup_scheduler
  log "Press Ctrl-C to stop everything and clear runtime junk."
  trap 'trap - EXIT INT TERM; shutdown_all; exit 130' INT
  trap 'trap - EXIT INT TERM; shutdown_all; exit 143' TERM
  trap 'trap - EXIT INT TERM; shutdown_all' EXIT
  # Keep the foreground shell attached so Ctrl-C can tear the stack down.
  while true; do
    sleep 3600
  done
}

while (($# > 0)); do
  case "$1" in
    --local)
      MODE="local"
      ;;
    --docker)
      MODE="docker"
      ;;
    --stop)
      DO_STOP=1
      ;;
    --cached)
      NO_CACHE=0
      ;;
    --no-cache)
      NO_CACHE=1
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

if [[ "$DO_STOP" == 1 ]]; then
  shutdown_all
  exit 0
fi

if [[ "$MODE" == "docker" ]]; then
  start_docker
else
  start_local
fi
