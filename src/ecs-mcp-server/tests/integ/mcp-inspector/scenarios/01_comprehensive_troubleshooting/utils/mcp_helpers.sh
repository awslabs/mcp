#!/bin/bash

# MCP Inspector CLI Helper Functions for ECS Troubleshooting Tools
# This file contains utility functions for calling MCP Inspector CLI commands
# and parsing responses from ECS troubleshooting tools

# Use existing MCP config file
MCP_CONFIG_FILE="/tmp/mcp-config.json"
MCP_SERVER_NAME="local-ecs-mcp-server"

# Validate MCP configuration exists
check_mcp_config() {
    if [ ! -f "$MCP_CONFIG_FILE" ]; then
        echo "❌ MCP configuration not found at $MCP_CONFIG_FILE"
        echo "Please ensure your MCP configuration is set up properly."
        return 1
    fi

    # Validate the server exists in the config
    if ! jq -e ".mcpServers.\"$MCP_SERVER_NAME\"" "$MCP_CONFIG_FILE" >/dev/null 2>&1; then
        echo "❌ Server '$MCP_SERVER_NAME' not found in MCP configuration"
        echo "Available servers:"
        jq -r '.mcpServers | keys[]' "$MCP_CONFIG_FILE" 2>/dev/null || echo "  (Unable to parse config)"
        return 1
    fi

    echo "✅ MCP configuration validated"
    return 0
}

# Call MCP troubleshooting tool with specified action and parameters
# Usage: call_mcp_troubleshooting_tool <action> <parameters_json>
call_mcp_troubleshooting_tool() {
    local action="$1"
    local parameters="$2"

    if [ -z "$action" ]; then
        echo "❌ Error: Action is required" >&2
        return 1
    fi

    if [ -z "$parameters" ]; then
        parameters="{}"
    fi

    echo "🔧 Calling MCP tool: action=$action, parameters=$parameters" >&2

    # Execute MCP Inspector CLI command using existing config
    local response
    response=$(mcp-inspector \
        --config "$MCP_CONFIG_FILE" \
        --server "$MCP_SERVER_NAME" \
        --cli \
        --method tools/call \
        --tool-name ecs_troubleshooting_tool \
        --tool-arg "action=$action" \
        --tool-arg "parameters=$parameters" 2>&1)

    local exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo "❌ MCP Inspector command failed with exit code $exit_code" >&2
        echo "Error output: $response" >&2
        return 1
    fi

    # Return only the JSON response, not debug messages
    echo "$response"
    return 0
}

# Wrapper functions for each troubleshooting tool

# Test get_ecs_troubleshooting_guidance tool
test_get_ecs_troubleshooting_guidance() {
    local cluster_name="$1"
    local service_name="$2"
    local symptoms="$3"

    if [ -z "$cluster_name" ]; then
        echo "❌ Error: cluster_name is required for get_ecs_troubleshooting_guidance"
        return 1
    fi

    local params="{"
    params="$params\"cluster_name\":\"$cluster_name\""

    if [ -n "$service_name" ]; then
        params="$params,\"service_name\":\"$service_name\""
    fi

    if [ -n "$symptoms" ]; then
        params="$params,\"symptoms_description\":\"$symptoms\""
    fi

    params="$params}"

    call_mcp_troubleshooting_tool "get_ecs_troubleshooting_guidance" "$params"
}

# Test detect_image_pull_failures tool
test_detect_image_pull_failures() {
    local cluster_name="$1"
    local service_name="$2"
    local family_prefix="$3"

    local params="{"
    local has_param=false

    if [ -n "$cluster_name" ]; then
        params="$params\"cluster_name\":\"$cluster_name\""
        has_param=true
    fi

    if [ -n "$service_name" ]; then
        if [ "$has_param" = true ]; then
            params="$params,"
        fi
        params="$params\"service_name\":\"$service_name\""
        has_param=true
    fi

    if [ -n "$family_prefix" ]; then
        if [ "$has_param" = true ]; then
            params="$params,"
        fi
        params="$params\"family_prefix\":\"$family_prefix\""
        has_param=true
    fi

    params="$params}"

    call_mcp_troubleshooting_tool "detect_image_pull_failures" "$params"
}

