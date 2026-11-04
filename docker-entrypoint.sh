#!/bin/sh
export TOKEN="${TOKEN:-$TELEGRAM_BOT_TOKEN}"
export OWNER_ID="${OWNER_ID:-${ADMIN_TELEGRAM_ID:-1560345442}}"
exec python addons.py
