#!/bin/sh
# Health check script for Docker
# Uses PORT env var or defaults to 8000

PORT=${PORT:-8000}
curl -f http://localhost:${PORT}/health || exit 1

