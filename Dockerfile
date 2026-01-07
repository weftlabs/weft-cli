# Multi-stage build for efficient images

# Stage 1: Build
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN useradd -m -u 1000 aiworkflow && \
    mkdir -p /app /data/ai-history && \
    chown -R aiworkflow:aiworkflow /app /data

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=aiworkflow:aiworkflow . .

# Switch to non-root user
USER aiworkflow

# Default command (can be overridden)
CMD ["python", "-m", "pytest"]
