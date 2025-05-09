#!/bin/bash
set -e

cd "$(dirname "$0")"

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# Install dependencies using uv if available, else fallback to pip
if command -v uv &> /dev/null; then
  echo "Installing dependencies with uv..."
  uv pip install -r ../uv.lock || uv pip install -r ../pyproject.toml
else
  echo "Installing dependencies with pip..."
  pip install --upgrade pip
  pip install -r ../requirements.txt || pip install -r ../pyproject.toml
fi

# Run the integration test script
export PYTHONPATH="$(cd .. && pwd):$PYTHONPATH"
echo "Running integration tests (test_server_integration.py)..."
python test_server_integration.py

RESULT=$?
if [ $RESULT -eq 0 ]; then
  echo "Integration tests completed successfully."
else
  echo "Integration tests failed with exit code $RESULT."
fi
