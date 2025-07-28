#!/bin/bash

echo "PDF Outline Extractor"
echo "====================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH."
    echo "Please install Docker from https://www.docker.com/get-started"
    exit 1
fi

echo "Building Docker image..."
docker build -t pdf-outline-extractor .

if [ $? -ne 0 ]; then
    echo "Error: Failed to build Docker image."
    exit 1
fi

echo ""
echo "Docker image built successfully!"
echo ""
echo "To process PDF files, place them in the 'input' folder and run:"
echo "docker run --rm -v \"$(pwd)/input:/app/input\" -v \"$(pwd)/output:/app/output\" pdf-outline-extractor"
echo ""
echo "Results will be saved in the 'output' folder."

# Ask if user wants to run the container now
read -p "Do you want to process PDFs in the input folder now? (y/n): " RUN_NOW

if [[ $RUN_NOW =~ ^[Yy]$ ]]; then
    echo "Processing PDFs in input folder..."
    docker run --rm -v "$(pwd)/input:/app/input" -v "$(pwd)/output:/app/output" pdf-outline-extractor
    echo "Done! Check the output folder for results."
else
    echo "Exiting without processing."
fi