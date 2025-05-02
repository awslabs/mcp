#!/bin/bash
# Activation script for oferv-details-mcp virtual environment

# Directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/.venv"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found at $VENV_DIR"
    echo "Please create it first with: python3 -m venv .venv"
    exit 1
fi

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Load environment variables from .env file if it exists
ENV_FILE="$SCRIPT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment variables from $ENV_FILE"
    # Export variables from .env file
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "No .env file found at $ENV_FILE"
fi

pip install -r requirements.txt

echo "Virtual environment activated. Run 'deactivate' to exit."
echo "Python executable: $(which python)"
echo "Python version: $(python --version)"