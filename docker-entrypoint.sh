#!/usr/bin/env bash
set -ex
WORKERS=${UVICORN_WORKERS:-1}  # Default to 1 if not set, for the cluster.
MAX_CONCURRENCY=${MAX_CONCURRENCY:-300}

#exec granian --interface asgi --host 0.0.0.0 --port 7777 --log-config ./etc/logging.json --respawn-failed-workers app:layer
exec uvicorn --workers $WORKERS --limit-concurrency $MAX_CONCURRENCY --host 0.0.0.0 --port 7777 --log-config ./etc/logging.json app:layer
