#!/bin/bash

# Run tests with coverage reporting
echo "Running tests with coverage reporting..."
python -m pytest --cov=bedrock_advisor --cov-report=term --cov-report=html --cov-report=xml

# Check if tests passed
if [ $? -eq 0 ]; then
    echo "Tests passed successfully!"
    echo "Coverage report generated in htmlcov/ directory"
    echo "Coverage XML report generated in coverage.xml file"
else
    echo "Tests failed!"
    exit 1
fi
