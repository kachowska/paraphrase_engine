#!/bin/bash

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     Paraphrase Engine v1.0 - Quick Install & Start          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
echo "📌 Checking Python version..."
python3 --version

# Upgrade pip
echo ""
echo "📦 Upgrading pip..."
pip3 install --upgrade pip setuptools wheel --quiet

# Install dependencies
echo ""
echo "📥 Installing dependencies (this may take a minute)..."
pip3 install -r requirements-minimal.txt --quiet

# Verify configuration
echo ""
echo "🔍 Verifying configuration..."
python3 verify_config.py

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                  ✅ Installation Complete!                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "🚀 To start your bot, run:"
echo "   python3 -m paraphrase_engine.main"
echo ""
echo "Or simply run:"
echo "   ./start.sh"
echo ""
