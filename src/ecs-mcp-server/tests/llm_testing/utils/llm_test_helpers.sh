#!/bin/bash

# LLM Test Helper functions for ECS MCP Server LLM testing
# This file contains utility functions for LLM testing scenarios

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_step() {
    echo -e "${BLUE}🔍 $1${NC}"
}

# Validate LLM testing environment
validate_llm_test_environment() {
    local validation_passed=true

    # Check if Python 3 is available
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed or not in PATH"
        validation_passed=false
    else
        log_success "Python 3 is available"
    fi

    # Check if AWS CLI is available and configured
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed or not in PATH"
        validation_passed=false
    else
        log_success "AWS CLI is available"

        # Check if AWS credentials are configured
        if aws sts get-caller-identity &> /dev/null; then
            log_success "AWS credentials are configured"
        else
            log_error "AWS credentials are not configured"
            validation_passed=false
        fi
    fi

    # Check if required Python modules are available
    if python3 -c "import asyncio, json, sys, os, unittest.mock" &> /dev/null; then
        log_success "Required Python modules are available"
    else
        log_error "Required Python modules are not available"
        validation_passed=false
    fi

    if [ "$validation_passed" = true ]; then
        return 0
    else
        return 1
    fi
}

# Check if ECS cluster exists
check_cluster_exists() {
    local cluster_name=$1
    local region=${2:-"us-east-1"}

    if aws ecs describe-clusters --clusters "$cluster_name" --region "$region" &>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Wait for cluster to be active
wait_for_cluster_active() {
    local cluster_name=$1
    local region=${2:-"us-east-1"}
    local max_wait_seconds=${3:-300}  # Default 5 minutes

    log_step "Waiting for cluster $cluster_name to be active (timeout: ${max_wait_seconds}s)..."

    local start_time=$(date +%s)

    while true; do
        local current_time=$(date +%s)
        local elapsed_time=$((current_time - start_time))

        if [ $elapsed_time -gt $max_wait_seconds ]; then
            log_error "Timeout reached. Cluster did not become active within $max_wait_seconds seconds."
            return 1
        fi

        local status
        status=$(aws ecs describe-clusters --clusters "$cluster_name" --region "$region" \
            --query 'clusters[0].status' --output text 2>/dev/null)
        local exit_code=$?

        if [ $exit_code -ne 0 ]; then
            log_error "Cluster $cluster_name does not exist or cannot be accessed."
            return 1
        fi

        if [ "$status" == "ACTIVE" ]; then
            log_success "Cluster is active."
            return 0
        fi

        log_info "Current status: $status (elapsed time: ${elapsed_time}s)"
        sleep 10  # Check every 10 seconds
    done
}

# Generate a random 5-character ID for resource naming
generate_random_id() {
    python3 -c "import uuid; print(str(uuid.uuid4()).replace('-', '')[:5])"
}

# Check if task definition exists
check_task_definition_exists() {
    local task_def_name=$1
    local region=${2:-"us-east-1"}

    if aws ecs describe-task-definition --task-definition "$task_def_name" --region "$region" &>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Check if service exists
check_service_exists() {
    local cluster_name=$1
    local service_name=$2
    local region=${3:-"us-east-1"}

    if aws ecs describe-services --cluster "$cluster_name" --services "$service_name" --region "$region" &>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Display test scenario header
display_scenario_header() {
    local scenario_name=$1
    local description=$2

    echo ""
    echo "=" * 60
    echo "🧪 LLM Testing Scenario: $scenario_name"
    echo "=" * 60
    echo ""
    if [ -n "$description" ]; then
        echo "$description"
        echo ""
    fi
}

# Display test results summary
display_test_summary() {
    local passed_tests=$1
    local total_tests=$2
    local scenario_name=${3:-"LLM Testing"}

    echo ""
    echo "=" * 60
    echo "📊 $scenario_name Summary"
    echo "=" * 60
    echo ""
    echo "Tests Passed: $passed_tests/$total_tests"

    if [ "$passed_tests" -eq "$total_tests" ]; then
        log_success "All tests passed! 🎉"
        echo ""
        echo "The ECS MCP Server tools are ready for LLM interactions."
        return 0
    else
        local failed_tests=$((total_tests - passed_tests))
        log_error "$failed_tests test(s) failed."
        echo ""
        echo "Please review the test output above for details."
        return 1
    fi
}

# Create temporary Python test file
create_python_test_file() {
    local test_file_path=$1
    local test_content=$2

    cat > "$test_file_path" << EOF
$test_content
EOF

    chmod +x "$test_file_path"
}

# Clean up temporary files
cleanup_temp_files() {
    local temp_files=("$@")

    for file in "${temp_files[@]}"; do
        if [ -f "$file" ]; then
            rm -f "$file"
            log_info "Cleaned up temporary file: $file"
        fi
    done
}

# Validate that required AWS resources exist for testing
validate_test_resources() {
    local cluster_name=$1
    local region=${2:-"us-east-1"}
    local required_resources=("${@:3}")

    log_step "Validating test resources..."

    # Check cluster
    if check_cluster_exists "$cluster_name" "$region"; then
        log_success "Test cluster '$cluster_name' exists"
    else
        log_error "Test cluster '$cluster_name' not found"
        return 1
    fi

    # Check additional resources if specified
    for resource in "${required_resources[@]}"; do
        case "$resource" in
            "task-definition:"*)
                local task_def_name="${resource#task-definition:}"
                if check_task_definition_exists "$task_def_name" "$region"; then
                    log_success "Task definition '$task_def_name' exists"
                else
                    log_error "Task definition '$task_def_name' not found"
                    return 1
                fi
                ;;
            "service:"*)
                local service_name="${resource#service:}"
                if check_service_exists "$cluster_name" "$service_name" "$region"; then
                    log_success "Service '$service_name' exists"
                else
                    log_error "Service '$service_name' not found"
                    return 1
                fi
                ;;
        esac
    done

    return 0
}

# Run Python test script and capture results
run_python_test() {
    local test_script_path=$1
    local test_name=${2:-"Python Test"}

    log_step "Running $test_name..."

    if python3 "$test_script_path"; then
        log_success "$test_name completed successfully"
        return 0
    else
        log_error "$test_name failed"
        return 1
    fi
}

# Display available test prompts from file
display_test_prompts() {
    local prompts_file=$1

    if [ -f "$prompts_file" ]; then
        echo ""
        echo "Available test prompts:"
        echo "=" * 60
        cat "$prompts_file"
        echo "=" * 60
    else
        log_warning "Test prompts file not found: $prompts_file"
    fi
}

# Check if all required environment variables are set
check_required_env_vars() {
    local required_vars=("$@")
    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
        return 1
    else
        log_success "All required environment variables are set"
        return 0
    fi
}
