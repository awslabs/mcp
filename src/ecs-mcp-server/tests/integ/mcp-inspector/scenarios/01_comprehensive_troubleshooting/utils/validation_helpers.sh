#!/bin/bash

# JSON Response Validation Helper Functions
# This file contains utility functions for validating JSON responses from MCP tools

# Colors for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Validate that a response is valid JSON
validate_json() {
    local response="$1"
    local tool_name="$2"

    if [ -z "$response" ]; then
        echo -e "${RED}❌ [$tool_name] Empty response${NC}"
        return 1
    fi

    # Try to parse JSON with jq
    if echo "$response" | jq . >/dev/null 2>&1; then
        echo -e "${GREEN}✅ [$tool_name] Valid JSON response${NC}"
        return 0
    else
        echo -e "${RED}❌ [$tool_name] Invalid JSON response${NC}"
        echo "First 500 chars of response: ${response:0:500}..."
        return 1
    fi
}

# Extract tool result from MCP response format
extract_tool_result() {
    local response="$1"
    local tool_name="$2"

    # Check if response has MCP content array format
    local has_content
    has_content=$(echo "$response" | jq -r 'has("content")' 2>/dev/null)

    if [ "$has_content" = "true" ]; then
        # Extract tool result from MCP content array
        local tool_result
        tool_result=$(echo "$response" | jq -r '.content[0].text // empty' 2>/dev/null)

        if [ -n "$tool_result" ] && [ "$tool_result" != "null" ]; then
            # Validate tool result is valid JSON
            if echo "$tool_result" | jq . >/dev/null 2>&1; then
                echo "$tool_result"
                return 0
            else
                echo -e "${RED}❌ [$tool_name] Tool result is not valid JSON${NC}" >&2
                echo "Tool result content: ${tool_result:0:200}..." >&2
                return 1
            fi
        else
            echo -e "${RED}❌ [$tool_name] No tool result found in MCP response${NC}" >&2
            return 1
        fi
    else
        # Direct JSON response (not wrapped in MCP format)
        echo "$response"
        return 0
    fi
}

# Validate tool response has success status
validate_success_status() {
    local tool_result="$1"
    local tool_name="$2"

    local status
    status=$(echo "$tool_result" | jq -r '.status // "unknown"')

    case "$status" in
        "success")
            echo -e "${GREEN}✅ [$tool_name] Success status confirmed${NC}"
            return 0
            ;;
        "error")
            echo -e "${RED}❌ [$tool_name] Error status detected${NC}"
            local error_msg
            error_msg=$(echo "$tool_result" | jq -r '.error // "No error message"')
            echo -e "${RED}   Error: $error_msg${NC}"
            return 1
            ;;
        *)
            echo -e "${YELLOW}⚠️ [$tool_name] Unknown status: $status${NC}"
            return 1
            ;;
    esac
}

