#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_DIR="$ROOT_DIR/api"
WEB_DIR="$ROOT_DIR/web"
RUN_DIR="$ROOT_DIR/.aura/run"
LOG_DIR="$ROOT_DIR/.aura/logs"
LOCAL_UV_CACHE="$ROOT_DIR/.aura/uv-cache"
LOCAL_BUN_CACHE="$ROOT_DIR/.aura/bun-cache"
AURA_TMP_DIR="$ROOT_DIR/.aura/tmp"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
UV_CACHE_DIR="${UV_CACHE_DIR:-$LOCAL_UV_CACHE}"
BUN_INSTALL_CACHE_DIR="${BUN_INSTALL_CACHE_DIR:-$LOCAL_BUN_CACHE}"
TMPDIR="${AURA_TMPDIR:-$AURA_TMP_DIR}"
export TMPDIR

API_PID_FILE="$RUN_DIR/api.pid"
WEB_PID_FILE="$RUN_DIR/web.pid"
API_LOG="$LOG_DIR/api.log"
WEB_LOG="$LOG_DIR/web.log"

log() {
  printf '[aura] %s\n' "$*"
}

fail() {
  printf '[aura] ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing '$1'. Install it before running this command."
}

require_tools() {
  require_command uv
  require_command bun
  require_command curl
  require_command lsof
  require_command pgrep
}

ensure_layout() {
  mkdir -p "$RUN_DIR" "$LOG_DIR" "$TMPDIR"
}

clean_generated() {
  stop_stack
  log "Removing generated build and runner output only"

  rm -rf \
    "$WEB_DIR/.next" \
    "$WEB_DIR/tsconfig.tsbuildinfo" \
    "$RUN_DIR" \
    "$LOG_DIR" \
    "$AURA_TMP_DIR" \
    "$LOCAL_BUN_CACHE"

  find "$API_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} +
  find "$API_DIR" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

  if [[ "$UV_CACHE_DIR" == "$LOCAL_UV_CACHE" ]]; then
    rm -rf "$LOCAL_UV_CACHE"
  fi

  log "Preserved source, dependencies, env files, and database data"
}

read_pid() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] || return 1
  local pid
  pid="$(<"$pid_file")"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  printf '%s\n' "$pid"
}

process_command() {
  local pid="$1"
  ps -p "$pid" -o command= 2>/dev/null || true
}

capture_listener_pid() {
  local name="$1"
  local port="$2"
  local pid_file="$3"
  local pid

  pid="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -n 1 || true)"
  if [[ -n "$pid" ]]; then
    printf '%s\n' "$pid" > "$pid_file"
    log "Tracking $name listener (pid $pid)"
  fi
}

stop_process_tree() {
  local pid="$1"
  local child
  local children

  children="$(pgrep -P "$pid" 2>/dev/null || true)"
  for child in $children; do
    stop_process_tree "$child"
  done
  kill "$pid" 2>/dev/null || true
}

stop_tracked_process() {
  local name="$1"
  local pid_file="$2"
  local pid

  pid="$(read_pid "$pid_file" 2>/dev/null || true)"
  if [[ -z "$pid" ]]; then
    rm -f "$pid_file"
    return 0
  fi

  if ! kill -0 "$pid" 2>/dev/null; then
    rm -f "$pid_file"
    return 0
  fi

  log "Stopping $name (pid $pid)"
  stop_process_tree "$pid"
  for _ in {1..20}; do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.25
  done

  if kill -0 "$pid" 2>/dev/null; then
    log "$name did not stop cleanly; sending SIGKILL to pid $pid"
    kill -KILL "$pid" 2>/dev/null || true
  fi

  if kill -0 "$pid" 2>/dev/null; then
    log "Could not stop $name; keeping $pid_file for a later retry" >&2
    return 1
  fi
  rm -f "$pid_file"
}

stop_stack() {
  stop_tracked_process "frontend" "$WEB_PID_FILE" || true
  stop_tracked_process "backend" "$API_PID_FILE" || true
}

