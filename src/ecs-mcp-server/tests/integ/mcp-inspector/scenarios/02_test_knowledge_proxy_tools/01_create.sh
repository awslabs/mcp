#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures

# AWS Knowledge Proxy Tools Integration Test - Prerequisites Phase
# This script validates prerequisites for testing AWS Knowledge proxy integration

# Set script location as base directory
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/mcp_knowledge_helpers.sh"

# Print header
echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}   AWS Knowledge Proxy Tools - Prerequisites Check    ${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo ""

# Validate prerequisites
echo -e "${BLUE}🔍 Validating prerequisites...${NC}"
if ! validate_mcp_knowledge_prerequisites; then
    echo ""
    echo -e "${RED}❌ Prerequisites validation failed.${NC}"
    echo -e "${RED}   Please fix the issues above before running the validation tests.${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Prerequisites validation completed!${NC}"
echo ""

exit 0