# Validate specific fields exist in tool response
validate_response_fields() {
    local tool_result="$1"
    local tool_name="$2"
    shift 2
    local expected_fields=("$@")

    local errors=0

    for field in "${expected_fields[@]}"; do
        local field_exists
        field_exists=$(echo "$tool_result" | jq -r "has(\"$field\")")

        if [ "$field_exists" = "true" ]; then
            echo -e "${GREEN}✅ [$tool_name] Field '$field' present${NC}"
        else
            echo -e "${RED}❌ [$tool_name] Field '$field' missing${NC}"
            errors=$((errors + 1))
        fi
    done

    if [ $errors -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# Comprehensive validation for get_ecs_troubleshooting_guidance tool
validate_get_ecs_troubleshooting_guidance() {
    local response="$1"

    echo -e "${BLUE}🔍 Validating get_ecs_troubleshooting_guidance response...${NC}"

    if ! validate_json "$response" "get_ecs_troubleshooting_guidance"; then
        return 1
    fi

    local tool_result
    if ! tool_result=$(extract_tool_result "$response" "get_ecs_troubleshooting_guidance"); then
        return 1
    fi

    if ! validate_success_status "$tool_result" "get_ecs_troubleshooting_guidance"; then
        return 1
    fi

    # The tool may have different response fields, let's be flexible
    # Just check that it has a status field and basic structure
    echo -e "${GREEN}✅ [get_ecs_troubleshooting_guidance] Basic validation passed${NC}"
    return 0
}

# Comprehensive validation for detect_image_pull_failures tool
validate_detect_image_pull_failures() {
    local response="$1"

    echo -e "${BLUE}🔍 Validating detect_image_pull_failures response...${NC}"

    if ! validate_json "$response" "detect_image_pull_failures"; then
        return 1
    fi

    local tool_result
    if ! tool_result=$(extract_tool_result "$response" "detect_image_pull_failures"); then
        return 1
    fi

    if ! validate_success_status "$tool_result" "detect_image_pull_failures"; then
        return 1
    fi

    # Expected fields for image pull failures
    local expected_fields=("image_issues" "assessment")
    validate_response_fields "$tool_result" "detect_image_pull_failures" "${expected_fields[@]}"
}

# Comprehensive validation for fetch_service_events tool
validate_fetch_service_events() {
    local response="$1"

    echo -e "${BLUE}🔍 Validating fetch_service_events response...${NC}"

    if ! validate_json "$response" "fetch_service_events"; then
        return 1
    fi

    local tool_result
    if ! tool_result=$(extract_tool_result "$response" "fetch_service_events"); then
        return 1
    fi

    if ! validate_success_status "$tool_result" "fetch_service_events"; then
        return 1
    fi

    # Expected fields for service events (based on actual response)
    local expected_fields=("events")
    validate_response_fields "$tool_result" "fetch_service_events" "${expected_fields[@]}"
}

# Comprehensive validation for fetch_task_failures tool
validate_fetch_task_failures() {
    local response="$1"

    echo -e "${BLUE}🔍 Validating fetch_task_failures response...${NC}"

    if ! validate_json "$response" "fetch_task_failures"; then
        return 1
    fi

    local tool_result
    if ! tool_result=$(extract_tool_result "$response" "fetch_task_failures"); then
        return 1
    fi

    if ! validate_success_status "$tool_result" "fetch_task_failures"; then
        return 1
    fi

    # Expected fields for task failures (based on actual response)
    local expected_fields=("failed_tasks")
    validate_response_fields "$tool_result" "fetch_task_failures" "${expected_fields[@]}"
}

# Comprehensive validation for fetch_task_logs tool
validate_fetch_task_logs() {
    local response="$1"

    echo -e "${BLUE}🔍 Validating fetch_task_logs response...${NC}"

    if ! validate_json "$response" "fetch_task_logs"; then
        return 1
    fi

    local tool_result
    if ! tool_result=$(extract_tool_result "$response" "fetch_task_logs"); then
        return 1
    fi

    if ! validate_success_status "$tool_result" "fetch_task_logs"; then
        return 1
    fi

    # Expected fields for task logs
    local expected_fields=("log_entries")
    validate_response_fields "$tool_result" "fetch_task_logs" "${expected_fields[@]}"
}

# Comprehensive validation for fetch_network_configuration tool
validate_fetch_network_configuration() {
    local response="$1"

    echo -e "${BLUE}🔍 Validating fetch_network_configuration response...${NC}"

    if ! validate_json "$response" "fetch_network_configuration"; then
        return 1
    fi

    local tool_result
    if ! tool_result=$(extract_tool_result "$response" "fetch_network_configuration"); then
        return 1
    fi

    if ! validate_success_status "$tool_result" "fetch_network_configuration"; then
        return 1
    fi

    # Expected fields for network configuration (based on actual response)
    local expected_fields=("data")
    validate_response_fields "$tool_result" "fetch_network_configuration" "${expected_fields[@]}"
}

# Print validation summary
print_validation_summary() {
    local total_tests="$1"
    local passed_tests="$2"
    local failed_tests="$3"

    echo ""
    echo "=================================================="
    echo "           VALIDATION SUMMARY"
    echo "=================================================="
    echo -e "Total tests:  $total_tests"
    echo -e "Passed tests: ${GREEN}$passed_tests${NC}"
    echo -e "Failed tests: ${RED}$failed_tests${NC}"
    echo "=================================================="

    if [ $failed_tests -eq 0 ]; then
        echo -e "${GREEN}🎉 All validation tests passed!${NC}"
        return 0
    else
        echo -e "${RED}❌ $failed_tests validation test(s) failed${NC}"
        return 1
    fi
}
