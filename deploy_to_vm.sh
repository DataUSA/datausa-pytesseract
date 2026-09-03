#!/bin/bash

export $(cat .env.gcp | xargs)

#echo "Docker Login"
#cat ./serviceAccountKey.json | base64 -d -w 0 | docker login -u _json_key --password-stdin https://${GCP_ARTIFACT_REGISTRY_LOCATION}-docker.pkg.dev

echo "Authenticate to gcloud"
gcloud auth activate-service-account --key-file=<(cat ./serviceAccountKey.json | base64 -d)

echo "Configure Docker to use gcloud as credential helper"
gcloud auth configure-docker ${GCP_ARTIFACT_REGISTRY_LOCATION}-docker.pkg.dev --quiet

echo "Compose pull"
docker compose --env-file .env.gcp pull

echo "Compose down"
docker compose down

echo "Compose up"
docker compose --env-file .env.gcp up -d

docker image prune -af --filter="label=project=pytesseract"