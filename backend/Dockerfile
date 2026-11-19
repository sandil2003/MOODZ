# ============================================
# Dockerfile for MOODZ Backend - Hugging Face Spaces
# ============================================

# ============================================
# Stage 1: Builder
# ============================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make libpq-dev && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Copy requirements
COPY requirements.txt .

# Install Python dependencies in virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# ============================================
# Stage 2: Runtime (Optimized for Hugging Face)
# ============================================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    HOME=/home/user

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client curl && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create user with UID 1000 (Hugging Face standard)
RUN useradd -m -u 1000 user && \
    mkdir -p /app/logs && \
    chown -R user:user /app

# Copy application code
COPY --chown=user:user . .

# Switch to non-root user
USER user

# Expose port 7860 (Hugging Face Spaces default)
EXPOSE 7860

# Run the application on port 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
