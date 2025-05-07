FROM caddy:2.8-alpine

LABEL project=pytesseract

RUN apk --no-cache add curl

COPY Caddyfile /etc/caddy/Caddyfile