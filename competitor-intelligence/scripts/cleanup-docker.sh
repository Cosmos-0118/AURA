#!/usr/bin/env bash

set -Eeuo pipefail

# Safe, project-scoped maintenance for the competitor-intelligence Compose
# stack. This script deliberately does not run `docker system prune`, remove
# volumes, or stop containers: snapshots and databases are user data.

MODULE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$MODULE_DIR"

COMPOSE=(docker compose --profile discovery --profile social)
if [[ -f "$MODULE_DIR/../.env" ]]; then
  COMPOSE=(docker compose --env-file "$MODULE_DIR/../.env" --profile discovery --profile social)
fi

RUN_DIR="$MODULE_DIR/.run"
LOCK_DIR="${CLEANUP_LOCK_DIR:-$RUN_DIR/cleanup.lock}"
LOCK_STALE_SECONDS="${CLEANUP_LOCK_STALE_SECONDS:-3600}"
CLEANUP_INTERVAL_SECONDS="${CLEANUP_INTERVAL_SECONDS:-21600}"
CLEANUP_MAX_IMAGE_PASSES="${CLEANUP_MAX_IMAGE_PASSES:-8}"
DRY_RUN="${CLEANUP_DRY_RUN:-0}"

log() {
  printf '[competitor-intelligence-cleanup] %s\n' "$*"
}

usage() {
  cat <<'EOF'
Usage: cleanup-docker.sh [--once|--daemon]

Removes only dangling images produced by this Compose project and asks the
browser proxy to sweep orphaned Chrome temp directories. It also recognizes
the older unlabelled AURA image fingerprints so the first pass can reclaim
space after upgrading this script. Volumes, active containers, tagged images,
and changedetection history are never removed.

Options:
  --once       Run one cleanup pass (default).
  --daemon     Run once, then repeat every CLEANUP_INTERVAL_SECONDS (6 hours).

Environment:
  CLEANUP_INTERVAL_SECONDS   Daemon interval; 0 disables the daemon.
  CLEANUP_MAX_IMAGE_PASSES   Maximum chained dangling-image passes (default 8).
  CLEANUP_DRY_RUN=1          Report targets without deleting anything.
  CLEANUP_LOCK_STALE_SECONDS Recover a lock abandoned for this many seconds.
EOF
}

require_docker() {
  command -v docker >/dev/null 2>&1 || {
    log "Docker is unavailable; skipping cleanup."
    return 1
  }
  docker compose version >/dev/null 2>&1 || {
    log "Docker Compose is unavailable; skipping cleanup."
    return 1
  }
}

validate_settings() {
  [[ "$LOCK_STALE_SECONDS" =~ ^[1-9][0-9]*$ ]] || {
    log "CLEANUP_LOCK_STALE_SECONDS must be a positive integer." >&2
    return 1
  }
  [[ "$CLEANUP_MAX_IMAGE_PASSES" =~ ^[1-9][0-9]*$ ]] || {
    log "CLEANUP_MAX_IMAGE_PASSES must be a positive integer." >&2
    return 1
  }
}

lock_age_seconds() {
  local modified
  case "$(uname -s)" in
    Darwin)
      modified="$(stat -f '%m' "$LOCK_DIR" 2>/dev/null || echo 0)"
      ;;
    *)
      modified="$(stat -c '%Y' "$LOCK_DIR" 2>/dev/null || echo 0)"
      ;;
  esac
  if [[ "$modified" =~ ^[0-9]+$ ]]; then
    echo $(( $(date +%s) - modified ))
  else
    echo "$LOCK_STALE_SECONDS"
  fi
}

lock_pid() {
  [[ -f "$LOCK_DIR/pid" ]] && cat "$LOCK_DIR/pid" || true
}

acquire_lock() {
  mkdir -p "$RUN_DIR"
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    printf '%s\n' "$$" > "$LOCK_DIR/pid"
    return 0
  fi

  local existing_pid
  existing_pid="$(lock_pid)"
  if [[ "$existing_pid" =~ ^[0-9]+$ ]] && kill -0 "$existing_pid" 2>/dev/null; then
    log "Another cleanup pass is already running (pid $existing_pid); skipping."
    return 1
  fi
  if (( $(lock_age_seconds) < LOCK_STALE_SECONDS )); then
    log "A cleanup lock exists but its owner is unknown; skipping safely."
    return 1
  fi

  log "Removing stale cleanup lock older than ${LOCK_STALE_SECONDS}s."
  rm -f "$LOCK_DIR/pid"
  rmdir "$LOCK_DIR" 2>/dev/null || {
    log "Could not reclaim the stale cleanup lock; skipping."
    return 1
  }
  mkdir "$LOCK_DIR"
  printf '%s\n' "$$" > "$LOCK_DIR/pid"
}

