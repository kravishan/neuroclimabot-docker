# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required by some Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libgomp1 \
    poppler-utils \
    tesseract-ocr \
    libmagic1 \
    wget \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download spacy model if needed
RUN python -m spacy download en_core_web_sm || true

# Copy application code
COPY . .

# Create directory for SQLite database
RUN mkdir -p /app/data

# Make startup script executable
RUN chmod +x /app/start-server.sh

# Expose port
EXPOSE 8000

# Health check - using wget as curl is already installed
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || curl -f http://localhost:8000/ || exit 1

# Run the application using startup script that waits for Redis
CMD ["/app/start-server.sh"]
