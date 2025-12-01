#!/bin/bash
# Start script for Render deployment
# Runs database migrations and starts the server

set -e

# Activate uv environment
export PATH="/app/.venv/bin:$PATH"

# Set environment
export ENVIRONMENT=${ENVIRONMENT:-production}

# Log environment info
echo "=========================================="
echo "Starting Physical AI Backend"
echo "Environment: $ENVIRONMENT"
echo "Python: $(python --version)"
echo "=========================================="

# Wait for database to be ready (for Render)
echo "Waiting for database connection..."
sleep 3

# Test database connection before migrations
if [ -n "$DATABASE_URL" ]; then
    echo "Testing database connection..."
    timeout 10 python -c "
import os
from sqlalchemy import create_engine, text
try:
    engine = create_engine(os.getenv('DATABASE_URL'), connect_args={'connect_timeout': 5})
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('✓ Database connection successful')
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    exit(1)
" || {
        echo "WARNING: Database connection test failed. Continuing anyway..."
    }
fi

# Run migrations (skip if database not available, but log the error)
echo "Running database migrations..."
uv run alembic upgrade head || {
    echo "WARNING: Migrations failed or database not available. Continuing anyway..."
}

# Start the server
# Render provides PORT environment variable
PORT=${PORT:-8000}
echo "=========================================="
echo "Starting server on port $PORT..."
echo "=========================================="

# Use exec to replace shell process with uvicorn
# Add timeout settings for Render
# Increased timeouts to handle slow database connections
exec uv run uvicorn app.main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --workers 1 \
    --timeout-keep-alive 60 \
    --timeout-graceful-shutdown 30 \
    --limit-concurrency 1000 \
    --backlog 2048 \
    --log-level info

