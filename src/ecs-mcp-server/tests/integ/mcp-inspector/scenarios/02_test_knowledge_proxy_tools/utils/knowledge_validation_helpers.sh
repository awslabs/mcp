#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures

# JSON Response Validation Helper Functions for AWS Knowledge Tools
# This file contains utility functions for validating JSON responses from AWS Knowledge MCP tools

# Expected AWS Knowledge tool names
EXPECTED_KNOWLEDGE_TOOLS=(
    "aws_knowledge_aws___search_documentation"
    "aws_knowledge_aws___read_documentation"
    "aws_knowledge_aws___recommend"
)

# Expected exact tool descriptions (upstream + ECS_TOOL_GUIDANCE) - for detecting upstream changes
EXPECTED_SEARCH_DESCRIPTION="Search AWS documentation using the official AWS Documentation Search API.

    ## Usage

    This tool searches across all AWS documentation and other AWS Websites including AWS Blog, AWS Solutions Library, Getting started with AWS, AWS Architecture Center and AWS Prescriptive Guidance for pages matching your search phrase.
    Use it to find relevant documentation when you don't have a specific URL.

    ## Search Tips

    - Use specific technical terms rather than general phrases
    - Include service names to narrow results (e.g., \"S3 bucket versioning\" instead of just \"versioning\")
    - Use quotes for exact phrase matching (e.g., \"AWS Lambda function URLs\")
    - Include abbreviations and alternative terms to improve results

    ## Result Interpretation

    Each result includes:
    - rank_order: The relevance ranking (lower is more relevant)
    - url: The documentation page URL
    - title: The page title
    - context: A brief excerpt or summary (if available)

    ## ECS DOCUMENTATION GUIDANCE:
    This tool provides up-to-date ECS documentation and implementation guidance, including new ECS features beyond standard LLM training data.

    New ECS features include:
    - ECS Native Blue-Green Deployments (different from CodeDeploy blue-green, launched 2025)"

EXPECTED_READ_DESCRIPTION="Fetch and convert an AWS documentation page to markdown format.

    ## Usage

    This tool retrieves the content of an AWS documentation page and converts it to markdown format.
    For long documents, you can make multiple calls with different start_index values to retrieve
    the entire content in chunks.

    ## URL Requirements

    - Must be from the docs.aws.amazon.com or aws.amazon.com domain

    ## Example URLs

    - https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html
    - https://docs.aws.amazon.com/lambda/latest/dg/lambda-invocation.html
    - https://aws.amazon.com/about-aws/whats-new/2023/02/aws-telco-network-builder/
    - https://aws.amazon.com/builders-library/ensuring-rollback-safety-during-deployments/
    - https://aws.amazon.com/blogs/developer/make-the-most-of-community-resources-for-aws-sdks-and-tools/

    ## Output Format

    The output is formatted as markdown text with:
    - Preserved headings and structure
    - Code blocks for examples
    - Lists and tables converted to markdown format

    ## Handling Long Documents

    If the response indicates the document was truncated, you have several options:

    1. **Continue Reading**: Make another call with start_index set to the end of the previous response
    2. **Stop Early**: For very long documents (>30,000 characters), if you've already found the specific information needed, you can stop reading

    ## ECS DOCUMENTATION GUIDANCE:
    This tool provides up-to-date ECS documentation and implementation guidance, including new ECS features beyond standard LLM training data.

    New ECS features include:
    - ECS Native Blue-Green Deployments (different from CodeDeploy blue-green, launched 2025)"

EXPECTED_RECOMMEND_DESCRIPTION="Get content recommendations for an AWS documentation page.

    ## Usage

    This tool provides recommendations for related AWS documentation pages based on a given URL.
    Use it to discover additional relevant content that might not appear in search results.
    URL must be from the docs.aws.amazon.com domain.

    ## Recommendation Types

    The recommendations include four categories:

    1. **Highly Rated**: Popular pages within the same AWS service
    2. **New**: Recently added pages within the same AWS service - useful for finding newly released features
    3. **Similar**: Pages covering similar topics to the current page
    4. **Journey**: Pages commonly viewed next by other users

    ## When to Use

    - After reading a documentation page to find related content
    - When exploring a new AWS service to discover important pages
    - To find alternative explanations of complex concepts
    - To discover the most popular pages for a service
    - To find newly released information by using a service's welcome page URL and checking the **New** recommendations

    ## Finding New Features

    To find newly released information about a service:
    1. Find any page belong to that service, typically you can try the welcome page
    2. Call this tool with that URL
    3. Look specifically at the **New** recommendation type in the results

    ## Result Interpretation

    Each recommendation includes:
    - url: The documentation page URL
    - title: The page title
    - context: A brief description (if available)

    ## ECS DOCUMENTATION GUIDANCE:
    This tool provides up-to-date ECS documentation and implementation guidance, including new ECS features beyond standard LLM training data.

    New ECS features include:
    - ECS Native Blue-Green Deployments (different from CodeDeploy blue-green, launched 2025)"

# Validate that a response is valid JSON
validate_json() {
    local response="$1"
    local tool_name="$2"

    if [ -z "${response}" ]; then
        echo -e "${RED}❌ [${tool_name}] Empty response${NC}" >&2
        return 1
    fi

    # Try to parse JSON with jq
    if echo "${response}" | jq . >/dev/null 2>&1; then
        echo -e "${GREEN}✅ [${tool_name}] Valid JSON response${NC}" >&2
        return 0
    else
        echo -e "${RED}❌ [${tool_name}] Invalid JSON response${NC}" >&2
        echo "First 500 chars of response: ${response:0:500}..." >&2
        return 1
    fi
}

# Extract tool result from MCP response format
extract_tool_result() {
    local response="$1"

    # Extract tool result from MCP content array
    local tool_result
    tool_result=$(echo "${response}" | jq -r '.content[0].text // empty' 2>/dev/null)

    if [ -n "${tool_result}" ] && [ "${tool_result}" != "null" ]; then
        echo "${tool_result}"
        return 0
    else
        return 1
    fi
}

# Validate a single tool description against expected value
validate_single_tool_description() {
    local tools_array="$1"
    local tool_name="$2"
    local expected_description="$3"
    local display_name="$4"

    local actual_desc
    actual_desc=$(echo "$tools_array" | jq -r ".[] | select(.name == \"$tool_name\") | .description" 2>/dev/null)

    if [ "$actual_desc" = "$expected_description" ]; then
        echo -e "${GREEN}✅ $display_name description matches exactly${NC}"
        return 0
    else
        echo -e "${RED}❌ $display_name description mismatch (upstream change detected!)${NC}"
        echo -e "${YELLOW}Expected length: ${#expected_description} chars${NC}"
        echo -e "${YELLOW}Actual length: ${#actual_desc} chars${NC}"
        return 1
    fi
}

# Validate all tool descriptions against expected values
validate_all_tool_descriptions() {
    local tools_array="$1"
    local exact_match_count=0

    # Test search_documentation description
    if validate_single_tool_description "$tools_array" "aws_knowledge_aws___search_documentation" "$EXPECTED_SEARCH_DESCRIPTION" "search_documentation"; then
        exact_match_count=$((exact_match_count + 1))
    fi

    # Test read_documentation description
    if validate_single_tool_description "$tools_array" "aws_knowledge_aws___read_documentation" "$EXPECTED_READ_DESCRIPTION" "read_documentation"; then
        exact_match_count=$((exact_match_count + 1))
    fi

    # Test recommend description
    if validate_single_tool_description "$tools_array" "aws_knowledge_aws___recommend" "$EXPECTED_RECOMMEND_DESCRIPTION" "recommend"; then
        exact_match_count=$((exact_match_count + 1))
    fi

    return $exact_match_count
}

# Validate tool descriptions match exactly to what we expect.
# This serves as an early warning system for upstream AWS Knowledge MCP Server updates.
validate_exact_tool_descriptions() {
    local tools_response="$1"

    echo -e "${BLUE}🔍 Validating exact tool descriptions (upstream change detection)...${NC}"

    if ! validate_json "$tools_response" "tools/list"; then
        return 1
    fi

    # Extract tools array from response
    local tools_array
    tools_array=$(echo "$tools_response" | jq -r '.tools' 2>/dev/null)

    # Validate each tool description exactly
    local exact_match_count
    validate_all_tool_descriptions "$tools_array"
    exact_match_count=$?

    local expected_count=${#EXPECTED_KNOWLEDGE_TOOLS[@]}
    if [ $exact_match_count -eq $expected_count ]; then
        echo -e "${GREEN}✅ All tool descriptions match exactly - no upstream changes detected${NC}"
        return 0
    else
        echo -e "${RED}❌ $((expected_count - exact_match_count)) tool description(s) don't match - upstream changes detected!${NC}"
        return 1
    fi
}

# Generic tool response validation function
validate_tool_response_structure() {
    local response="$1"
    local tool_name="$2"
    local display_name="$3"

    echo -e "${BLUE}🔍 Validating $display_name response...${NC}" >&2

    if ! validate_json "$response" "$tool_name"; then
        return 1
    fi

    local tool_result
    if ! tool_result=$(extract_tool_result "$response"); then
        echo -e "${RED}❌ [$tool_name] Failed to extract tool result${NC}" >&2
        return 1
    fi

    # Check if tool result has content.result structure
    local has_content_result
    has_content_result=$(echo "$tool_result" | jq -r '.content | has("result")' 2>/dev/null)

    if [ "$has_content_result" = "true" ]; then
        echo "$tool_result"
        return 0
    else
        echo -e "${RED}❌ [$tool_name] Response missing 'content.result' field${NC}" >&2
        return 1
    fi
}

# Validate search documentation content
validate_search_content() {
    local tool_result="$1"
    local tool_name="$2"

    local result_count
    result_count=$(echo "$tool_result" | jq -r '.content.result | length' 2>/dev/null)

    if [ "$result_count" -gt 0 ]; then
        echo -e "${GREEN}✅ [$tool_name] Found $result_count search results${NC}"
        return 0
    else
        echo -e "${RED}❌ [$tool_name] No search results returned${NC}"
        return 1
    fi
}

# Validate read documentation content
validate_read_content() {
    local tool_result="$1"
    local tool_name="$2"

    local content
    content=$(echo "$tool_result" | jq -r '.content.result // empty' 2>/dev/null)

    if [ -n "$content" ] && [ "$content" != "null" ]; then
        local content_length=${#content}
        echo -e "${GREEN}✅ [$tool_name] Content retrieved ($content_length chars)${NC}"

        # Check for markdown indicators using array approach for DRY compliance
        local markdown_patterns=(
            '^#+ '                    # Headers
            '\[.*\]\(.*\)'           # Links
            '^(\*|-|\+|\d+\.) '      # Lists
            '```|`.*`'               # Code blocks/inline code
        )

        local markdown_indicators=0
        for pattern in "${markdown_patterns[@]}"; do
            if echo "$content" | grep -E "$pattern" >/dev/null 2>&1; then
                markdown_indicators=$((markdown_indicators + 1))
            fi
        done

        local min_indicators=2
        if [ $markdown_indicators -ge $min_indicators ]; then
            echo -e "${GREEN}✅ [$tool_name] Content is properly markdown formatted (${markdown_indicators} indicators)${NC}"
        else
            echo -e "${YELLOW}⚠️ [$tool_name] Content may not be fully markdown formatted (${markdown_indicators} indicators)${NC}"
        fi

        return 0
    else
        echo -e "${RED}❌ [$tool_name] Empty or null content${NC}"
        return 1
    fi
}

# Validate recommend documentation content
validate_recommend_content() {
    local tool_result="$1"
    local tool_name="$2"

    local recommendation_count
    recommendation_count=$(echo "$tool_result" | jq -r '.content.result | length' 2>/dev/null)

    if [ "$recommendation_count" -gt 0 ]; then
        echo -e "${GREEN}✅ [$tool_name] Found $recommendation_count recommendations${NC}"
        return 0
    else
        echo -e "${RED}❌ [$tool_name] No recommendations returned${NC}"
        return 1
    fi
}

# Validate search documentation response
validate_aws_knowledge_search_documentation() {
    local response="$1"
    local tool_result

    if tool_result=$(validate_tool_response_structure "$response" "search_documentation" "aws_knowledge_aws___search_documentation"); then
        validate_search_content "$tool_result" "search_documentation"
    else
        return 1
    fi
}

# Validate read documentation response
validate_aws_knowledge_read_documentation() {
    local response="$1"
    local tool_result

    if tool_result=$(validate_tool_response_structure "$response" "read_documentation" "aws_knowledge_aws___read_documentation"); then
        validate_read_content "$tool_result" "read_documentation"
    else
        return 1
    fi
}

# Validate recommend documentation response
validate_aws_knowledge_recommend() {
    local response="$1"
    local tool_result

    if tool_result=$(validate_tool_response_structure "$response" "recommend" "aws_knowledge_aws___recommend"); then
        validate_recommend_content "$tool_result" "recommend"
    else
        return 1
    fi
}


# Print validation summary
print_validation_summary() {
    local total_tests="$1"
    local passed_tests="$2"
    local failed_tests="$3"

    echo ""
    echo "=================================================="
    echo "       AWS KNOWLEDGE VALIDATION SUMMARY"
    echo "=================================================="
    echo -e "Total tests:  $total_tests"
    echo -e "Passed tests: ${GREEN}$passed_tests${NC}"
    echo -e "Failed tests: ${RED}$failed_tests${NC}"
    echo "=================================================="

    if [ $failed_tests -eq 0 ]; then
        echo -e "${GREEN}🎉 All AWS Knowledge validation tests passed!${NC}"
        return 0
    else
        echo -e "${RED}❌ $failed_tests AWS Knowledge validation test(s) failed${NC}"
        return 1
    fi
}

# Log tool response with formatting
log_knowledge_tool_response() {
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

    # Show key information on stdout based on tool type
    case "$tool_name" in
        "aws_knowledge_aws___search_documentation")
            local result_count=$(echo "$tool_json" | jq -r '.content.result | length' 2>/dev/null)
            local first_title=$(echo "$tool_json" | jq -r '.content.result[0].title' 2>/dev/null)

            echo "✓ Search results: $result_count"
            echo "✓ First result: $first_title"
            ;;
        "aws_knowledge_aws___read_documentation")
            local content_length=$(echo "$tool_json" | jq -r '.content.result | length' 2>/dev/null)
            local has_headings=$(echo "$tool_json" | jq -r '.content.result' | grep -c '^#' 2>/dev/null || echo "0")

            echo "✓ Content length: $content_length chars"
            echo "✓ Markdown headings found: $has_headings"
            ;;
        "aws_knowledge_aws___recommend")
            local rec_count=$(echo "$tool_json" | jq -r '.content.result | length' 2>/dev/null)
            local first_rec_title=$(echo "$tool_json" | jq -r '.content.result[0].title' 2>/dev/null)

            echo "✓ Recommendations: $rec_count"
            echo "✓ First recommendation: $first_rec_title"
            ;;
    esac
}
