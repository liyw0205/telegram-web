#!/bin/sh
set -eu

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

print_cmd_status() {
  name="$1"
  if has_cmd "$name"; then
    printf 'found: %s -> %s\n' "$name" "$(command -v "$name")"
  else
    printf 'missing: %s\n' "$name"
  fi
}

printf 'Browser smoke environment check\n'
printf '\nRuntime commands:\n'
for cmd in node npm npx; do
  print_cmd_status "$cmd"
done

printf '\nPlaywright:\n'
playwright_available=0
if has_cmd node && node -e "require('playwright')" >/dev/null 2>&1; then
  playwright_available=1
  printf 'found: playwright node module\n'
else
  printf 'missing: playwright node module\n'
fi

printf '\nBrowser commands:\n'
browser_available=0
for browser in chromium chromium-browser google-chrome google-chrome-stable firefox; do
  if has_cmd "$browser"; then
    browser_available=1
  fi
  print_cmd_status "$browser"
done

printf '\nResult:\n'
if [ "$playwright_available" -eq 1 ] && [ "$browser_available" -eq 1 ]; then
  printf 'automated browser smoke appears possible in this shell.\n'
else
  printf 'automated browser smoke is not ready in this shell; use docs/browser-smoke.md for manual checks.\n'
fi
