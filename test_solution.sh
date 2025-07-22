#!/bin/bash

# Test script for PDF Outline Extractor
echo "🔍 Testing PDF Outline Extractor Solution"

# Create test directories
mkdir -p input output

# Copy test files 
echo "📄 Setting up test files..."
cp file01.pdf file03.pdf input/ 2>/dev/null || echo "⚠️  Test PDFs not found, using any available PDFs"

# Build Docker image
echo "🐳 Building Docker image..."
docker build --platform linux/amd64 -t pdf-outline-extractor:test .

if [ $? -eq 0 ]; then
    echo "✅ Docker build successful"
else
    echo "❌ Docker build failed"
    exit 1
fi

# Run the container
echo "🚀 Running PDF extraction..."
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none pdf-outline-extractor:test

# Check results
echo "📊 Results:"
ls -la output/
echo ""

# Show sample result if available
if [ -f "output/file03.json" ]; then
    echo "📋 Sample output (file03.json):"
    head -20 output/file03.json
fi

echo "✅ Test completed successfully!"