release_lock() {
  rm -f "$LOCK_DIR/pid"
  rmdir "$LOCK_DIR" 2>/dev/null || true
}

sweep_browser_temp() {
  local container_id
  container_id="$("${COMPOSE[@]}" ps -q browser-chrome 2>/dev/null | head -n 1)"
  if [[ -z "$container_id" ]]; then
    log "browser-chrome is not running; no browser temp sweep needed."
    return 0
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY RUN: would sweep orphaned Chrome temp directories in browser-chrome."
    return 0
  fi

  local result
  result="$(
    "${COMPOSE[@]}" exec -T browser-chrome /usr/src/app/bin/python -c \
      'from chrome import sweep_orphans; print(sweep_orphans(min_age=300))' 2>&1
  )" || {
    log "Browser temp sweep skipped: $result"
    return 0
  }
  log "Browser temp sweep: ${result//$'\n'/ }"
}

prune_project_images() {
  local remaining_passes="${1:-1}"
  local image_id labels history
  local image_ids=()
  while IFS= read -r image_id; do
    [[ -n "$image_id" ]] || continue
    labels="$(docker image inspect --format '{{json .Config.Labels}}' "$image_id" 2>/dev/null || echo '{}')"
    case "$labels" in
      *'"com.jaassure.cleanup":"competitor-intelligence"'*)
        image_ids+=("$image_id")
        ;;
      *)
        # Before the cleanup label was added, these images were untagged by
        # repeated no-cache builds. Match immutable Dockerfile fingerprints,
        # never a generic <none> image, so unrelated projects are skipped.
        history="$(docker image history --no-trunc --format '{{.CreatedBy}}' "$image_id" 2>/dev/null || true)"
        if [[ "$history" == *"/app/changedetectionio/conditions/plugins/aura_row_layout_plugin.py"* \
           && "$history" == *"/app/changedetectionio/conditions/plugins/static/row-layout.css"* ]] \
           || [[ "$history" == *"in ./competitor_intelligence"* \
           && "$history" == *"in ./config"* ]]; then
          image_ids+=("$image_id")
        fi
        ;;
    esac
  done < <(docker image ls --quiet --filter dangling=true | sort -u)

  if ((${#image_ids[@]} == 0)); then
    log "No dangling project images to remove."
    return 0
  fi

  log "Found ${#image_ids[@]} dangling project image(s): ${image_ids[*]}"
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY RUN: leaving images untouched."
    return 0
  fi
  local removed=0
  for image_id in "${image_ids[@]}"; do
    if docker image rm "$image_id" >/dev/null 2>&1; then
      removed=$((removed + 1))
    else
      log "Skipped image $image_id because Docker still reports it in use."
    fi
  done
  log "Removed $removed dangling project image(s); kept $(( ${#image_ids[@]} - removed )) in-use image(s)."
  if (( removed > 0 && remaining_passes > 1 )); then
    prune_project_images "$((remaining_passes - 1))"
  fi
}

run_once() (
  require_docker || exit 0
  validate_settings || exit 2
  acquire_lock || exit 0
  trap release_lock EXIT INT TERM

  sweep_browser_temp
  prune_project_images "$CLEANUP_MAX_IMAGE_PASSES"
  log "Cleanup pass complete. Volumes and active data were preserved."
)

case "${1:---once}" in
  --once)
    run_once
    ;;
  --daemon)
    if [[ "$CLEANUP_INTERVAL_SECONDS" == "0" ]]; then
      log "CLEANUP_INTERVAL_SECONDS=0; daemon disabled."
      exit 0
    fi
    [[ "$CLEANUP_INTERVAL_SECONDS" =~ ^[1-9][0-9]*$ ]] || {
      log "CLEANUP_INTERVAL_SECONDS must be a positive integer or 0." >&2
      exit 2
    }
    while true; do
      run_once
      sleep "$CLEANUP_INTERVAL_SECONDS"
    done
    ;;
  -h|--help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
