FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads && chmod 777 uploads

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Run the application with increased timeout
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "300", "--workers", "2", "app:app"] 