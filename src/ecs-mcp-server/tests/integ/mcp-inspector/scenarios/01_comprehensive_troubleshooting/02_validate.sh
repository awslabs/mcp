#!/bin/bash

# Comprehensive MCP Inspector validation for all ECS troubleshooting tools
# This script tests all the troubleshooting tools against the ECS infrastructure created by 01_create.sh
# Usage: ./02_validate.sh [cluster-name]

# Set script location and source utilities
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/utils/mcp_helpers.sh"
source "$DIR/utils/validation_helpers.sh"

# Function to log tool response and show simple assertion results
log_and_assert_tool_response() {
    local response="$1"
    local tool_name="$2"
    local log_file="$3"

    # Extract the actual tool JSON from the MCP wrapper
    local tool_json=$(echo "$response" | jq -r '.content[0].text' 2>/dev/null)

    # Log full response to file
    {
        echo "📋 $tool_name Full Response:"
        echo "=========================================="
        echo "$tool_json" | jq . 2>/dev/null || echo "$tool_json"
        echo ""
    } >> "$log_file"

    # Show simple assertions on stdout based on tool type
    case "$tool_name" in
        "get_ecs_troubleshooting_guidance")
            local cluster_name=$(echo "$tool_json" | jq -r '.raw_data.cluster_details[0].name' 2>/dev/null)
            local service_name=$(echo "$tool_json" | jq -r '.raw_data.service_details[0].name' 2>/dev/null)
            local active_services=$(echo "$tool_json" | jq -r '.raw_data.cluster_details[0].activeServicesCount' 2>/dev/null)
            local desired_count=$(echo "$tool_json" | jq -r '.raw_data.service_details[0].desiredCount' 2>/dev/null)

            echo "✓ Cluster name: $cluster_name"
            echo "✓ Service name: $service_name"
            echo "✓ Active services count: $active_services"
            echo "✓ Desired service count: $desired_count"
            ;;
        "detect_image_pull_failures")
            local status=$(echo "$tool_json" | jq -r '.status' 2>/dev/null)
            local issues_count=$(echo "$tool_json" | jq -r '.image_issues | length' 2>/dev/null)

            echo "✓ Status: $status"
            echo "✓ Image issues count: $issues_count"
            ;;
        "fetch_service_events")
            local service_exists=$(echo "$tool_json" | jq -r '.service_exists' 2>/dev/null)
            local desired_count=$(echo "$tool_json" | jq -r '.raw_data.service.desiredCount' 2>/dev/null)

            echo "✓ Service exists: $service_exists"
            echo "✓ Service desired count: $desired_count"
            ;;
        "fetch_task_failures")
            local cluster_exists=$(echo "$tool_json" | jq -r '.cluster_exists' 2>/dev/null)
            local task_def=$(echo "$tool_json" | jq -r '.failed_tasks[0].task_definition' 2>/dev/null)

            echo "✓ Cluster exists: $cluster_exists"
            echo "✓ Failed task definition: $task_def"
            ;;
        "fetch_task_logs")
            local status=$(echo "$tool_json" | jq -r '.status' 2>/dev/null)
            local log_entries_count=$(echo "$tool_json" | jq -r '.log_entries | length' 2>/dev/null)

            echo "✓ Status: $status"
            echo "✓ Log entries count: $log_entries_count"
            ;;
        "fetch_network_configuration")
            local status=$(echo "$tool_json" | jq -r '.status' 2>/dev/null)
            local cluster_name=$(echo "$tool_json" | jq -r '.data.clusters[0]' 2>/dev/null)

            echo "✓ Status: $status"
            echo "✓ Cluster found: $cluster_name"
            ;;
    esac
}


# Parse command line arguments - cluster name is optional, will auto-detect if not provided
CLUSTER_NAME="$1"

# Auto-detect cluster if not provided
if [ -z "$CLUSTER_NAME" ]; then
    CLUSTERS=$(aws ecs list-clusters --query 'clusterArns[*]' --output text 2>/dev/null)
    for CLUSTER_ARN in $CLUSTERS; do
        TEMP_CLUSTER_NAME=$(echo "$CLUSTER_ARN" | awk -F/ '{print $2}')
        if [[ "$TEMP_CLUSTER_NAME" == *"mcp-integration-test-cluster"* ]]; then
            CLUSTER_NAME="$TEMP_CLUSTER_NAME"
            break
        fi
    done

    if [ -z "$CLUSTER_NAME" ]; then
        echo "❌ Could not find mcp-integration-test-cluster. Please provide cluster name or run 01_create.sh first."
        exit 1
    fi

    echo "🔍 Auto-detected cluster: $CLUSTER_NAME"
fi

# Auto-detect service name
SERVICE_NAME=""
SERVICES=$(aws ecs list-services --cluster "$CLUSTER_NAME" --query 'serviceArns[*]' --output text 2>/dev/null)
for SERVICE_ARN in $SERVICES; do
    TEMP_SERVICE_NAME=$(echo "$SERVICE_ARN" | awk -F/ '{print $3}')
    if [[ "$TEMP_SERVICE_NAME" == *"mcp-integration-test-service"* ]]; then
        SERVICE_NAME="$TEMP_SERVICE_NAME"
        break
    fi
done

echo "🔍 Auto-detected service: $SERVICE_NAME"

# Auto-detect VPC
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text 2>/dev/null)
if [ -n "$VPC_ID" ] && [ "$VPC_ID" != "None" ]; then
    echo "🔍 Auto-detected VPC: $VPC_ID"
fi

# Initialize test tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

echo "🧪 Starting comprehensive MCP Inspector troubleshooting tool tests..."
echo "   Cluster: $CLUSTER_NAME"
echo "   Service: $SERVICE_NAME"
echo "   Task Family: $TASK_FAMILY"
echo "   VPC: $VPC_ID"
echo ""

