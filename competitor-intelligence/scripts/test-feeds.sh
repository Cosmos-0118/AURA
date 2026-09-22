#!/usr/bin/env bash
set -Eeuo pipefail

MODULE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
FEEDS_PATH="${1:-$MODULE_DIR/config/feeds.json}"

if [[ ! -f "$FEEDS_PATH" ]]; then
  printf 'Missing feeds file: %s\n' "$FEEDS_PATH" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  printf 'jq is required to run feed checks.\n' >&2
  exit 1
fi

failures=0
while IFS= read -r url; do
  [[ -n "$url" ]] || continue
  printf '\nTesting: %s\n' "$url"
  code="$(
    curl -L \
      --connect-timeout 15 \
      --max-time 90 \
      -s \
      -o /tmp/competitor-feed-test \
      -w '%{http_code}' \
      "$url" || true
  )"
  if [[ "$code" == "200" ]]; then
    printf 'OK HTTP %s\n' "$code"
  else
    printf 'FAIL HTTP %s\n' "$code"
    failures=$((failures + 1))
  fi
done < <(jq -r '.[].url' "$FEEDS_PATH")

printf '\nDone. Failures: %s\n' "$failures"
exit "$failures"
