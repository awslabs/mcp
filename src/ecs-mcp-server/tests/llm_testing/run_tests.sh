#!/bin/bash

# Main script to run all ECS MCP Server LLM test scenarios
# Usage: ./run_tests.sh [scenario_number]

# Set script location as base directory
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd $BASE_DIR

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load helper functions
source "$BASE_DIR/utils/aws_helpers.sh"

# Print header
echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}   ECS MCP Server LLM Testing Framework Runner         ${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo ""

# List available scenarios
list_scenarios() {
    echo -e "${YELLOW}Available Test Scenarios:${NC}"
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

    echo -e "${YELLOW}Running scenario: ${GREEN}$scenario_name${NC}"
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

    if [ ! -f "$scenario_dir/05_cleanup.sh" ]; then
        echo -e "${RED}Warning: Cleanup script (05_cleanup.sh) not found in $scenario_dir.${NC}"
    fi

    # Display scenario description if available
    if [ -f "$scenario_dir/description.txt" ]; then
        echo -e "${BLUE}Test description:${NC}"
        cat "$scenario_dir/description.txt"
        echo ""
    fi

    # Run create script
    echo -e "${BLUE}Running create script...${NC}"
    "$scenario_dir/01_create.sh"
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Create script failed.${NC}"
        return 1
    fi

    # Wait for a moment to let resources be created
    echo -e "${BLUE}Waiting for resources to be created/updated...${NC}"
    sleep 10

    # Run validate script
    echo -e "${BLUE}Running validate script...${NC}"
    "$scenario_dir/02_validate.sh"
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Validation failed.${NC}"
        echo -e "${YELLOW}The scenario may not be ready for testing.${NC}"
    else
        echo -e "${GREEN}Scenario is ready for testing.${NC}"
    fi

    # Display prompts
    if [ -f "$scenario_dir/03_prompts.txt" ]; then
        echo -e "${BLUE}Available test prompts:${NC}"
        echo -e "${YELLOW}=======================================================${NC}"
        cat "$scenario_dir/03_prompts.txt"
        echo -e "${YELLOW}=======================================================${NC}"
    else
        echo -e "${RED}Warning: No prompts file (03_prompts.txt) found.${NC}"
    fi

    # Ask if user wants to run cleanup
    read -p "Do you want to run the cleanup script now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]] && [ -f "$scenario_dir/05_cleanup.sh" ]; then
        echo -e "${BLUE}Running cleanup script...${NC}"
        "$scenario_dir/05_cleanup.sh"
        echo -e "${GREEN}Cleanup completed.${NC}"
    else
        echo -e "${YELLOW}Skipping cleanup. Remember to manually run ${scenario_dir}/05_cleanup.sh when done testing.${NC}"
    fi

    echo -e "${YELLOW}=======================================================${NC}"
    echo -e "${GREEN}Scenario execution completed.${NC}"
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
echo -e "${GREEN}Testing completed.${NC}"
echo -e "${BLUE}=======================================================${NC}"