# Validate prerequisites
echo "🔍 Validating prerequisites..."
if ! validate_mcp_prerequisites; then
    echo "❌ Prerequisites validation failed. Exiting."
    exit 1
fi
echo ""

echo ""
echo "🧪 Starting MCP Inspector troubleshooting tool validation tests..."
echo ""

# Test 1: get_ecs_troubleshooting_guidance
echo "=================================================================================="
echo "TEST 1: get_ecs_troubleshooting_guidance"
echo "=================================================================================="
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo "🔍 Running get_ecs_troubleshooting_guidance..."

# Create log file for this test run
LOG_FILE="$DIR/test-results-$(date +%Y%m%d_%H%M%S).log"

RESPONSE1=$(test_get_ecs_troubleshooting_guidance "$CLUSTER_NAME" "$SERVICE_NAME" "Tasks failing to start due to network restrictions")
TEST1_EXIT_CODE=$?

# Log and show assertions
log_and_assert_tool_response "$RESPONSE1" "get_ecs_troubleshooting_guidance" "$LOG_FILE"

if [ $TEST1_EXIT_CODE -eq 0 ] && validate_get_ecs_troubleshooting_guidance "$RESPONSE1"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}✅ get_ecs_troubleshooting_guidance test PASSED${NC}"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}❌ get_ecs_troubleshooting_guidance test FAILED${NC}"
fi
echo ""

# Test 2: detect_image_pull_failures
echo "=================================================================================="
echo "TEST 2: detect_image_pull_failures"
echo "=================================================================================="
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo "🔍 Running detect_image_pull_failures..."

RESPONSE2=$(test_detect_image_pull_failures "$CLUSTER_NAME" "$SERVICE_NAME" "")
TEST2_EXIT_CODE=$?

# Log and show assertions
log_and_assert_tool_response "$RESPONSE2" "detect_image_pull_failures" "$LOG_FILE"

if [ $TEST2_EXIT_CODE -eq 0 ] && validate_detect_image_pull_failures "$RESPONSE2"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}✅ detect_image_pull_failures test PASSED${NC}"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}❌ detect_image_pull_failures test FAILED${NC}"
fi
echo ""

# Test 3: fetch_service_events
echo "=================================================================================="
echo "TEST 3: fetch_service_events"
echo "=================================================================================="
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo "🔍 Running fetch_service_events..."

RESPONSE3=$(test_fetch_service_events "$CLUSTER_NAME" "$SERVICE_NAME" "3600")
TEST3_EXIT_CODE=$?

# Log and show assertions
log_and_assert_tool_response "$RESPONSE3" "fetch_service_events" "$LOG_FILE"

if [ $TEST3_EXIT_CODE -eq 0 ] && validate_fetch_service_events "$RESPONSE3"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}✅ fetch_service_events test PASSED${NC}"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}❌ fetch_service_events test FAILED${NC}"
fi
echo ""

# Test 4: fetch_task_failures
echo "=================================================================================="
echo "TEST 4: fetch_task_failures"
echo "=================================================================================="
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo "🔍 Running fetch_task_failures..."

RESPONSE4=$(test_fetch_task_failures "$CLUSTER_NAME" "3600")
TEST4_EXIT_CODE=$?

# Log and show assertions
log_and_assert_tool_response "$RESPONSE4" "fetch_task_failures" "$LOG_FILE"

if [ $TEST4_EXIT_CODE -eq 0 ] && validate_fetch_task_failures "$RESPONSE4"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}✅ fetch_task_failures test PASSED${NC}"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}❌ fetch_task_failures test FAILED${NC}"
fi
echo ""

# Test 5: fetch_task_logs
echo "=================================================================================="
echo "TEST 5: fetch_task_logs"
echo "=================================================================================="
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo "🔍 Running fetch_task_logs..."

RESPONSE5=$(test_fetch_task_logs "$CLUSTER_NAME" "" "" "3600")
TEST5_EXIT_CODE=$?

# Log and show assertions
log_and_assert_tool_response "$RESPONSE5" "fetch_task_logs" "$LOG_FILE"

if [ $TEST5_EXIT_CODE -eq 0 ] && validate_fetch_task_logs "$RESPONSE5"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}✅ fetch_task_logs test PASSED${NC}"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}❌ fetch_task_logs test FAILED${NC}"
fi
echo ""

# Test 6: fetch_network_configuration
echo "=================================================================================="
echo "TEST 6: fetch_network_configuration"
echo "=================================================================================="
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo "🔍 Running fetch_network_configuration..."

RESPONSE6=$(test_fetch_network_configuration "$VPC_ID" "$CLUSTER_NAME")
TEST6_EXIT_CODE=$?

# Log and show assertions
log_and_assert_tool_response "$RESPONSE6" "fetch_network_configuration" "$LOG_FILE"

if [ $TEST6_EXIT_CODE -eq 0 ] && validate_fetch_network_configuration "$RESPONSE6"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}✅ fetch_network_configuration test PASSED${NC}"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}❌ fetch_network_configuration test FAILED${NC}"
fi
echo ""

# Print final summary
echo "=================================================================================="
print_validation_summary $TOTAL_TESTS $PASSED_TESTS $FAILED_TESTS
echo "=================================================================================="
echo ""
echo "📋 Full tool responses logged to: $LOG_FILE"

# Exit with appropriate code
if [ $FAILED_TESTS -eq 0 ]; then
    echo ""
    echo "🎉 All MCP Inspector troubleshooting tool tests completed successfully!"
    echo "The scenario validation is complete and all 6 tools are working correctly."
    exit 0
else
    echo ""
    echo "❌ Some tests failed. Check the output above for details."
    exit 1
fi
