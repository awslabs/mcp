#!/bin/bash

# Main script to run all ECS MCP Server Integration test scenarios using MCP Inspector
# Usage: ./run-tests.sh [scenario_number]

# Set script location as base directory
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd $BASE_DIR

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load helper functions from llm_testing
LLMTEST_BASE_DIR="$(dirname "$(dirname "$BASE_DIR")")/llm_testing"
source "$LLMTEST_BASE_DIR/utils/aws_helpers.sh"

# Print header
echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}   ECS MCP Server Integration Testing (MCP Inspector) ${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo ""

# List available scenarios
list_scenarios() {
    echo -e "${YELLOW}Available MCP Integration Test Scenarios:${NC}"
    echo ""
    for dir in "$BASE_DIR"/scenarios/*/; do
        if [ -d "$dir" ]; then
            scenario_num=$(basename "$dir" | cut -d'_' -f1)
            scenario_name=$(basename "$dir" | cut -d'_' -f2-)
            description=""

            # Check for description file
            if [ -f "${dir}/description.txt" ]; then
                description=$(cat "${dir}/description.txt" | head -n 1)
            fi

            echo -e "  ${GREEN}$scenario_num${NC}: $scenario_name"
            if [ ! -z "$description" ]; then
                echo -e "     └─ $description"
            fi
        fi
    done
    echo ""
}

# Run a specific scenario
run_scenario() {
    local scenario_dir=$1
    local scenario_name=$(basename "$scenario_dir" | cut -d'_' -f2-)

    echo -e "${YELLOW}Running MCP Inspector scenario: ${GREEN}$scenario_name${NC}"
    echo -e "${YELLOW}=======================================================${NC}"

    # Check if the scenario directory exists
    if [ ! -d "$scenario_dir" ]; then
        echo -e "${RED}Error: Scenario directory $scenario_dir does not exist.${NC}"
        return 1
    fi

    # Check if all required scripts exist
    if [ ! -f "$scenario_dir/01_create.sh" ]; then
        echo -e "${RED}Error: Create script (01_create.sh) not found in $scenario_dir.${NC}"
        return 1
    fi

    if [ ! -f "$scenario_dir/02_validate.sh" ]; then
        echo -e "${RED}Error: Validate script (02_validate.sh) not found in $scenario_dir.${NC}"
        return 1
    fi

    # Display scenario description if available
    if [ -f "$scenario_dir/description.txt" ]; then
        echo -e "${BLUE}Test description:${NC}"
        cat "$scenario_dir/description.txt"
        echo ""
    fi

    # Create log file for this test run
    local log_file="$BASE_DIR/mcp-integration-test-$(date +%Y%m%d_%H%M%S).log"
    echo -e "${BLUE}Logging output to: $log_file${NC}"
    exec > >(tee -a "$log_file") 2>&1

    echo -e "${BLUE}Running create script...${NC}"
    if ! "$scenario_dir/01_create.sh"; then
        echo -e "${RED}Error: Create script failed.${NC}"
        return 1
    fi

    # Poll for service readiness instead of fixed wait
    echo -e "${BLUE}Waiting for ECS service to be ready for testing...${NC}"

    # Find the created cluster and service
    CLUSTERS=$(aws ecs list-clusters --query 'clusterArns[*]' --output text)
    CLUSTER_NAME=""
    for CLUSTER_ARN in $CLUSTERS; do
        TEMP_CLUSTER_NAME=$(echo "$CLUSTER_ARN" | awk -F/ '{print $2}')
        if [[ "$TEMP_CLUSTER_NAME" == *"mcp-integration-test-cluster"* ]]; then
            CLUSTER_NAME="$TEMP_CLUSTER_NAME"
            break
        fi
    done

    if [ -n "$CLUSTER_NAME" ]; then
        # Poll until we have failed tasks or timeout
        local wait_count=0
        local max_wait=18  # 3 minutes (18 * 10 seconds)

        while [ $wait_count -lt $max_wait ]; do
            STOPPED_TASKS=$(aws ecs list-tasks --cluster "$CLUSTER_NAME" --desired-status STOPPED --query 'length(taskArns)' 2>/dev/null || echo "0")

            if [ "$STOPPED_TASKS" -gt 0 ]; then
                echo -e "${GREEN}✅ Found $STOPPED_TASKS stopped tasks - scenario is ready for testing${NC}"
                break
            fi

            echo "Waiting for tasks to fail... ($((wait_count * 10))s elapsed)"
            sleep 10
            wait_count=$((wait_count + 1))
        done

        if [ $wait_count -eq $max_wait ]; then
            echo -e "${YELLOW}⚠️ Timed out waiting for task failures. Proceeding with testing anyway.${NC}"
        fi
    fi

    # Run validation script (MCP Inspector tests)
    echo -e "${BLUE}Running MCP Inspector validation tests...${NC}"
    if ! "$scenario_dir/02_validate.sh" "$CLUSTER_NAME"; then
        echo -e "${RED}Error: MCP Inspector validation failed.${NC}"
        echo -e "${YELLOW}Check the log file for detailed error information: $log_file${NC}"
    else
        echo -e "${GREEN}✅ All MCP Inspector troubleshooting tool tests passed!${NC}"
    fi

    # Ask if user wants to run cleanup
    echo ""
    read -p "Do you want to run the cleanup script now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]] && [ -f "$scenario_dir/03_cleanup.sh" ]; then
        echo -e "${BLUE}Running cleanup script...${NC}"
        "$scenario_dir/03_cleanup.sh"
        echo -e "${GREEN}Cleanup completed.${NC}"
    else
        echo -e "${YELLOW}Skipping cleanup. Remember to manually run cleanup when done:${NC}"
        echo -e "${YELLOW}  cd $scenario_dir && ./03_cleanup.sh${NC}"
    fi

    echo -e "${YELLOW}=======================================================${NC}"
    echo -e "${GREEN}MCP Inspector scenario execution completed.${NC}"
    echo -e "${BLUE}Log file saved at: $log_file${NC}"
    echo ""
}

# Main execution
if [ -z "$1" ]; then
    # No specific scenario specified, list available scenarios
    list_scenarios
    read -p "Enter the scenario number to run (or 'all' for all scenarios): " scenario_choice

    if [ "$scenario_choice" == "all" ]; then
        # Run all scenarios
        for dir in "$BASE_DIR"/scenarios/*/; do
            if [ -d "$dir" ]; then
                run_scenario "$dir"
            fi
        done
    else
        # Run specific scenario
        scenario_dir="$BASE_DIR/scenarios/${scenario_choice}_*"
        # Use wildcard expansion to find the directory
        scenario_dir_expanded=$(echo $scenario_dir)
        run_scenario "$scenario_dir_expanded"
    fi
else
    # Specific scenario specified
    scenario_dir="$BASE_DIR/scenarios/${1}_*"
    # Use wildcard expansion to find the directory
    scenario_dir_expanded=$(echo $scenario_dir)
    run_scenario "$scenario_dir_expanded"
fi

echo -e "${BLUE}=======================================================${NC}"
echo -e "${GREEN}MCP Inspector integration testing completed.${NC}"
echo -e "${BLUE}=======================================================${NC}"
