#!/bin/bash
export PORT=${PORT:-80}

if [ -f credentials.env ]; then
  set -a
  source credentials.env
  set +a
fi

python3 update.py && python3 -m bot
