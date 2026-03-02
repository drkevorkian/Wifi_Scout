#!/bin/bash
# Network Scout - Unix Installation Script

echo "================================================"
echo "  Network Scout v2.2.9 - Installation"
echo "================================================"
echo

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "Python found:"
python3 --version
echo

# Create virtual environment (optional but recommended)
echo "Creating virtual environment..."
python3 -m venv venv
if [ $? -eq 0 ]; then
    echo "Virtual environment created successfully"
    source venv/bin/activate
else
    echo "Warning: Could not create virtual environment"
    echo "Continuing with system Python..."
fi
echo

# Upgrade pip
echo "Upgrading pip..."
python3 -m pip install --upgrade pip
echo

# Install dependencies
echo "Installing dependencies..."
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo
    echo "ERROR: Failed to install dependencies"
    exit 1
fi
echo

echo "================================================"
echo "  Installation Complete!"
echo "================================================"
echo
echo "To run Network Scout:"
if [ -d "venv" ]; then
    echo "  1. Activate virtual environment: source venv/bin/activate"
    echo "  2. Run: python3 network_suite.py"
else
    echo "  python3 network_suite.py"
fi
echo
echo "Or simply run: ./run_wifi_scout.sh"
echo
