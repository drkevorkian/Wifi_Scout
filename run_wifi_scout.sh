#!/bin/bash
# Network Scout - Quick Launch Script

echo "Starting Network Scout v2.2.9..."
echo

# Check if virtual environment exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the application
python3 network_suite.py

# Check exit code
if [ $? -ne 0 ]; then
    echo
    echo "Application exited with an error."
    read -p "Press Enter to continue..."
fi
