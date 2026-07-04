#!/bin/sh
set -u

failures=0
warnings=0

ok() {
  printf 'ok: %s\n' "$1"
}

warn() {
  warnings=$((warnings + 1))
  printf 'warn: %s\n' "$1"
}

fail() {
  failures=$((failures + 1))
  printf 'fail: %s\n' "$1"
}

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

check_cmd() {
  name="$1"
  if has_cmd "$name"; then
    ok "$name -> $(command -v "$name")"
    return 0
  fi
  fail "$name command is missing"
  return 1
}

is_loopback_host() {
  case "$(printf '%s' "$1" | tr 'A-Z' 'a-z')" in
    127.0.0.1|localhost|::1) return 0 ;;
    *) return 1 ;;
  esac
}

check_token_shape() {
  token="$1"
  if [ -z "$token" ]; then
    return 0
  fi
  len=${#token}
  if [ "$len" -lt 8 ] || [ "$len" -gt 256 ]; then
    fail "configured Web Token environment value must be 8..256 characters"
    return 0
  fi
  case "$token" in
    *[[:space:]]*) fail "configured Web Token environment value must not contain whitespace" ;;
    *) ok "Web Token environment value is present and shape is valid" ;;
  esac
}

printf 'Telegram Web runtime diagnostics\n'
printf 'Repository: %s\n\n' "$(pwd)"

printf 'Required files:\n'
for path in app.py requirements.txt templates static scripts/run-termux.sh; do
  if [ -e "$path" ]; then
    ok "$path exists"
  else
    fail "$path is missing"
  fi
done

printf '\nCommands:\n'
check_cmd python || true
if has_cmd node; then
  ok "node -> $(command -v node)"
else
  warn "node command is missing; frontend smoke checks cannot run"
fi

printf '\nEnvironment:\n'
host="${TELEGRAM_WEB_HOST:-${HOST:-127.0.0.1}}"
port="${TELEGRAM_WEB_PORT:-${PORT:-5000}}"
printf 'info: effective host is %s\n' "$host"
printf 'info: effective port is %s\n' "$port"

case "$port" in
  ''|*[!0-9]*) fail "port must be a number" ;;
  *)
    if [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
      fail "port must be in 1..65535"
    else
      ok "port value is valid"
    fi
    ;;
esac

env_token="${TELEGRAM_WEB_TOKEN:-${WEB_TELEGRAM_TOKEN:-}}"
check_token_shape "$env_token"
if is_loopback_host "$host"; then
  ok "loopback bind does not require Web Token"
elif [ -n "$env_token" ]; then
  ok "non-loopback bind has Web Token from environment"
else
  warn "non-loopback bind has no Web Token in environment; data/config.json is not inspected by this script"
fi

printf '\nPython:\n'
if has_cmd python; then
  pycache_prefix="${PYTHONPYCACHEPREFIX:-${TMPDIR:-$HOME/.cache}/telegram-web-pycache}"
  if PYTHONPYCACHEPREFIX="$pycache_prefix" python -m py_compile app.py >/dev/null 2>&1; then
    ok "app.py compiles"
  else
    fail "app.py compile failed"
  fi

  if python - <<'PY'
import importlib

modules = [
    "flask",
    "flask_socketio",
    "telethon",
    "socks",
    "socketio",
]
missing = []
for name in modules:
    try:
        importlib.import_module(name)
    except Exception as exc:
        missing.append(f"{name} ({exc})")
if missing:
    print("missing Python modules: " + ", ".join(missing))
    raise SystemExit(1)
PY
  then
    ok "Python runtime dependencies import"
  else
    fail "Python runtime dependency import failed"
  fi
fi

printf '\nFrontend:\n'
if has_cmd node; then
  if node --check static/js/app.js >/dev/null 2>&1; then
    ok "static/js/app.js syntax is valid"
  else
    fail "static/js/app.js syntax check failed"
  fi
  if node --check tests/frontend_smoke.js >/dev/null 2>&1; then
    ok "tests/frontend_smoke.js syntax is valid"
  else
    fail "tests/frontend_smoke.js syntax check failed"
  fi
fi

printf '\nSummary:\n'
if [ "$failures" -gt 0 ]; then
  printf 'failures=%s warnings=%s\n' "$failures" "$warnings"
  exit 1
fi
printf 'failures=0 warnings=%s\n' "$warnings"
exit 0
