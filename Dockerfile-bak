# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
        git \
        pandoc \
        texlive-latex-base \
        texlive-latex-recommended \
        texlive-fonts-recommended \
        lmodern \
        vim \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        shared-mime-info \
        libcairo2 \
        libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir git+https://github.com/dfop02/html4docx.git@1.1.1

# Copy application code
COPY . .

# Create non-root user for security
RUN adduser --disabled-password --gecos '' --shell /bin/bash appuser \
    && chown -R appuser:appuser /app

# Expose port
EXPOSE 8000

# Make wait script executable
RUN chmod +x wait-for-db.py

# Switch to non-root user
USER appuser

# Run uvicorn with multiple workers for concurrent request handling
# --workers 4: Run with 4 worker processes for parallel request processing
# Each worker can handle requests independently, preventing blocking
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--timeout-graceful-shutdown", "200", "--timeout-keep-alive", "200"]