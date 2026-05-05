#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures

# AWS Knowledge Proxy Tools Integration Test - Cleanup Phase
# This script performs cleanup after AWS Knowledge proxy integration tests
# Since no AWS infrastructure is created, cleanup is minimal

# Set script location as base directory
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/mcp_knowledge_helpers.sh"

# =============================================================================
# CONSTANTS
# =============================================================================
# File patterns for cleanup
readonly LOG_FILE_PATTERN="knowledge-proxy-test-results-*.log"
readonly TEMP_JSON_PATTERN="*.tmp.json"

# Print header
echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}   AWS Knowledge Proxy Tools - Cleanup Phase          ${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo ""

echo -e "${YELLOW}📋 Cleanup Scenario: AWS Knowledge Proxy Integration${NC}"
echo ""
echo "This cleanup phase removes temporary files and logs created during"
echo "the AWS Knowledge proxy integration testing."
echo ""

# Clean up temporary log files
echo -e "${BLUE}🧹 Cleaning up temporary files...${NC}"

# Count log files to clean
LOG_FILES_COUNT=$(ls "$SCRIPT_DIR"/$LOG_FILE_PATTERN 2>/dev/null | wc -l)

if [ "$LOG_FILES_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}Found $LOG_FILES_COUNT log file(s) to clean up:${NC}"
    for log_file in "$SCRIPT_DIR"/$LOG_FILE_PATTERN; do
        if [ -f "$log_file" ]; then
            echo "  • $(basename "$log_file")"
        fi
    done

    echo ""
    read -p "Do you want to remove these log files? (y/n) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f "$SCRIPT_DIR"/$LOG_FILE_PATTERN
        echo -e "${GREEN}✅ Removed $LOG_FILES_COUNT log file(s)${NC}"
    else
        echo -e "${YELLOW}⚠️ Log files preserved for review${NC}"
    fi
else
    echo -e "${GREEN}✅ No temporary log files found to clean up${NC}"
fi

echo ""

# Clean up any temporary JSON files (if created during testing)
TEMP_JSON_COUNT=$(ls "$SCRIPT_DIR"/$TEMP_JSON_PATTERN 2>/dev/null | wc -l)

if [ "$TEMP_JSON_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}Found $TEMP_JSON_COUNT temporary JSON file(s) to clean up${NC}"
    rm -f "$SCRIPT_DIR"/$TEMP_JSON_PATTERN
    echo -e "${GREEN}✅ Removed temporary JSON files${NC}"
else
    echo -e "${GREEN}✅ No temporary JSON files found to clean up${NC}"
fi

echo ""
echo -e "${GREEN}=======================================================${NC}"
echo -e "${GREEN}🎉 AWS Knowledge proxy cleanup completed!${NC}"
echo -e "${GREEN}=======================================================${NC}"
echo ""
echo -e "${YELLOW}Summary:${NC}"
echo "  • Temporary log files processed"
echo "  • No AWS resources get created for this test"
echo "  • Test environment is clean"
echo ""

exit 0
