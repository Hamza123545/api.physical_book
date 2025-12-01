# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files first (for better caching)
COPY pyproject.toml uv.lock* ./

# Install dependencies using uv
RUN uv sync --frozen || uv sync

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x start.sh healthcheck.sh

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (Hugging Face Spaces uses PORT env var, default 7860)
EXPOSE 7860

# Health check - uses healthcheck.sh which respects PORT env var
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ./healthcheck.sh

# Start the application
# Hugging Face Spaces can use either app.py or start.sh
# Using start.sh for consistency, but app.py is also available
CMD ["./start.sh"]

