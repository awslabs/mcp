#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures

# MCP Inspector CLI Helper Functions for AWS Knowledge Tools
# This file contains utility functions for calling MCP Inspector CLI commands
# and parsing responses from AWS Knowledge tools

# =============================================================================
# CONSTANTS
# =============================================================================
# Colors for output formatting
readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# MCP Configuration
readonly MCP_CONFIG_FILE="/tmp/mcp-config.json"
readonly MCP_SERVER_NAME="local-ecs-mcp-server"
readonly INSTALL_COMMAND_MCP_INSPECTOR="npm install -g @modelcontextprotocol/inspector"
readonly INSTALL_COMMAND_UV="pip install uv"

# Validate MCP configuration exists
check_mcp_config() {
    if [ ! -f "${MCP_CONFIG_FILE}" ]; then
        echo "❌ MCP configuration not found at ${MCP_CONFIG_FILE}"
        echo "Please ensure your MCP configuration is set up properly."
        return 1
    fi

    # Validate the server exists in the config
    if ! jq -e ".mcpServers.\"${MCP_SERVER_NAME}\"" "${MCP_CONFIG_FILE}" >/dev/null 2>&1; then
        echo "❌ Server '${MCP_SERVER_NAME}' not found in MCP configuration"
        echo "Available servers:"
        jq -r '.mcpServers | keys[]' "${MCP_CONFIG_FILE}" 2>/dev/null || echo "  (Unable to parse config)"
        return 1
    fi

    echo "✅ MCP configuration validated"
    return 0
}

# Get list of all available tools from MCP server
# Usage: get_mcp_tools
get_mcp_tools() {
    echo "🔧 Fetching all available MCP tools..." >&2

    # Execute MCP Inspector CLI command to list tools
    local response
    response=$(mcp-inspector \
        --config "$MCP_CONFIG_FILE" \
        --server "$MCP_SERVER_NAME" \
        --cli \
        --method tools/list 2>&1)

    local exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo "❌ MCP Inspector tools/list failed with exit code $exit_code" >&2
        echo "Error output: $response" >&2
        return 1
    fi

    echo "$response"
    return 0
}

# Note: tools/get method is not supported by MCP Inspector CLI
# Tool descriptions can only be validated through the tools/list response
# which includes tool information but not detailed descriptions

# Call AWS Knowledge search documentation tool
# Usage: test_aws_knowledge_search_documentation <search_phrase>
test_aws_knowledge_search_documentation() {
    local search_phrase="$1"

    if [ -z "$search_phrase" ]; then
        echo "❌ Error: search_phrase is required for aws_knowledge_aws___search_documentation"
        return 1
    fi

    echo "🔧 Calling AWS Knowledge search_documentation with: ${search_phrase}" >&2

    # Execute MCP Inspector CLI command
    local response
    response=$(mcp-inspector \
        --config "$MCP_CONFIG_FILE" \
        --server "$MCP_SERVER_NAME" \
        --cli \
        --method tools/call \
        --tool-name aws_knowledge_aws___search_documentation \
        --tool-arg "search_phrase=${search_phrase}" 2>&1)

    local exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo "❌ MCP Inspector command failed with exit code $exit_code" >&2
        echo "Error output: $response" >&2
        return 1
    fi

    echo "$response"
    return 0
}

# Call AWS Knowledge read documentation tool
# Usage: test_aws_knowledge_read_documentation <url>
test_aws_knowledge_read_documentation() {
    local url="$1"

    if [ -z "$url" ]; then
        echo "❌ Error: url is required for aws_knowledge_aws___read_documentation"
        return 1
    fi

    echo "🔧 Calling AWS Knowledge read_documentation with: ${url}" >&2

    # Execute MCP Inspector CLI command
    local response
    response=$(mcp-inspector \
        --config "$MCP_CONFIG_FILE" \
        --server "$MCP_SERVER_NAME" \
        --cli \
        --method tools/call \
        --tool-name aws_knowledge_aws___read_documentation \
        --tool-arg "url=${url}" 2>&1)

    local exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo "❌ MCP Inspector command failed with exit code $exit_code" >&2
        echo "Error output: $response" >&2
        return 1
    fi

    echo "$response"
    return 0
}

# Call AWS Knowledge recommend tool
# Usage: test_aws_knowledge_recommend <url>
test_aws_knowledge_recommend() {
    local url="$1"

    if [ -z "$url" ]; then
        echo "❌ Error: url is required for aws_knowledge_aws___recommend"
        return 1
    fi

    echo "🔧 Calling AWS Knowledge recommend with: ${url}" >&2

    # Execute MCP Inspector CLI command
    local response
    response=$(mcp-inspector \
        --config "$MCP_CONFIG_FILE" \
        --server "$MCP_SERVER_NAME" \
        --cli \
        --method tools/call \
        --tool-name aws_knowledge_aws___recommend \
        --tool-arg "url=${url}" 2>&1)

    local exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo "❌ MCP Inspector command failed with exit code $exit_code" >&2
        echo "Error output: $response" >&2
        return 1
    fi

    echo "$response"
    return 0
}

# Check if mcp-inspector is available
check_mcp_inspector() {
    if command -v mcp-inspector >/dev/null 2>&1; then
        echo "✅ mcp-inspector CLI is available"
        return 0
    else
        echo "❌ mcp-inspector CLI is not available. Please install it first."
        echo "   You can install it using: $INSTALL_COMMAND_MCP_INSPECTOR"
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
        echo "   You can install it using: $INSTALL_COMMAND_UV"
        return 1
    fi
}

# Validate prerequisites for MCP Knowledge testing
validate_mcp_knowledge_prerequisites() {
    echo "🔍 Validating MCP Knowledge testing prerequisites..."

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

    # Check that jq is available for JSON processing
    if ! command -v jq >/dev/null 2>&1; then
        echo "❌ jq is not available. Please install it for JSON processing."
        errors=$((errors + 1))
    else
        echo "✅ jq is available"
    fi

    if [ $errors -eq 0 ]; then
        echo "✅ All prerequisites validated successfully"
        return 0
    else
        echo "❌ $errors prerequisite(s) failed validation"
        return 1
    fi
}
