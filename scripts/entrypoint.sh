#!/bin/bash
set -e

# Entrypoint script for Docker container
# Handles port substitution and process startup

# Set PORT from environment, default to 8080
PORT=${PORT:-8080}
echo "🚀 Starting Benchmark-Tavily on port $PORT"

# Create nginx config with PORT substitution
mkdir -p /tmp/nginx
export PORT
envsubst '${PORT}' < /etc/nginx/nginx.conf.template > /tmp/nginx/nginx.conf

# Start nginx in the background
echo "🌐 Starting nginx..."
nginx -c /tmp/nginx/nginx.conf -g 'daemon off;' &
NGINX_PID=$!
echo "👉 App will be at http://localhost:$PORT (port 8000 is internal-only, not published)"

# Start FastAPI/uvicorn on loopback (only accessible via nginx)
echo "⚙️  Starting FastAPI..."
cd /app

# Enable Python virtual environment
source .venv/bin/activate 2>/dev/null || true

# Ensure PATH includes .venv/bin
export PATH="/app/.venv/bin:$PATH"

# Start uvicorn
exec python -m uvicorn \
    api.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --log-level info &

UVICORN_PID=$!

# Handle signals for graceful shutdown
trap 'kill -TERM $NGINX_PID $UVICORN_PID 2>/dev/null' TERM
trap 'kill -TERM $NGINX_PID $UVICORN_PID 2>/dev/null' INT

# Wait for both processes
wait
