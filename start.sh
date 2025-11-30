#!/bin/bash
# Start script for Render deployment
# Runs database migrations and starts the server

set -e

# Run migrations (skip if database not available)
uv run alembic upgrade head || echo "Migrations skipped"

# Start the server
# Render provides PORT environment variable
PORT=${PORT:-8000}
exec uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT

