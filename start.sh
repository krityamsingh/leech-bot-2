#!/bin/bash
export PORT=${PORT:-80}

python3 update.py && python3 -m bot
