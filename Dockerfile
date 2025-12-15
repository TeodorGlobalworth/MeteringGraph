FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Flask port
EXPOSE 5067

# Run with Gunicorn (production server)
# 4 workers, 2 threads each = 8 concurrent requests per container
CMD ["gunicorn", "--bind", "0.0.0.0:5067", "--workers", "4", "--threads", "2", "run:app"]
