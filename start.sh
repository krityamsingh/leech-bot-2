#!/bin/bash

# Use the venv python from the base image if available, fallback to system python
PYTHON_BIN="/wzvenv/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python"
fi

if [ "${RUN_UPDATE_ON_START:-false}" = "true" ]; then
    $PYTHON_BIN update.py
fi

exec $PYTHON_BIN -m bot