# Test fetch_service_events tool
test_fetch_service_events() {
    local cluster_name="$1"
    local service_name="$2"
    local time_window="$3"

    if [ -z "$cluster_name" ] || [ -z "$service_name" ]; then
        echo "❌ Error: cluster_name and service_name are required for fetch_service_events"
        return 1
    fi

    local params="{"
    params="$params\"cluster_name\":\"$cluster_name\""
    params="$params,\"service_name\":\"$service_name\""

    if [ -n "$time_window" ]; then
        params="$params,\"time_window\":$time_window"
    fi

    params="$params}"

    call_mcp_troubleshooting_tool "fetch_service_events" "$params"
}

# Test fetch_task_failures tool
test_fetch_task_failures() {
    local cluster_name="$1"
    local time_window="$2"

    if [ -z "$cluster_name" ]; then
        echo "❌ Error: cluster_name is required for fetch_task_failures"
        return 1
    fi

    local params="{"
    params="$params\"cluster_name\":\"$cluster_name\""

    if [ -n "$time_window" ]; then
        params="$params,\"time_window\":$time_window"
    fi

    params="$params}"

    call_mcp_troubleshooting_tool "fetch_task_failures" "$params"
}

# Test fetch_task_logs tool
test_fetch_task_logs() {
    local cluster_name="$1"
    local task_id="$2"
    local filter_pattern="$3"
    local time_window="$4"

    if [ -z "$cluster_name" ]; then
        echo "❌ Error: cluster_name is required for fetch_task_logs"
        return 1
    fi

    local params="{"
    params="$params\"cluster_name\":\"$cluster_name\""

    if [ -n "$task_id" ]; then
        params="$params,\"task_id\":\"$task_id\""
    fi

    if [ -n "$filter_pattern" ]; then
        params="$params,\"filter_pattern\":\"$filter_pattern\""
    fi

    if [ -n "$time_window" ]; then
        params="$params,\"time_window\":$time_window"
    fi

    params="$params}"

    call_mcp_troubleshooting_tool "fetch_task_logs" "$params"
}

# Test fetch_network_configuration tool
test_fetch_network_configuration() {
    local vpc_id="$1"
    local cluster_name="$2"

    local params="{"
    local has_param=false

    if [ -n "$vpc_id" ]; then
        params="$params\"vpc_id\":\"$vpc_id\""
        has_param=true
    fi

    if [ -n "$cluster_name" ]; then
        if [ "$has_param" = true ]; then
            params="$params,"
        fi
        params="$params\"cluster_name\":\"$cluster_name\""
        has_param=true
    fi

    params="$params}"

    call_mcp_troubleshooting_tool "fetch_network_configuration" "$params"
}

# Check if mcp-inspector is available
check_mcp_inspector() {
    if command -v mcp-inspector >/dev/null 2>&1; then
        echo "✅ mcp-inspector CLI is available"
        return 0
    else
        echo "❌ mcp-inspector CLI is not available. Please install it first."
        echo "   You can install it using: pip install mcp-inspector"
        return 1
    fi
}

# Check if uv is available (required by the MCP config)
check_uv() {
    if command -v uv >/dev/null 2>&1; then
        echo "✅ uv is available"
        return 0
    else
        echo "❌ uv is not available. Please install it first."
        echo "   You can install it using: pip install uv"
        return 1
    fi
}

# Validate prerequisites for MCP testing
validate_mcp_prerequisites() {
    echo "🔍 Validating MCP testing prerequisites..."

    local errors=0

    if ! check_uv; then
        errors=$((errors + 1))
    fi

    if ! check_mcp_inspector; then
        errors=$((errors + 1))
    fi

    if ! check_mcp_config; then
        errors=$((errors + 1))
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        echo "❌ AWS credentials are not configured properly"
        errors=$((errors + 1))
    else
        echo "✅ AWS credentials are configured"
    fi

    if [ $errors -eq 0 ]; then
        echo "✅ All prerequisites validated successfully"
        return 0
    else
        echo "❌ $errors prerequisite(s) failed validation"
        return 1
    fi
}
