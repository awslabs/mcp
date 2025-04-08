#!/bin/bash
# Script to run the diagrams-mcp-server tests

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

# Check for diagrams package
python -c "import diagrams" 2>/dev/null
if [ $? -ne 0 ]; then
    MISSING_PACKAGES+=("diagrams")
fi

# Check for bandit package
python -c "import bandit" 2>/dev/null
if [ $? -ne 0 ]; then
    MISSING_PACKAGES+=("bandit")
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
    for pkg in "pytest" "diagrams" "bandit" "pydantic"; do
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

# Check if aws_diagram module can be imported
echo "Checking if diagrams_mcp_server module can be imported..."
python -c "import diagrams_mcp_server; print(f'diagrams_mcp_server module found at: {diagrams_mcp_server.__file__}')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Warning: diagrams_mcp_server module cannot be imported. This may cause test failures."
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
        ln -sf $(pwd)/awslabs/aws_diagram $(pwd)/aws_diagram 2>/dev/null
    fi

    echo "Trying again..."
    python -c "import diagrams_mcp_server; print(f'diagrams_mcp_server module found at: {diagrams_mcp_server.__file__}')" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "Still cannot import diagrams_mcp_server module. Tests may fail."
        echo "Directory structure:"
        ls -la
        echo "awslabs directory:"
        ls -la awslabs 2>/dev/null || echo "awslabs directory not found"
    fi
fi

# Check if tests directory exists and is not empty
if [ ! -d "tests" ]; then
    echo "Error: tests directory not found. Make sure you are running this script from the root of the project."
    exit 1
fi

if [ -z "$(ls -A tests)" ]; then
    echo "Error: tests directory is empty. No tests to run."
    exit 1
fi

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

# If you want to run with coverage, uncomment the following line
# $PYTEST_CMD --cov=aws_diagram --cov-report=term-missing tests/

# If you want to run with coverage and generate an HTML report, uncomment the following line
# $PYTEST_CMD --cov=aws_diagram --cov-report=html tests/

echo "Test run completed."
