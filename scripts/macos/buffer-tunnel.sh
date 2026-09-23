#!/usr/bin/env bash

set -Eeuo pipefail

readonly API_PORT="8000"
readonly NGROK_DOMAIN="perceptually-homocentric-lindy.ngrok-free.dev"
readonly EXPECTED_BASE_URL="https://${NGROK_DOMAIN}"

if ! command -v ngrok >/dev/null 2>&1; then
  printf '[aura] ERROR: ngrok is required for Buffer media publishing.\n' >&2
  exit 1
fi
if ! command -v curl >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
  printf '[aura] ERROR: curl and python3 are required to validate the running AURA API.\n' >&2
  exit 1
fi

media_config="$(curl --fail --silent --show-error --max-time 5 \
  "http://127.0.0.1:${API_PORT}/api/media/config" 2>/dev/null || true)"
if [[ -z "$media_config" ]]; then
  printf '[aura] ERROR: AURA is not responding on http://127.0.0.1:%s. Start the API first.\n' "$API_PORT" >&2
  exit 1
fi
if ! printf '%s' "$media_config" | python3 -c '
import json
import sys

payload = json.load(sys.stdin)
expected = sys.argv[1]
if not payload.get("configured") or payload.get("base_url", "").rstrip("/") != expected:
    print(f"expected configured MEDIA_PUBLIC_BASE_URL={expected}; received {payload!r}", file=sys.stderr)
    raise SystemExit(1)
' "$EXPECTED_BASE_URL"; then
  printf '[aura] ERROR: set MEDIA_PUBLIC_BASE_URL=%s in the root .env and restart AURA.\n' "$EXPECTED_BASE_URL" >&2
  exit 1
fi

printf '[aura] Starting the Buffer media tunnel at https://%s -> http://localhost:%s\n' "$NGROK_DOMAIN" "$API_PORT"
printf '[aura] Keep this terminal running while Buffer is in use.\n'
exec ngrok http --url="$NGROK_DOMAIN" "$API_PORT"
