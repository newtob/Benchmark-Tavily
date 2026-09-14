#!/usr/bin/env bash
# Starts uvicorn in the background, waits for it to answer /api/healthz,
# then execs nginx in the foreground as PID 1's final process. See
# specs/tavily-benchmark-app.md §8.
#
# nginx's external listen port comes from $PORT (default 8080 for local
# `docker run`) — Vercel's Container deployment mode assigns $PORT at
# runtime and expects the container to listen on exactly that port.
set -euo pipefail

# /etc/nginx isn't writable by the non-root appuser this container runs as,
# so the port-substituted config is written to /tmp instead of edited in
# place, and nginx is told to use that file explicitly.
NGINX_CONF=/tmp/nginx.conf
sed "s/__PORT__/${PORT:-8080}/" /etc/nginx/nginx.conf > "$NGINX_CONF"

uvicorn api.main:app --host 127.0.0.1 --port 8000 &
UVICORN_PID=$!

trap 'kill "$UVICORN_PID" 2>/dev/null' EXIT

for _ in $(seq 1 30); do
  if curl -sf -o /dev/null http://127.0.0.1:8000/api/healthz; then
    break
  fi
  sleep 1
done

if ! curl -sf -o /dev/null http://127.0.0.1:8000/api/healthz; then
  echo "uvicorn did not become healthy within 30s" >&2
  exit 1
fi

trap - EXIT
exec nginx -c "$NGINX_CONF" -g "daemon off;"
