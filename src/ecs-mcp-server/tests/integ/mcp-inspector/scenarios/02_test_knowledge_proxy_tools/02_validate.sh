#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures

# AWS Knowledge Proxy Tools Integration Test - Validation Phase
# This script validates all AWS Knowledge MCP tools via MCP Inspector CLI
# Usage: ./02_validate.sh

# Set script location and source utilities
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/mcp_knowledge_helpers.sh"
source "$SCRIPT_DIR/utils/knowledge_validation_helpers.sh"

# =============================================================================
# CONSTANTS
# =============================================================================
# Test configuration
readonly EXPECTED_NUM_KNOWLEDGE_TOOLS=3
readonly MAX_RESPONSE_TIME_SECONDS=10 # Typical response time is 5-7 seconds
readonly LOG_FILE_PREFIX="knowledge-proxy-test-results"
readonly ECS_WELCOME_URL="https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html"
readonly ECS_SERVICES_URL="https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_services.html"

# Test queries
readonly SEARCH_QUERY_GENERAL="ECS service deployment"
readonly SEARCH_QUERY_BLUE_GREEN="ECS native blue-green deployments"
readonly SEARCH_QUERY_PERFORMANCE="ECS"

# Initialize test tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Create log file for this test run
readonly LOG_FILE="$SCRIPT_DIR/$LOG_FILE_PREFIX-$(date +%Y%m%d_%H%M%S).log"

# Print header
echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}    AWS Knowledge Proxy Tools - Integration Tests     ${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo ""

echo -e "${YELLOW}📋 Test Scenario: AWS Knowledge Proxy Integration${NC}"
echo ""
echo "This comprehensive test validates the AWS Knowledge MCP Server proxy"
echo "integration, including tool availability, descriptions, and functionality."
echo ""
echo -e "${BLUE}📋 Full tool responses logged to: $LOG_FILE${NC}"
echo ""

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

# Run a single functional test for an AWS Knowledge tool with proper output ordering
# Usage: run_functional_test <test_number> <test_description> <tool_call_function> <validator_function>
run_functional_test() {
    local test_number="$1"
    local test_description="$2"
    local tool_call_function="$3"
    local validator_function="$4"

    echo "================================================================================="
    echo "TEST ${test_number}: ${test_description}"
    echo "================================================================================="
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    # Execute tool call (this will print the "🔧 Calling..." message in correct order)
    local response
    response=$("${tool_call_function}")
    local call_exit_code=$?

    # Log response details
    log_knowledge_tool_response "${response}" "${test_number}" "${LOG_FILE}"

    # Validate response
    if [ $call_exit_code -eq 0 ] && "${validator_function}" "${response}"; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "${GREEN}✅ ${test_description} PASSED${NC}"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "${RED}❌ ${test_description} FAILED${NC}"
    fi
    echo ""
}

# Execute tool availability test for a specific tool
# Usage: test_tool_availability <tool_name> <test_args...>
test_tool_availability() {
    local tool_name="$1"
    shift
    local test_args=("$@")

    echo -e "${BLUE}  Testing: ${tool_name}${NC}"

    case "${tool_name}" in
        "aws_knowledge_aws___search_documentation")
            test_response=$(test_aws_knowledge_search_documentation "ECS" 2>/dev/null)
            ;;
        "aws_knowledge_aws___read_documentation")
            test_response=$(test_aws_knowledge_read_documentation "${ECS_WELCOME_URL}" 2>/dev/null)
            ;;
        "aws_knowledge_aws___recommend")
            test_response=$(test_aws_knowledge_recommend "${ECS_SERVICES_URL}" 2>/dev/null)
            ;;
        *)
            echo -e "${RED}    ❌ Unknown tool: ${tool_name}${NC}"
            return 1
            ;;
    esac

    if [ $? -eq 0 ] && [ -n "${test_response}" ]; then
        echo -e "${GREEN}    ✅ ${tool_name} is available${NC}"
        return 0
    else
        echo -e "${RED}    ❌ ${tool_name} is not available${NC}"
        return 1
    fi
}

echo "🧪 Starting AWS Knowledge proxy tool validation tests..."
echo ""

# =============================================================================
# TEST 1: AWS Knowledge Tools Availability (via direct calls)
# =============================================================================
echo "================================================================================="
echo "TEST 1: AWS Knowledge Tools Availability Validation"
echo "================================================================================="

echo -e "${BLUE}🔍 Testing availability of EXACTLY ${EXPECTED_NUM_KNOWLEDGE_TOOLS} AWS Knowledge tools via direct calls...${NC}"

# Test availability
tool_availability_count=0

for tool_name in "${EXPECTED_KNOWLEDGE_TOOLS[@]}"; do
    if test_tool_availability "${tool_name}"; then
        tool_availability_count=$((tool_availability_count + 1))
    fi
done

