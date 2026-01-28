#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Local build script for AWS MCP Servers fuzz targets
# This script builds fuzz targets with coverage instrumentation locally
# for development and testing purposes.
#
# Requirements: 14.1
#
# Usage:
#   ./fuzzing/scripts/build_local.sh [options]
#
# Options:
#   -h, --help      Show this help message
#   -v, --verbose   Enable verbose output
#   -c, --clean     Clean build artifacts before building
#   -t, --target    Build specific target (e.g., postgres, openapi)
#
# Example:
#   ./fuzzing/scripts/build_local.sh                    # Build all targets
#   ./fuzzing/scripts/build_local.sh -t postgres        # Build postgres targets only
#   ./fuzzing/scripts/build_local.sh -c -v              # Clean and verbose build

set -o errexit
set -o nounset
set -o pipefail

# Script directory and repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FUZZING_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$FUZZING_DIR")"

# Build output directory
BUILD_DIR="${FUZZING_DIR}/build"

# Default options
VERBOSE=false
CLEAN=false
TARGET_FILTER=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color


# Print colored message
print_msg() {
    local color="$1"
    local msg="$2"
    echo -e "${color}${msg}${NC}"
}

# Print info message
info() {
    print_msg "$BLUE" "[INFO] $1"
}

# Print success message
success() {
    print_msg "$GREEN" "[SUCCESS] $1"
}

# Print warning message
warn() {
    print_msg "$YELLOW" "[WARNING] $1"
}

# Print error message
error() {
    print_msg "$RED" "[ERROR] $1"
}

# Print verbose message
verbose() {
    if [ "$VERBOSE" = true ]; then
        print_msg "$NC" "[VERBOSE] $1"
    fi
}

# Show usage
usage() {
    cat << EOF
Local build script for AWS MCP Servers fuzz targets

Usage: $(basename "$0") [options]

Options:
  -h, --help      Show this help message
  -v, --verbose   Enable verbose output
  -c, --clean     Clean build artifacts before building
  -t, --target    Build specific target category (e.g., postgres, openapi)

Target categories:
  postgres          SQL injection detection fuzzers
  document_loader   Document parsing fuzzers
  openapi           OpenAPI specification fuzzers
  dynamodb          DynamoDB/JSON validation fuzzers
  aws_api           AWS API command parsing fuzzers
  neptune           Graph query (Gremlin/SPARQL) fuzzers
  aws_documentation URL and path validation fuzzers
  mq                Amazon MQ message fuzzers
  sns_sqs           SNS/SQS message fuzzers
  core              Configuration parsing fuzzers

Examples:
  $(basename "$0")                    # Build all targets
  $(basename "$0") -t postgres        # Build postgres targets only
  $(basename "$0") -c -v              # Clean and verbose build
  $(basename "$0") -t openapi -v      # Build openapi targets with verbose output

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -c|--clean)
                CLEAN=true
                shift
                ;;
            -t|--target)
                TARGET_FILTER="$2"
                shift 2
                ;;
            *)
                error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# Clean build artifacts
clean_build() {
    info "Cleaning build artifacts..."
    rm -rf "$BUILD_DIR"
    find "$FUZZING_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$FUZZING_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
    find "$FUZZING_DIR" -type f -name ".coverage*" -delete 2>/dev/null || true
    success "Build artifacts cleaned"
}

# Create build directory structure
setup_build_dir() {
    info "Setting up build directory..."
    mkdir -p "$BUILD_DIR/targets"
    mkdir -p "$BUILD_DIR/corpus"
    mkdir -p "$BUILD_DIR/dictionaries"
    verbose "Build directory: $BUILD_DIR"
}

# Check Python environment
check_python() {
    info "Checking Python environment..."

    if ! command -v python3 &> /dev/null; then
        error "Python 3 is not installed"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    verbose "Python version: $PYTHON_VERSION"

    # Check for required packages
    local required_packages=("hypothesis" "pydantic")
    for pkg in "${required_packages[@]}"; do
        if ! python3 -c "import $pkg" 2>/dev/null; then
            warn "Package '$pkg' not found. Install with: pip install $pkg"
        else
            verbose "Package '$pkg' is available"
        fi
    done

    # Check for optional atheris package
    if python3 -c "import atheris" 2>/dev/null; then
        verbose "Atheris is available for coverage-guided fuzzing"
    else
        warn "Atheris not installed. Install with: pip install atheris"
        warn "Atheris is optional but enables coverage-guided fuzzing"
    fi

    success "Python environment check complete"
}


# Build a single fuzz target
build_target() {
    local target_file="$1"
    local target_name
    target_name=$(basename "$target_file" .py)
    local target_category
    target_category=$(basename "$(dirname "$target_file")")

    verbose "Building target: $target_category/$target_name"

    # Copy target file to build directory
    local target_build_dir="$BUILD_DIR/targets/$target_category"
    mkdir -p "$target_build_dir"
    cp "$target_file" "$target_build_dir/"

    # Verify the target is syntactically correct
    if python3 -m py_compile "$target_file" 2>/dev/null; then
        verbose "  Syntax check passed"
    else
        warn "  Syntax check failed for $target_name"
        return 1
    fi

    return 0
}

