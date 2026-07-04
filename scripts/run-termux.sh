#!/bin/sh
set -eu

export TELEGRAM_WEB_HOST="${TELEGRAM_WEB_HOST:-127.0.0.1}"
export TELEGRAM_WEB_PORT="${TELEGRAM_WEB_PORT:-5000}"
export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-${TMPDIR:-$HOME/.cache}/telegram-web-pycache}"

exec python app.py
