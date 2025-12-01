#!/bin/sh
# Health check script for Docker
# Uses PORT env var or defaults to 7860 (Hugging Face Spaces default)

PORT=${PORT:-7860}
# Try health endpoint, if it fails try root endpoint
curl -f http://localhost:${PORT}/health 2>/dev/null || curl -f http://localhost:${PORT}/ 2>/dev/null || exit 1