# Package corpus for a target category
package_corpus() {
    local category="$1"
    local corpus_dir="$FUZZING_DIR/corpus/$category"

    if [ -d "$corpus_dir" ] && [ "$(ls -A "$corpus_dir" 2>/dev/null)" ]; then
        verbose "Packaging corpus for: $category"
        local corpus_build_dir="$BUILD_DIR/corpus/$category"
        mkdir -p "$corpus_build_dir"
        cp -r "$corpus_dir"/* "$corpus_build_dir/" 2>/dev/null || true

        # Create zip archive for OSS-Fuzz compatibility
        if command -v zip &> /dev/null; then
            (cd "$corpus_build_dir" && zip -q -r "../${category}_seed_corpus.zip" . 2>/dev/null) || true
        fi
    else
        verbose "No corpus found for: $category"
    fi
}

# Copy dictionary for a target category
copy_dictionary() {
    local category="$1"
    local dict_name="$2"
    local dict_path="$FUZZING_DIR/dictionaries/$dict_name"

    if [ -f "$dict_path" ]; then
        verbose "Copying dictionary: $dict_name for $category"
        cp "$dict_path" "$BUILD_DIR/dictionaries/"
    fi
}

# Build all targets in a category
build_category() {
    local category_dir="$1"
    local category
    category=$(basename "$category_dir")

    # Skip if target filter is set and doesn't match
    if [ -n "$TARGET_FILTER" ] && [ "$category" != "$TARGET_FILTER" ]; then
        return 0
    fi

    info "Building category: $category"

    local target_count=0
    local success_count=0

    for target_file in "$category_dir"/fuzz_*.py; do
        if [ -f "$target_file" ]; then
            ((target_count++)) || true
            if build_target "$target_file"; then
                ((success_count++)) || true
            fi
        fi
    done

    if [ "$target_count" -gt 0 ]; then
        verbose "  Built $success_count/$target_count targets"

        # Package corpus
        package_corpus "$category"

        # Copy appropriate dictionaries based on category
        case "$category" in
            postgres|mysql)
                copy_dictionary "$category" "sql.dict"
                ;;
            openapi)
                copy_dictionary "$category" "openapi.dict"
                copy_dictionary "$category" "json.dict"
                ;;
            dynamodb)
                copy_dictionary "$category" "json.dict"
                ;;
            neptune)
                copy_dictionary "$category" "gremlin.dict"
                copy_dictionary "$category" "sparql.dict"
                ;;
            aws_api)
                copy_dictionary "$category" "aws_cli.dict"
                ;;
            core)
                copy_dictionary "$category" "yaml.dict"
                copy_dictionary "$category" "toml.dict"
                ;;
        esac
    fi
}

# Copy support files
copy_support_files() {
    info "Copying support files..."

    # Copy harness base and classifier
    cp "$FUZZING_DIR/harness_base.py" "$BUILD_DIR/" 2>/dev/null || true
    cp "$FUZZING_DIR/classifier.py" "$BUILD_DIR/" 2>/dev/null || true
    cp "$FUZZING_DIR/coverage_reporter.py" "$BUILD_DIR/" 2>/dev/null || true
    cp "$FUZZING_DIR/__init__.py" "$BUILD_DIR/" 2>/dev/null || true

    verbose "Support files copied to build directory"
}


# Generate build summary
generate_summary() {
    info "Build Summary"
    echo "============================================"
    echo "Build directory: $BUILD_DIR"
    echo ""

    # Count targets
    local target_count
    target_count=$(find "$BUILD_DIR/targets" -name "fuzz_*.py" 2>/dev/null | wc -l | tr -d ' ')
    echo "Fuzz targets built: $target_count"

    # Count corpus files
    local corpus_count
    corpus_count=$(find "$BUILD_DIR/corpus" -type f ! -name "*.zip" 2>/dev/null | wc -l | tr -d ' ')
    echo "Corpus files: $corpus_count"

    # Count dictionaries
    local dict_count
    dict_count=$(find "$BUILD_DIR/dictionaries" -name "*.dict" 2>/dev/null | wc -l | tr -d ' ')
    echo "Dictionaries: $dict_count"

    echo "============================================"

    # List built targets
    if [ "$VERBOSE" = true ]; then
        echo ""
        echo "Built targets:"
        find "$BUILD_DIR/targets" -name "fuzz_*.py" -exec basename {} \; 2>/dev/null | sort | sed 's/^/  - /'
    fi
}

# Main function
main() {
    parse_args "$@"

    echo "============================================"
    echo "AWS MCP Servers - Local Fuzz Target Builder"
    echo "============================================"
    echo ""

    # Clean if requested
    if [ "$CLEAN" = true ]; then
        clean_build
    fi

    # Setup
    check_python
    setup_build_dir

    # Build targets
    info "Building fuzz targets..."
    for category_dir in "$FUZZING_DIR/targets"/*/; do
        if [ -d "$category_dir" ]; then
            build_category "$category_dir"
        fi
    done

    # Copy support files
    copy_support_files

    # Generate summary
    echo ""
    generate_summary

    echo ""
    success "Build complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Run tests: pytest fuzzing/tests/ -v"
    echo "  2. Run local fuzzing: ./fuzzing/scripts/run_local.sh -t <target>"
    echo "  3. Generate coverage: pytest fuzzing/ --cov=fuzzing --cov-report=html"
}

# Run main function
main "$@"
