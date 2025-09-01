#!/bin/bash

# Setup script for Ping SSO Onboarding Agent Visual Demo

set -e

echo "🎨 Setting up Ping SSO Onboarding Agent Visual Demo"
echo "=================================================="

# Check Node.js version
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ first."
    echo "   Visit: https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 16 ]; then
    echo "❌ Node.js version 16+ is required. Found: $(node --version)"
    echo "   Please upgrade Node.js: https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js version: $(node --version)"

# Check npm
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

echo "✅ npm version: $(npm --version)"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "🚀 To start the visual demo:"
echo "   npm start"
echo ""
echo "🌐 The demo will open at: http://localhost:3000"
echo ""
echo "🎮 Demo Controls:"
echo "   - Click 'Play' to run the automated demo"
echo "   - Use 'Step Forward' for manual progression"
echo "   - Click 'Reset' to start over"
echo "   - Select different clients from the dropdown"
echo ""
echo "📚 For more information, see README.md"

