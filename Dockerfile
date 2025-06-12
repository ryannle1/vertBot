# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies (for matplotlib, pandas, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libfreetype6-dev \
        libpng-dev \
        libopenblas-dev \
        liblapack-dev \
        git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt || pip install -r requirement.txt

# Expose port if needed (not required for Discord bots, but useful for health checks)
EXPOSE 8080

# Set environment variables for secrets (override in cloud)
ENV CONFIG_PATH=/app/config/secrets.env

# Default command to run the bot
CMD ["python", "-m", "bot.main"]