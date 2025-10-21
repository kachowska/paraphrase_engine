#!/bin/bash

# Paraphrase Engine v1.0 - Startup Script

set -e

echo "=========================================="
echo "   Paraphrase Engine v1.0 - Starting"
echo "=========================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please copy env.example to .env and configure it."
    exit 1
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p temp_files logs credentials

# Check Python version
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python $required_version or higher is required (found $python_version)"
    exit 1
fi

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run the application
echo "Starting Paraphrase Engine..."
python3 main.py
