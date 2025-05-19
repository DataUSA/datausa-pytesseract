#!/usr/bin/env bash

WORKERS=${UVICORN_WORKERS:-1}  # Default to 1 if not set, for the cluster.
MAX_CONCURRENCY=${MAX_CONCURRENCY:-300}

# Check if TESSERACT_DEBUG_TOKEN is set; if not, generate it
if [ -z "$TESSERACT_DEBUG_TOKEN" ]; then
    export TESSERACT_DEBUG_TOKEN=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | cut -c1-32)
fi

echo $TESSERACT_DEBUG_TOKEN

exec uvicorn --workers $WORKERS --limit-concurrency $MAX_CONCURRENCY --host 0.0.0.0 --port 7777 --log-config ./etc/logging.json app:layer
