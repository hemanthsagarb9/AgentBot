#!/bin/bash

# Setup script for Ping SSO Onboarding Agent

set -e

echo "🚀 Setting up Ping SSO Onboarding Agent"
echo "======================================"

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python $required_version or higher is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Setup environment file
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env file with your configuration"
fi

# Initialize database
echo "Initializing database..."
if [ ! -d "migrations/versions" ]; then
    alembic revision --autogenerate -m "Initial migration"
fi

echo "✅ Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Start PostgreSQL database"
echo "3. Run: alembic upgrade head"
echo "4. Run: uvicorn app.main:app --reload"
echo ""
echo "Or use Docker Compose:"
echo "docker-compose up -d"
