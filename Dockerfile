FROM python:3.12-slim

WORKDIR /app

# Switch to Aliyun mirror for faster package downloads in China
# First, remove any existing sources
RUN rm -f /etc/apt/sources.list.d/* && \
    # Create new sources.list with Aliyun mirrors for Debian 12 (bookworm)
    echo "deb http://mirrors.aliyun.com/debian/ bookworm main non-free contrib" > /etc/apt/sources.list && \
    echo "deb-src http://mirrors.aliyun.com/debian/ bookworm main non-free contrib" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security bookworm-security main non-free contrib" >> /etc/apt/sources.list && \
    echo "deb-src http://mirrors.aliyun.com/debian-security bookworm-security main non-free contrib" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bookworm-updates main non-free contrib" >> /etc/apt/sources.list && \
    echo "deb-src http://mirrors.aliyun.com/debian/ bookworm-updates main non-free contrib" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bookworm-backports main non-free contrib" >> /etc/apt/sources.list && \
    echo "deb-src http://mirrors.aliyun.com/debian/ bookworm-backports main non-free contrib" >> /etc/apt/sources.list

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Use Aliyun PyPI mirror for faster package downloads
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.aliyun.com && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .


# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Run the application with increased timeout
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "300", "--workers", "2", "app:app"] 