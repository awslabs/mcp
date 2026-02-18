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

# Local fuzzing execution script for AWS MCP Servers
# This script runs fuzz targets locally with configurable duration
# and generates coverage reports after the run.
#
# Requirements: 14.2, 14.3
#
# Usage:
#   ./fuzzing/scripts/run_local.sh [options] -t <target>
#
# Options:
#   -h, --help          Show this help message
#   -t, --target        Target to fuzz (required, e.g., fuzz_sql_injection)
#   -d, --duration      Fuzzing duration in seconds (default: 60)
#   -c, --corpus        Path to corpus directory (optional)
#   -D, --dict          Path to dictionary file (optional)
#   -o, --output        Output directory for results (default: fuzzing/results)
#   -v, --verbose       Enable verbose output
#   --coverage          Generate coverage report after fuzzing
#   --pytest            Run as pytest test instead of Atheris fuzzer
#   --examples          Number of Hypothesis examples (default: 100)
#
# Example:
#   ./fuzzing/scripts/run_local.sh -t fuzz_sql_injection -d 120
#   ./fuzzing/scripts/run_local.sh -t fuzz_pdf --pytest --examples 500
#   ./fuzzing/scripts/run_local.sh -t fuzz_json_nesting --coverage

set -o errexit
set -o nounset
set -o pipefail

# Script directory and repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FUZZING_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$FUZZING_DIR")"

# Default options
TARGET=""
DURATION=60
CORPUS_DIR=""
DICT_FILE=""
OUTPUT_DIR="${FUZZING_DIR}/results"
VERBOSE=false
GENERATE_COVERAGE=false
USE_PYTEST=false
HYPOTHESIS_EXAMPLES=100

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
Local fuzzing execution script for AWS MCP Servers

Usage: $(basename "$0") [options] -t <target>

Options:
  -h, --help          Show this help message
  -t, --target        Target to fuzz (required, e.g., fuzz_sql_injection)
  -d, --duration      Fuzzing duration in seconds (default: 60)
  -c, --corpus        Path to corpus directory (optional)
  -D, --dict          Path to dictionary file (optional)
  -o, --output        Output directory for results (default: fuzzing/results)
  -v, --verbose       Enable verbose output
  --coverage          Generate coverage report after fuzzing
  --pytest            Run as pytest test instead of Atheris fuzzer
  --examples          Number of Hypothesis examples when using --pytest (default: 100)

Available targets:
  postgres/fuzz_sql_injection       SQL injection detection fuzzer
  document_loader/fuzz_pdf          PDF parsing fuzzer
  document_loader/fuzz_path_validation  Path validation fuzzer
  openapi/fuzz_spec_parser          OpenAPI specification fuzzer
  dynamodb/fuzz_item_validation     DynamoDB item validation fuzzer
  dynamodb/fuzz_json_nesting        JSON nesting fuzzer
  aws_api/fuzz_command_parser       AWS CLI command parser fuzzer
  neptune/fuzz_gremlin              Gremlin query fuzzer
  neptune/fuzz_sparql               SPARQL query fuzzer
  aws_documentation/fuzz_url_validation  URL validation fuzzer
  aws_documentation/fuzz_path_traversal  Path traversal fuzzer
  mq/fuzz_message_payload           Amazon MQ message fuzzer
  sns_sqs/fuzz_message_structure    SNS/SQS message fuzzer
  core/fuzz_config_parser           Configuration parser fuzzer
  core/fuzz_yaml_toml               YAML/TOML parser fuzzer

Examples:
  $(basename "$0") -t postgres/fuzz_sql_injection -d 120
  $(basename "$0") -t openapi/fuzz_spec_parser --pytest --examples 500
  $(basename "$0") -t dynamodb/fuzz_json_nesting --coverage -v

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
            -t|--target)
                TARGET="$2"
                shift 2
                ;;
            -d|--duration)
                DURATION="$2"
                shift 2
                ;;
            -c|--corpus)
                CORPUS_DIR="$2"
                shift 2
                ;;
            -D|--dict)
                DICT_FILE="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --coverage)
                GENERATE_COVERAGE=true
                shift
                ;;
            --pytest)
                USE_PYTEST=true
                shift
                ;;
            --examples)
                HYPOTHESIS_EXAMPLES="$2"
                shift 2
                ;;
            *)
                error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Validate required arguments
    if [ -z "$TARGET" ]; then
        error "Target is required. Use -t or --target to specify."
        usage
        exit 1
    fi
}


