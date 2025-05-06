#!/bin/bash

route_traffic() {
echo "Routing traffic to $1"
case $1 in
    "blue")
        upstreams='[{"dial":"pytesseract-blue:7777"}]'
    ;;
    "green")
        upstreams='[{"dial":"pytesseract-green:7777"}]'
    ;;
esac

docker compose --env-file .env.gcp exec pytesseract-caddy curl \
    -H "Content-Type: application/json" \
    -d "$upstreams" \
    -X PATCH http://localhost:2019/config/apps/http/servers/srv0/routes/0/handle/0/routes/0/handle/0/upstreams
}

up() {
echo "Starting $1"
container="pytesseract-$1"
docker compose --env-file .env.gcp up -d "$container"
}

down() {
echo "Stopping $1"
container="pytesseract-$1"
docker compose --env-file .env.gcp down "$container"
}

wait_healthy() {
    echo "Waiting for $1 to be healthy..."
    container="pytesseract-$1"

    retries=15  # 9 minutes / 30s per retry
    for ((i=1; i<=retries; i++)); do
        status_code=$(docker compose --env-file .env.gcp exec "$container" \
            curl -o /dev/null -s -w "%{http_code}" http://localhost:7777/_health)

        if [[ "$status_code" == "204" ]]; then
            echo "$1 is healthy"
            return 0
        fi
        
        echo "Health check failed (HTTP $status_code). Retrying in 30 seconds... ($i/$retries)"
        sleep 30
    done

    echo "$1 failed to become healthy after 5 minutes!"
    return 1
}

# Pull the latest version and create the containers if they don't exist
echo "Pulling the latest version and creating the containers if they don't exist"
docker compose --env-file .env.gcp pull

echo "Compose up"
docker compose --env-file .env.gcp up -d --no-recreate pytesseract-blue pytesseract-caddy

echo "up green"
up green

echo "Wait healthy green"
if ! wait_healthy green ; then
down green
exit 1
fi

echo "Route traffic green"
route_traffic green

echo "Down Blue"
down blue
echo "Up Blue"
up blue
echo "Wait Healthy blue"
wait_healthy blue
echo "Route traffic blue"
route_traffic blue

echo "Down green"
down green

# # Clean old images with the 'project=pytesseract' label
docker image prune -af --filter="label=project=pytesseract"