# Now validate exact descriptions (upstream change detection)
TOOLS_LIST_RESPONSE=$(get_mcp_tools)
TOOLS_LIST_EXIT_CODE=$?

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if [ $tool_availability_count -eq $EXPECTED_NUM_KNOWLEDGE_TOOLS ]; then
    echo -e "${GREEN}✅ Exactly ${EXPECTED_NUM_KNOWLEDGE_TOOLS} AWS Knowledge tools are available${NC}"

    # Validate exact descriptions
    if [ $TOOLS_LIST_EXIT_CODE -eq 0 ] && validate_exact_tool_descriptions "$TOOLS_LIST_RESPONSE"; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}❌ ${tool_availability_count} AWS Knowledge tools are available${NC}"
fi
echo ""

# =============================================================================
# TEST 2-4: Functional tests for all AWS Knowledge tools (using helper functions)
# =============================================================================

# Create wrapper functions for proper tool calling
call_search_test() { test_aws_knowledge_search_documentation "${SEARCH_QUERY_GENERAL}"; }
call_read_test() { test_aws_knowledge_read_documentation "${ECS_WELCOME_URL}"; }
call_recommend_test() { test_aws_knowledge_recommend "${ECS_SERVICES_URL}"; }

# Run all functional tests with proper output ordering
run_functional_test "2" "search_documentation functional test" "call_search_test" "validate_aws_knowledge_search_documentation"
run_functional_test "3" "read_documentation functional test" "call_read_test" "validate_aws_knowledge_read_documentation"
run_functional_test "4" "recommend functional test" "call_recommend_test" "validate_aws_knowledge_recommend"

# =============================================================================
# TEST 5: Cross-tool validation - Blue-Green Deployment feature search
# =============================================================================
echo "================================================================================="
echo "TEST 5: Blue-Green Deployment Feature Detection"
echo "================================================================================="
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo -e "${BLUE}🔍 Testing search for new ECS Blue-Green deployment feature...${NC}"

BG_SEARCH_RESPONSE=$(test_aws_knowledge_search_documentation "$SEARCH_QUERY_BLUE_GREEN")
BG_SEARCH_EXIT_CODE=$?

# Log response details
log_knowledge_tool_response "$BG_SEARCH_RESPONSE" "aws_knowledge_aws___search_documentation" "$LOG_FILE"

if [ $BG_SEARCH_EXIT_CODE -eq 0 ] && validate_aws_knowledge_search_documentation "$BG_SEARCH_RESPONSE"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}✅ Blue-Green deployment search PASSED${NC}"

    # Check if results mention blue-green deployments
    tool_result=$(extract_tool_result "$BG_SEARCH_RESPONSE" "bg_search_validation")
    bg_results=$(echo "$tool_result" | jq -r '.content.result[] | select(.title | test("blue.?green|deployment"; "i")) | .title' 2>/dev/null)

    if [ -n "$bg_results" ]; then
        echo -e "${GREEN}✅ Found blue-green deployment related results${NC}"
    else
        echo -e "${YELLOW}⚠️ No specific blue-green deployment results found${NC}"
    fi
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}❌ Blue-Green deployment search FAILED${NC}"
fi
echo ""

# =============================================================================
# TEST 6: Tool response time validation
# =============================================================================
echo "================================================================================="
echo "TEST 6: Tool Response Time Performance"
echo "================================================================================="
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo -e "${BLUE}🔍 Testing tool response times...${NC}"

# Time a simple search operation
START_TIME=$(date +%s)
PERF_RESPONSE=$(test_aws_knowledge_search_documentation "$SEARCH_QUERY_PERFORMANCE")
PERF_EXIT_CODE=$?
END_TIME=$(date +%s)

RESPONSE_TIME=$((END_TIME - START_TIME))

if [ $PERF_EXIT_CODE -eq 0 ] && [ $RESPONSE_TIME -lt $MAX_RESPONSE_TIME_SECONDS ]; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}✅ Tool response time acceptable (less than ${MAX_RESPONSE_TIME_SECONDS}s): ${RESPONSE_TIME}s${NC}"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    if [ $RESPONSE_TIME -ge $MAX_RESPONSE_TIME_SECONDS ]; then
        echo -e "${RED}❌ Tool response time too slow: ${RESPONSE_TIME}s (>${MAX_RESPONSE_TIME_SECONDS}s)${NC}"
    else
        echo -e "${RED}❌ Tool response failed${NC}"
    fi
fi
echo ""

# =============================================================================
# Print final summary
# =============================================================================
echo "================================================================================="
print_validation_summary $TOTAL_TESTS $PASSED_TESTS $FAILED_TESTS
echo "================================================================================="
echo ""
echo "📋 Full tool responses logged to: $LOG_FILE"


# Exit with appropriate code
if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}🎉 All AWS Knowledge proxy integration tests passed!${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}❌ $FAILED_TESTS test(s) failed. Check the output above for details.${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting tips:${NC}"
    echo "  • Check MCP server configuration in /tmp/mcp-config.json"
    echo "  • Review full responses in log file: $LOG_FILE"
    echo ""
    exit 1
fi
