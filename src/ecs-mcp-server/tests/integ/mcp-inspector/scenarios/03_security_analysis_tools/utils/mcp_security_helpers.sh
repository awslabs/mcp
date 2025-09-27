#!/bin/bash

# MCP Inspector CLI Helper Functions for ECS Security Analysis Tools
# This file contains utility functions for calling MCP Inspector CLI commands
# and parsing responses from ECS security analysis tools

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

# Call MCP security analysis tool with specified action and parameters
# Usage: call_mcp_security_analysis_tool <action> <parameters_json>
call_mcp_security_analysis_tool() {
    local action="$1"
    local parameters="$2"

    if [ -z "$action" ]; then
        echo "❌ Error: Action is required" >&2
        return 1
    fi

    if [ -z "$parameters" ]; then
        parameters="{}"
    fi

    echo "🔧 Calling MCP security analysis tool: action=$action, parameters=$parameters" >&2

    # Execute MCP Inspector CLI command using existing config
    local response
    response=$(mcp-inspector \
        --config "$MCP_CONFIG_FILE" \
        --server "$MCP_SERVER_NAME" \
        --cli \
        --method tools/call \
        --tool-name ecs_security_analysis_tool \
        --tool-arg "action=$action" \
        --tool-arg "parameters=${parameters}" 2>&1)

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

# Wrapper functions for each security analysis tool action

# Test list_clusters action
test_security_list_clusters() {
    local region="$1"

    local params="{"
    if [ -n "$region" ]; then
        params="$params\"region\":\"$region\""
    fi
    params="$params}"

    call_mcp_security_analysis_tool "list_clusters" "$params"
}

# Test analyze_cluster_security action
test_security_analyze_cluster_security() {
    local cluster_name="$1"
    local region="$2"

    if [ -z "$cluster_name" ]; then
        echo "❌ Error: cluster_name is required for analyze_cluster_security"
        return 1
    fi

    local params="{"
    params="$params\"cluster_name\":\"$cluster_name\""

    if [ -n "$region" ]; then
        params="$params,\"region\":\"$region\""
    fi

    params="$params}"

    call_mcp_security_analysis_tool "analyze_cluster_security" "$params"
}

# Test generate_security_report action
test_security_generate_security_report() {
    local cluster_name="$1"
    local report_format="$2"
    local region="$3"

    if [ -z "$cluster_name" ]; then
        echo "❌ Error: cluster_name is required for generate_security_report"
        return 1
    fi

    local params="{"
    params="$params\"cluster_name\":\"$cluster_name\""

    if [ -n "$report_format" ]; then
        params="$params,\"report_format\":\"$report_format\""
    fi

    if [ -n "$region" ]; then
        params="$params,\"region\":\"$region\""
    fi

    params="$params}"

    call_mcp_security_analysis_tool "generate_security_report" "$params"
}

# Test get_security_recommendations action
test_security_get_security_recommendations() {
    local cluster_name="$1"
    local severity_filter="$2"
    local region="$3"

    if [ -z "$cluster_name" ]; then
        echo "❌ Error: cluster_name is required for get_security_recommendations"
        return 1
    fi

    local params="{"
    params="$params\"cluster_name\":\"$cluster_name\""

    if [ -n "$severity_filter" ]; then
        params="$params,\"severity_filter\":\"$severity_filter\""
    fi

    if [ -n "$region" ]; then
        params="$params,\"region\":\"$region\""
    fi

    params="$params}"

    call_mcp_security_analysis_tool "get_security_recommendations" "$params"
}

# Test check_compliance_status action
test_security_check_compliance_status() {
    local cluster_name="$1"
    local compliance_framework="$2"
    local region="$3"

    if [ -z "$cluster_name" ]; then
        echo "❌ Error: cluster_name is required for check_compliance_status"
        return 1
    fi

    local params="{"
    params="$params\"cluster_name\":\"$cluster_name\""

    if [ -n "$compliance_framework" ]; then
        params="$params,\"compliance_framework\":\"$compliance_framework\""
    fi

    if [ -n "$region" ]; then
        params="$params,\"region\":\"$region\""
    fi

    params="$params}"

    call_mcp_security_analysis_tool "check_compliance_status" "$params"
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

# Validate prerequisites for MCP security analysis testing
validate_mcp_security_prerequisites() {
    echo "🔍 Validating MCP security analysis testing prerequisites..."

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
