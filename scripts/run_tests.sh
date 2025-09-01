#!/bin/bash

# Run tests for Ping SSO Onboarding Agent

set -e

echo "🧪 Running Ping SSO Onboarding Agent Tests"
echo "=========================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
pip install pytest-cov pytest-asyncio

# Run linting
echo "Running code quality checks..."
if command -v black &> /dev/null; then
    black --check app/ tests/
else
    echo "Warning: black not installed, skipping formatting check"
fi

if command -v isort &> /dev/null; then
    isort --check-only app/ tests/
else
    echo "Warning: isort not installed, skipping import check"
fi

# Run tests
echo "Running tests..."
pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

echo "✅ All tests completed!"
echo "📊 Coverage report generated in htmlcov/"
