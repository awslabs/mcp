#!/bin/bash
# Script to run the nova-canvas-mcp-server tests

# Set the Python path to include the current directory and the parent directory
export PYTHONPATH=$PYTHONPATH:$(pwd):$(pwd)/..

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: You are not running in a virtual environment."
    echo "It's recommended to create and activate a virtual environment before running tests."
    echo "You can create one with: python -m venv venv"
    echo "And activate it with: source venv/bin/activate (Linux/Mac) or venv\\Scripts\\activate (Windows)"
    echo "Continuing without a virtual environment..."
    echo ""
fi

# Always use python -m pytest to ensure we use the correct pytest
PYTEST_CMD="python -m pytest"

# Check if pytest and other dependencies are installed
echo "Checking for required packages..."
MISSING_PACKAGES=()

# Check for pytest
python -c "import pytest" 2>/dev/null
if [ $? -ne 0 ]; then
    MISSING_PACKAGES+=("pytest pytest-asyncio pytest-cov")
fi

# Check for boto3 package
python -c "import boto3" 2>/dev/null
if [ $? -ne 0 ]; then
    MISSING_PACKAGES+=("boto3")
fi

# Check for loguru package
python -c "import loguru" 2>/dev/null
if [ $? -ne 0 ]; then
    MISSING_PACKAGES+=("loguru")
fi

# Check for pydantic package
python -c "import pydantic" 2>/dev/null
if [ $? -ne 0 ]; then
    MISSING_PACKAGES+=("pydantic")
fi

# Install missing packages
if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo "Installing missing packages: ${MISSING_PACKAGES[*]}"

    # Try pip first (more reliable)
    if command -v pip &> /dev/null; then
        echo "Using pip to install packages..."
        pip install ${MISSING_PACKAGES[*]} -v
    # Try pip3 if pip is not available
    elif command -v pip3 &> /dev/null; then
        echo "Using pip3 to install packages..."
        pip3 install ${MISSING_PACKAGES[*]} -v
    # Try uv as a last resort
    elif command -v uv &> /dev/null; then
        echo "Using uv to install packages..."
        uv pip install ${MISSING_PACKAGES[*]} -v
    else
        echo "Error: No package manager (pip, pip3, or uv) is available. Please install the missing packages manually."
        exit 1
    fi

    # Verify installation with more verbose output
    echo "Verifying package installations..."
    for pkg in "pytest" "boto3" "loguru" "pydantic"; do
        echo "Checking for $pkg..."
        python -c "import $pkg; print(f'$pkg version: {$pkg.__version__}')" 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "Failed to install $pkg. Trying to install it individually..."
            pip install $pkg -v || pip3 install $pkg -v || echo "Failed to install $pkg. Please install it manually."

            # Check again
            python -c "import $pkg" 2>/dev/null
            if [ $? -ne 0 ]; then
                echo "Still failed to install $pkg. Please install it manually."
                echo "You can try: pip install $pkg"
                exit 1
            fi
        fi
    done
fi

# Print debug information
echo "Debug information:"
echo "Python version: $(python --version)"
echo "Python path: $PYTHONPATH"
echo "Current directory: $(pwd)"
echo "Python executable: $(which python)"
echo "Pytest module location: $(python -c "import pytest; print(pytest.__file__)" 2>/dev/null || echo "Not found")"

# Check if nova_canvas_mcp_server module can be imported
echo "Checking if nova_canvas_mcp_server module can be imported..."
python -c "import awslabs.nova_canvas_mcp_server; print(f'nova_canvas_mcp_server module found at: {awslabs.nova_canvas_mcp_server.__file__}')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Warning: nova_canvas_mcp_server module cannot be imported. This may cause test failures."
    echo "Installing the package in development mode..."

    # Check if uv is available
    if command -v uv &> /dev/null; then
        uv pip install -e .
    # Check if pip is available
    elif command -v pip &> /dev/null; then
        pip install -e .
    else
        echo "Neither uv nor pip is available. Creating a symbolic link instead..."
        # Create a symbolic link to the module in the current directory
        ln -sf $(pwd)/awslabs/nova_canvas_mcp_server $(pwd)/nova_canvas_mcp_server 2>/dev/null
    fi

    echo "Trying again..."
    python -c "import awslabs.nova_canvas_mcp_server; print(f'nova_canvas_mcp_server module found at: {awslabs.nova_canvas_mcp_server.__file__}')" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "Still cannot import nova_canvas_mcp_server module. Tests may fail."
        echo "Directory structure:"
        ls -la
        echo "awslabs directory:"
        ls -la awslabs 2>/dev/null || echo "awslabs directory not found"
    fi
fi

# Check if tests directory exists
if [ -d "tests" ]; then
    # List test files
    echo "Test files found:"
    find tests -name "test_*.py" | sort

    # Run the tests
    echo "Running tests..."
    $PYTEST_CMD -xvs tests/

    # If pytest fails, try using unittest as a fallback
    if [ $? -ne 0 ]; then
        echo "Pytest failed. Trying to run tests with unittest as a fallback..."
        python -m unittest discover -s tests
    fi

    # Run tests with coverage
    echo "Running tests with coverage..."
    $PYTEST_CMD --cov --cov-branch --cov-report=term-missing tests/
else
    echo "No tests directory found, skipping tests"
fi

echo "Test run completed."
