#!/bin/bash

# Comprehensive MCP Inspector validation for all ECS security analysis tools
# This script tests all the security analysis tools against the ECS infrastructure created by 01_create.sh
# Usage: ./02_validate.sh [cluster-name]

# Set script location and source utilities
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/utils/mcp_security_helpers.sh"
source "$DIR/utils/security_validation_helpers.sh"

# Parse command line arguments - cluster name is optional, will auto-detect if not provided
CLUSTER_NAME="$1"

# Auto-detect cluster if not provided
if [ -z "$CLUSTER_NAME" ]; then
    CLUSTERS=$(aws ecs list-clusters --query 'clusterArns[*]' --output text 2>/dev/null)
    for CLUSTER_ARN in $CLUSTERS; do
        TEMP_CLUSTER_NAME=$(echo "$CLUSTER_ARN" | awk -F/ '{print $2}')
        if [[ "$TEMP_CLUSTER_NAME" == *"mcp-security-test-cluster"* ]]; then
            CLUSTER_NAME="$TEMP_CLUSTER_NAME"
            break
        fi
    done

    if [ -z "$CLUSTER_NAME" ]; then
        echo "❌ Could not find mcp-security-test-cluster. Please provide cluster name or run 01_create.sh first."
        exit 1
    fi

    echo "🔍 Auto-detected cluster: $CLUSTER_NAME"
fi

# Auto-detect service name
SERVICE_NAME=""
SERVICES=$(aws ecs list-services --cluster "$CLUSTER_NAME" --query 'serviceArns[*]' --output text 2>/dev/null)
for SERVICE_ARN in $SERVICES; do
    TEMP_SERVICE_NAME=$(echo "$SERVICE_ARN" | awk -F/ '{print $3}')
    if [[ "$TEMP_SERVICE_NAME" == *"mcp-security-test-service"* ]]; then
        SERVICE_NAME="$TEMP_SERVICE_NAME"
        break
    fi
done

echo "🔍 Auto-detected service: $SERVICE_NAME"

# Get current region
REGION=$(aws configure get region)
echo "🔍 Using region: $REGION"

# Initialize test tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

echo "🧪 Starting comprehensive MCP Inspector security analysis tool tests..."
echo "   Cluster: $CLUSTER_NAME"
echo "   Service: $SERVICE_NAME"
echo "   Region: $REGION"
echo ""

# Validate prerequisites
echo "🔍 Validating prerequisites..."
if ! validate_mcp_security_prerequisites; then
    echo "❌ Prerequisites validation failed. Exiting."
    exit 1
fi
echo ""

echo ""
echo "🧪 Starting MCP Inspector security analysis tool validation tests..."
echo ""

# Create log file for this test run
LOG_FILE="$DIR/security-test-results-$(date +%Y%m%d_%H%M%S).log"

# Test 1: list_clusters
echo "=================================================================================="
echo "TEST 1: list_clusters"
echo "=================================================================================="
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo "🔍 Running list_clusters..."

RESPONSE1=$(test_security_list_clusters "$REGION")
TEST1_EXIT_CODE=$?

# Log and show assertions
log_security_tool_response "$RESPONSE1" "list_clusters" "$LOG_FILE"

if [ $TEST1_EXIT_CODE -eq 0 ] && validate_security_list_clusters "$RESPONSE1"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}✅ list_clusters test PASSED${NC}"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}❌ list_clusters test FAILED${NC}"
fi
echo ""

# Test 2: analyze_cluster_security
echo "=================================================================================="
echo "TEST 2: analyze_cluster_security"
echo "=================================================================================="
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo "🔍 Running analyze_cluster_security..."

RESPONSE2=$(test_security_analyze_cluster_security "$CLUSTER_NAME" "$REGION")
TEST2_EXIT_CODE=$?

# Log and show assertions
log_security_tool_response "$RESPONSE2" "analyze_cluster_security" "$LOG_FILE"

if [ $TEST2_EXIT_CODE -eq 0 ] && validate_security_analyze_cluster_security "$RESPONSE2"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}✅ analyze_cluster_security test PASSED${NC}"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}❌ analyze_cluster_security test FAILED${NC}"
fi
echo ""

# Test 3: generate_security_report
echo "=================================================================================="
echo "TEST 3: generate_security_report"
echo "=================================================================================="
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo "🔍 Running generate_security_report..."

RESPONSE3=$(test_security_generate_security_report "$CLUSTER_NAME" "detailed" "$REGION")
TEST3_EXIT_CODE=$?

# Log and show assertions
log_security_tool_response "$RESPONSE3" "generate_security_report" "$LOG_FILE"

if [ $TEST3_EXIT_CODE -eq 0 ] && validate_security_generate_security_report "$RESPONSE3"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}✅ generate_security_report test PASSED${NC}"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}❌ generate_security_report test FAILED${NC}"
fi
echo ""

# Test 4: get_security_recommendations
echo "=================================================================================="
echo "TEST 4: get_security_recommendations"
echo "=================================================================================="
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo "🔍 Running get_security_recommendations..."

RESPONSE4=$(test_security_get_security_recommendations "$CLUSTER_NAME" "high" "$REGION")
TEST4_EXIT_CODE=$?

# Log and show assertions
log_security_tool_response "$RESPONSE4" "get_security_recommendations" "$LOG_FILE"

if [ $TEST4_EXIT_CODE -eq 0 ] && validate_security_get_security_recommendations "$RESPONSE4"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}✅ get_security_recommendations test PASSED${NC}"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}❌ get_security_recommendations test FAILED${NC}"
fi
echo ""

# Test 5: check_compliance_status
echo "=================================================================================="
echo "TEST 5: check_compliance_status"
echo "=================================================================================="
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo "🔍 Running check_compliance_status..."

RESPONSE5=$(test_security_check_compliance_status "$CLUSTER_NAME" "aws-foundational" "$REGION")
TEST5_EXIT_CODE=$?

# Log and show assertions
log_security_tool_response "$RESPONSE5" "check_compliance_status" "$LOG_FILE"

if [ $TEST5_EXIT_CODE -eq 0 ] && validate_security_check_compliance_status "$RESPONSE5"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}✅ check_compliance_status test PASSED${NC}"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}❌ check_compliance_status test FAILED${NC}"
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
    echo "🎉 All MCP Inspector security analysis tool tests completed successfully!"
    echo "The scenario validation is complete and all 5 security analysis actions are working correctly."
    exit 0
else
    echo ""
    echo "❌ Some tests failed. Check the output above for details."
    exit 1
fi
