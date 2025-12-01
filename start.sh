#!/bin/bash
# Start script for Render deployment
# Runs database migrations and starts the server

set -e

# Activate uv environment
export PATH="/app/.venv/bin:$PATH"

# Run migrations (skip if database not available, but log the error)
echo "Running database migrations..."
uv run alembic upgrade head || {
    echo "WARNING: Migrations failed or database not available. Continuing anyway..."
}

# Start the server
# Render provides PORT environment variable
PORT=${PORT:-8000}
echo "Starting server on port $PORT..."

# Use exec to replace shell process with uvicorn
exec uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1