port_is_busy() {
  lsof -tiTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

assert_ports_free() {
  if port_is_busy "$API_PORT"; then
    fail "Port $API_PORT is already in use. Run './scripts/stop.sh' for AURA-owned processes or stop the other process manually."
  fi
  if port_is_busy "$WEB_PORT"; then
    fail "Port $WEB_PORT is already in use. Run './scripts/stop.sh' for AURA-owned processes or stop the other process manually."
  fi
}

ensure_env() {
  [[ -f "$ROOT_DIR/.env" ]] || fail "Missing .env. Copy .env.example to .env and set DATABASE_URL before starting AURA."

  if [[ ! -f "$WEB_DIR/.env.local" ]]; then
    log "Creating web/.env.local from the non-secret template"
    cp "$WEB_DIR/env.example.txt" "$WEB_DIR/.env.local"
  fi
}

build_backend() {
  log "Syncing backend environment"
  (cd "$API_DIR" && UV_CACHE_DIR="$UV_CACHE_DIR" uv sync --frozen)
  log "Compiling backend sources"
  (cd "$API_DIR" && UV_CACHE_DIR="$UV_CACHE_DIR" uv run python -m compileall main.py db.py schemas.py graph.py routes agents)
}

build_frontend() {
  log "Installing frontend lockfile dependencies"
  (cd "$WEB_DIR" && BUN_INSTALL_CACHE_DIR="$BUN_INSTALL_CACHE_DIR" bun install --frozen-lockfile)
  log "Running frontend typecheck"
  (cd "$WEB_DIR" && bun run typecheck)
  log "Building frontend"
  (cd "$WEB_DIR" && bun run build)
}

build_stack() {
  require_tools
  ensure_layout
  build_backend
  build_frontend
  log "Build completed"
}

ensure_production_build() {
  [[ -f "$WEB_DIR/.next/BUILD_ID" ]] || fail "No frontend production build found. Choose 'Build + run' or run './scripts/build.sh' first."
}

wait_for_http() {
  local name="$1"
  local url="$2"
  for _ in {1..60}; do
    if curl --silent --show-error --fail --max-time 10 "$url" >/dev/null 2>&1; then
      log "$name is ready at $url"
      return 0
    fi
    sleep 0.5
  done
  return 1
}

start_processes() {
  local frontend_mode="$1"
  require_tools
  ensure_env
  if [[ "$frontend_mode" == "production" ]]; then
    ensure_production_build
  fi
  ensure_layout
  stop_stack
  assert_ports_free

  : > "$API_LOG"
  : > "$WEB_LOG"

  log "Starting backend on http://localhost:$API_PORT"
  (
    cd "$API_DIR"
    exec env UV_CACHE_DIR="$UV_CACHE_DIR" \
      uv run uvicorn main:app --host "$API_HOST" --port "$API_PORT" \
      >>"$API_LOG" 2>&1
  ) &
  local api_pid=$!
  printf '%s\n' "$api_pid" > "$API_PID_FILE"

  log "Starting frontend on http://localhost:$WEB_PORT"
  (
    cd "$WEB_DIR"
    export PORT="$WEB_PORT"
    export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:$API_PORT}"
    if [[ "$frontend_mode" == "production" ]]; then
      exec bun run start
    else
      exec bun run dev
    fi
  ) >>"$WEB_LOG" 2>&1 &
  local web_pid=$!
  printf '%s\n' "$web_pid" > "$WEB_PID_FILE"

  if ! wait_for_http "backend" "http://localhost:$API_PORT/api/health"; then
    log "Backend failed to become ready. Recent log:"
    tail -n 40 "$API_LOG" >&2 || true
    stop_stack
    return 1
  fi
  capture_listener_pid "backend" "$API_PORT" "$API_PID_FILE"

  if ! wait_for_http "frontend" "http://localhost:$WEB_PORT/dashboard/overview"; then
    log "Frontend failed to become ready. Recent log:"
    tail -n 40 "$WEB_LOG" >&2 || true
    capture_listener_pid "frontend" "$WEB_PORT" "$WEB_PID_FILE"
    stop_stack
    return 1
  fi
  capture_listener_pid "frontend" "$WEB_PORT" "$WEB_PID_FILE"

  api_pid="$(read_pid "$API_PID_FILE" 2>/dev/null || printf '%s' "$api_pid")"
  web_pid="$(read_pid "$WEB_PID_FILE" 2>/dev/null || printf '%s' "$web_pid")"

  log "AURA is running. Logs: $API_LOG and $WEB_LOG"
  log "Press Ctrl-C to stop both processes"

  trap 'stop_stack; exit 0' INT TERM EXIT
  while kill -0 "$api_pid" 2>/dev/null && kill -0 "$web_pid" 2>/dev/null; do
    sleep 1
  done

  log "One process exited. Recent backend log:"
  tail -n 20 "$API_LOG" || true
  log "Recent frontend log:"
  tail -n 20 "$WEB_LOG" || true
  stop_stack
  trap - INT TERM EXIT
  return 1
}

usage() {
  cat <<'EOF'
Usage: ./scripts/aura.sh <command>

Commands:
  clean   Remove generated build output, Python caches, runner logs/PIDs, and local uv cache
  build   Clean generated output, install locked dependencies, typecheck, and build both apps
  start   Start FastAPI and the existing Next.js production build
  dev     Start FastAPI and Next.js in development mode with hot reload
  up      Clean, build, then start FastAPI and Next.js in production mode
  stop    Stop only AURA processes recorded by this runner
EOF
}

interactive_menu() {
  printf '\n'
  printf 'AURA launcher\n'
  printf '============\n'
  printf '1) Build only\n'
  printf '2) Build + run\n'
  printf '3) Just run\n'
  printf 'q) Exit\n\n'

  local choice
  read -r -p 'Choose an option [1-3/q]: ' choice
  case "$choice" in
    1)
      clean_generated
      build_stack
      ;;
    2)
      clean_generated
      build_stack
      start_processes "production"
      ;;
    3)
      start_processes "production"
      ;;
    q|Q|"")
      log "Nothing started"
      ;;
    *)
      fail "Unknown option '$choice'. Choose 1, 2, 3, or q."
      ;;
  esac
}

main() {
  local command="${1:-}"
  case "$command" in
    ""|menu)
      interactive_menu
      ;;
    clean)
      clean_generated
      ;;
    build)
      clean_generated
      build_stack
      ;;
    start)
      start_processes "production"
      ;;
    dev)
      start_processes "development"
      ;;
    up)
      clean_generated
      build_stack
      start_processes "production"
      ;;
    stop)
      stop_stack
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      usage >&2
      return 2
      ;;
  esac
}

main "$@"
