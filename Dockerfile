# Use Python 3.9 slim image for smaller size
# FROM --platform=linux/amd64 python:3.9-slim
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for PyMuPDF
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY final_pdf_extractor.py .

# Create input and output directories
RUN mkdir -p /app/input /app/output

# Set the entrypoint
ENTRYPOINT ["python", "final_pdf_extractor.py"]
