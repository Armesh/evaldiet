#!/usr/bin/env bash

# Go to the directory of this script
cd "$(dirname "$0")"

# Activate virtualenv (Git Bash version)
source ./.venv/Scripts/activate

# Run uvicorn with colors
uvicorn app.main:app \
  --reload \
  --host 127.0.0.1 \
  --port 8000 \
  --use-colors
