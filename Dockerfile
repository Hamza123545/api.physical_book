# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files first (for better caching)
COPY pyproject.toml uv.lock* ./

# Install dependencies using uv
RUN uv sync --frozen || uv sync

# Copy application code
COPY . .

# Make start script executable
RUN chmod +x start.sh || true

# Expose port (Render will set PORT env var)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start the application using start script
CMD ["./start.sh"]

