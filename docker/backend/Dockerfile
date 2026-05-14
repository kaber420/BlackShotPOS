FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for cryptography, asyncpg, escpos, etc.
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    libusb-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy python project configuration first for caching
COPY pyproject.toml ./

# Copy the rest of the application
# Note: Context should be the project root
COPY . .

# Install the application and its dependencies
RUN pip install --no-cache-dir -e .

# Expose API port
EXPOSE 8000

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
