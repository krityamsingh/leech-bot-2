#!/bin/bash
set -e

# Use the venv python from the base image if available, fallback to system python
PYTHON_BIN="/wzvenv/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python"
fi

if [ "${RUN_UPDATE_ON_START:-false}" = "true" ]; then
    $PYTHON_BIN update.py || true
fi

# ── Optional: launch PHP MadelineProto bridge in the background ──────────────
# It only starts if:
#   1. USE_PHP_TRANSPORT is enabled in config.py
#   2. php-bridge/data/session.madeline exists (created by `php login.php` once)
# Otherwise the Python bot just runs alone and uses Kurigram HyperUP/HyperDL.
PHP_SESSION="/usr/src/app/php-bridge/data/session.madeline"
USE_PHP=$($PYTHON_BIN -c "import sys; sys.path.insert(0, '/usr/src/app'); \
import config; print('1' if getattr(config, 'USE_PHP_TRANSPORT', False) else '0')" 2>/dev/null || echo "0")

if [ "$USE_PHP" = "1" ] && [ -f "$PHP_SESSION" ]; then
    echo "[start.sh] USE_PHP_TRANSPORT=True and session found — launching php-bridge"
    (cd /usr/src/app/php-bridge && php server.php) &
    PHP_PID=$!
    echo "[start.sh] php-bridge PID=$PHP_PID"

    cleanup() {
        echo "[start.sh] Shutting down"
        if kill -0 $PHP_PID 2>/dev/null; then kill -TERM $PHP_PID; fi
    }
    trap cleanup EXIT INT TERM
elif [ "$USE_PHP" = "1" ]; then
    echo "[start.sh] USE_PHP_TRANSPORT=True but $PHP_SESSION missing."
    echo "[start.sh] Open a Railway shell and run:"
    echo "           cd /usr/src/app/php-bridge && php login.php"
    echo "[start.sh] Continuing with Kurigram-only (Python) transport."
fi

# ── Always start the main Python bot ─────────────────────────────────────────
exec $PYTHON_BIN -m bot
