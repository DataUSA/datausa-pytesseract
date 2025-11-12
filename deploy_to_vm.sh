#!/bin/bash

export $(cat .env.gcp | xargs)

echo "Compose pull"
docker compose --env-file .env.gcp pull

echo "Compose down"
docker compose down

echo "Compose up"
docker compose --env-file .env.gcp up -d

docker image prune -af --filter="label=project=pytesseract"