# Find target file
find_target() {
    local target="$1"
    local target_file=""

    # Check if target includes category path
    if [[ "$target" == *"/"* ]]; then
        target_file="$FUZZING_DIR/targets/$target.py"
    else
        # Search for target in all categories
        for category_dir in "$FUZZING_DIR/targets"/*/; do
            if [ -f "$category_dir$target.py" ]; then
                target_file="$category_dir$target.py"
                break
            fi
        done
    fi

    if [ -z "$target_file" ] || [ ! -f "$target_file" ]; then
        error "Target not found: $target"
        echo ""
        echo "Available targets:"
        find "$FUZZING_DIR/targets" -name "fuzz_*.py" -exec basename {} .py \; 2>/dev/null | sort | sed 's/^/  - /'
        exit 1
    fi

    echo "$target_file"
}

# Get category from target file path
get_category() {
    local target_file="$1"
    basename "$(dirname "$target_file")"
}

# Find corpus directory for target
find_corpus() {
    local category="$1"
    local corpus_path="$FUZZING_DIR/corpus/$category"

    if [ -d "$corpus_path" ] && [ "$(ls -A "$corpus_path" 2>/dev/null)" ]; then
        echo "$corpus_path"
    fi
}

# Find dictionary for target
find_dictionary() {
    local category="$1"
    local dict_path=""

    case "$category" in
        postgres|mysql)
            dict_path="$FUZZING_DIR/dictionaries/sql.dict"
            ;;
        openapi)
            dict_path="$FUZZING_DIR/dictionaries/openapi.dict"
            ;;
        dynamodb)
            dict_path="$FUZZING_DIR/dictionaries/json.dict"
            ;;
        neptune)
            dict_path="$FUZZING_DIR/dictionaries/gremlin.dict"
            ;;
        aws_api)
            dict_path="$FUZZING_DIR/dictionaries/aws_cli.dict"
            ;;
        core)
            dict_path="$FUZZING_DIR/dictionaries/yaml.dict"
            ;;
    esac

    if [ -n "$dict_path" ] && [ -f "$dict_path" ]; then
        echo "$dict_path"
    fi
}

# Setup output directory
setup_output() {
    local target_name="$1"
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local run_dir="$OUTPUT_DIR/${target_name}_${timestamp}"

    mkdir -p "$run_dir/corpus"
    mkdir -p "$run_dir/crashes"
    mkdir -p "$run_dir/coverage"

    echo "$run_dir"
}

# Run with pytest/Hypothesis
run_pytest() {
    local target_file="$1"
    local run_dir="$2"

    info "Running with pytest/Hypothesis (${HYPOTHESIS_EXAMPLES} examples)..."

    local pytest_args=(
        "-v"
        "--tb=short"
        "-x"  # Stop on first failure
    )

    # Add coverage if requested
    if [ "$GENERATE_COVERAGE" = true ]; then
        pytest_args+=(
            "--cov=$FUZZING_DIR"
            "--cov-report=html:$run_dir/coverage/html"
            "--cov-report=json:$run_dir/coverage/coverage.json"
        )
    fi

    # Set Hypothesis examples via environment
    export HYPOTHESIS_MAX_EXAMPLES="$HYPOTHESIS_EXAMPLES"

    verbose "Running: pytest ${pytest_args[*]} $target_file"

    # Run pytest
    if python3 -m pytest "${pytest_args[@]}" "$target_file" 2>&1 | tee "$run_dir/pytest_output.log"; then
        success "Pytest run completed successfully"
        return 0
    else
        warn "Pytest run completed with failures"
        return 1
    fi
}


# Run with Atheris fuzzer
run_atheris() {
    local target_file="$1"
    local run_dir="$2"
    local corpus_dir="$3"
    local dict_file="$4"

    # Check if atheris is available
    if ! python3 -c "import atheris" 2>/dev/null; then
        error "Atheris is not installed. Install with: pip install atheris"
        error "Alternatively, use --pytest to run with Hypothesis instead."
        exit 1
    fi

    info "Running with Atheris fuzzer for ${DURATION} seconds..."

    # Build atheris command
    local atheris_args=()

    # Add corpus directory
    if [ -n "$corpus_dir" ]; then
        atheris_args+=("$corpus_dir")
        verbose "Using corpus: $corpus_dir"
    fi

    # Add new corpus output directory
    atheris_args+=("$run_dir/corpus")

    # Add dictionary if available
    if [ -n "$dict_file" ]; then
        atheris_args+=("-dict=$dict_file")
        verbose "Using dictionary: $dict_file"
    fi

    # Add timeout
    atheris_args+=("-max_total_time=$DURATION")

    # Add artifact prefix for crashes
    atheris_args+=("-artifact_prefix=$run_dir/crashes/")

    # Add other useful options
    atheris_args+=("-print_final_stats=1")
    atheris_args+=("-print_corpus_stats=1")

    verbose "Running: python3 $target_file ${atheris_args[*]}"

    # Set up Python path
    export PYTHONPATH="${FUZZING_DIR}:${REPO_ROOT}/src:${PYTHONPATH:-}"

    # Run atheris
    local exit_code=0
    if python3 "$target_file" "${atheris_args[@]}" 2>&1 | tee "$run_dir/atheris_output.log"; then
        success "Atheris fuzzing completed"
    else
        exit_code=$?
        if [ $exit_code -eq 77 ]; then
            # Exit code 77 means a crash was found
            warn "Atheris found crashes (exit code 77)"
        else
            warn "Atheris exited with code $exit_code"
        fi
    fi

    # Count crashes
    local crash_count
    crash_count=$(find "$run_dir/crashes" -type f 2>/dev/null | wc -l | tr -d ' ')
    if [ "$crash_count" -gt 0 ]; then
        warn "Found $crash_count crash(es) in $run_dir/crashes/"
    fi

    return $exit_code
}

# Generate coverage report
generate_coverage_report() {
    local target_file="$1"
    local run_dir="$2"

    info "Generating coverage report..."

    # Run with coverage
    local coverage_file="$run_dir/coverage/.coverage"

    python3 -m coverage run --data-file="$coverage_file" -m pytest "$target_file" -v --tb=short 2>&1 | tee -a "$run_dir/coverage_run.log" || true

    # Generate HTML report
    if [ -f "$coverage_file" ]; then
        python3 -m coverage html --data-file="$coverage_file" -d "$run_dir/coverage/html" 2>/dev/null || true
        python3 -m coverage json --data-file="$coverage_file" -o "$run_dir/coverage/coverage.json" 2>/dev/null || true
        python3 -m coverage report --data-file="$coverage_file" 2>&1 | tee "$run_dir/coverage/summary.txt" || true

        success "Coverage report generated in $run_dir/coverage/"
    else
        warn "No coverage data generated"
    fi
}

# Print run summary
print_summary() {
    local target_name="$1"
    local run_dir="$2"
    local duration="$3"
    local mode="$4"

    echo ""
    info "Run Summary"
    echo "============================================"
    echo "Target:     $target_name"
    echo "Mode:       $mode"
    echo "Duration:   ${duration}s"
    echo "Output:     $run_dir"
    echo ""

    # Count corpus entries
    local corpus_count
    corpus_count=$(find "$run_dir/corpus" -type f 2>/dev/null | wc -l | tr -d ' ')
    echo "Corpus entries: $corpus_count"

    # Count crashes
    local crash_count
    crash_count=$(find "$run_dir/crashes" -type f 2>/dev/null | wc -l | tr -d ' ')
    echo "Crashes found:  $crash_count"

    # Show coverage if available
    if [ -f "$run_dir/coverage/summary.txt" ]; then
        echo ""
        echo "Coverage Summary:"
        tail -5 "$run_dir/coverage/summary.txt" | sed 's/^/  /'
    fi

    echo "============================================"

    # Show crash files if any
    if [ "$crash_count" -gt 0 ]; then
        echo ""
        warn "Crash files:"
        find "$run_dir/crashes" -type f -exec basename {} \; 2>/dev/null | head -10 | sed 's/^/  - /'
        if [ "$crash_count" -gt 10 ]; then
            echo "  ... and $((crash_count - 10)) more"
        fi
    fi
}


# Main function
main() {
    parse_args "$@"

    echo "============================================"
    echo "AWS MCP Servers - Local Fuzzing Runner"
    echo "============================================"
    echo ""

    # Find target file
    local target_file
    target_file=$(find_target "$TARGET")
    local target_name
    target_name=$(basename "$target_file" .py)
    local category
    category=$(get_category "$target_file")

    info "Target: $category/$target_name"
    verbose "Target file: $target_file"

    # Find corpus and dictionary if not specified
    if [ -z "$CORPUS_DIR" ]; then
        CORPUS_DIR=$(find_corpus "$category")
        if [ -n "$CORPUS_DIR" ]; then
            verbose "Auto-detected corpus: $CORPUS_DIR"
        fi
    fi

    if [ -z "$DICT_FILE" ]; then
        DICT_FILE=$(find_dictionary "$category")
        if [ -n "$DICT_FILE" ]; then
            verbose "Auto-detected dictionary: $DICT_FILE"
        fi
    fi

    # Setup output directory
    local run_dir
    run_dir=$(setup_output "$target_name")
    info "Output directory: $run_dir"

    # Set up Python path
    export PYTHONPATH="${FUZZING_DIR}:${REPO_ROOT}/src:${PYTHONPATH:-}"
    verbose "PYTHONPATH: $PYTHONPATH"

    # Run fuzzing
    local start_time
    start_time=$(date +%s)
    local exit_code=0
    local mode=""

    if [ "$USE_PYTEST" = true ]; then
        mode="pytest/Hypothesis"
        run_pytest "$target_file" "$run_dir" || exit_code=$?
    else
        mode="Atheris"
        run_atheris "$target_file" "$run_dir" "$CORPUS_DIR" "$DICT_FILE" || exit_code=$?
    fi

    local end_time
    end_time=$(date +%s)
    local actual_duration=$((end_time - start_time))

    # Generate coverage report if requested and not already done
    if [ "$GENERATE_COVERAGE" = true ] && [ "$USE_PYTEST" = false ]; then
        generate_coverage_report "$target_file" "$run_dir"
    fi

    # Print summary
    print_summary "$target_name" "$run_dir" "$actual_duration" "$mode"

    echo ""
    if [ $exit_code -eq 0 ]; then
        success "Fuzzing run completed successfully!"
    else
        warn "Fuzzing run completed with issues (exit code: $exit_code)"
    fi

    exit $exit_code
}

# Run main function
main "$@"
