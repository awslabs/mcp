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
EXPECTED_SEARCH_DESCRIPTION=$(cat <<'SEARCH_DESC_EOF'
# AWS Documentation Search Tool
This is your primary source for AWS information—always prefer this over general knowledge for AWS services, features, configurations, troubleshooting, and best practices.

## When to Use This Tool

**Always search when the query involves:**
- Any AWS service or feature (Lambda, S3, EC2, RDS, etc.)
- AWS architecture, patterns, or best practices
- AWS CLI, SDK, or API usage
- AWS CDK or CloudFormation
- AWS Amplify development
- AWS errors or troubleshooting
- AWS pricing, limits, or quotas
- "How do I..." questions about AWS
- Recent AWS updates or announcements

**Only skip this tool when:**
- Query is about non-AWS technologies
- Question is purely conceptual (e.g., "What is a database?")
- General programming questions unrelated to AWS

## Quick Topic Selection

| Query Type | Use Topic | Example |
|------------|-----------|---------|
| API/SDK/CLI code | `reference_documentation` | "S3 PutObject boto3", "Lambda invoke API" |
| New features, releases | `current_awareness` | "Lambda new features 2024", "what's new in ECS" |
| Errors, debugging | `troubleshooting` | "AccessDenied S3", "Lambda timeout error" |
| Amplify apps | `amplify_docs` | "Amplify Auth React", "Amplify Storage Flutter" |
| CDK concepts, APIs, CLI | `cdk_docs` | "CDK stack props Python", "cdk deploy command" |
| CDK code samples, patterns | `cdk_constructs` | "serverless API CDK", "Lambda function example TypeScript" |
| CloudFormation templates | `cloudformation` | "DynamoDB CloudFormation", "StackSets template" |
| Architecture, blogs, guides | `general` | "Lambda best practices", "S3 architecture patterns" |

## Documentation Topics

### reference_documentation
**For: API methods, SDK code, CLI commands, technical specifications**

Use for:
- SDK method signatures: "boto3 S3 upload_file parameters"
- CLI commands: "aws ec2 describe-instances syntax"
- API references: "Lambda InvokeFunction API"
- Service configuration: "RDS parameter groups"

Don't confuse with general—use this for specific technical implementation.

### current_awareness
**For: New features, announcements, "what's new", release dates**

Use for:
- "New Lambda features"
- "When was EventBridge Scheduler released"
- "Latest S3 updates"
- "Is feature X available yet"

Keywords: new, recent, latest, announced, released, launch, available

### troubleshooting
**For: Error messages, debugging, problems, "not working"**

Use for:
- Error codes: "InvalidParameterValue", "AccessDenied"
- Problems: "Lambda function timing out"
- Debug scenarios: "S3 bucket policy not working"
- "How to fix..." queries

Keywords: error, failed, issue, problem, not working, how to fix, how to resolve

### amplify_docs
**For: Frontend/mobile apps with Amplify framework**

Always include framework: React, Next.js, Angular, Vue, JavaScript, React Native, Flutter, Android, Swift

Examples:
- "Amplify authentication React"
- "Amplify GraphQL API Next.js"
- "Amplify Storage Flutter setup"

### cdk_docs
**For: CDK concepts, API references, CLI commands, getting started**

Use for CDK questions like:
- "How to get started with CDK"
- "CDK stack construct TypeScript"
- "cdk deploy command options"
- "CDK best practices Python"
- "What are CDK constructs"

Include language: Python, TypeScript, Java, C#, Go

**Common mistake**: Using general knowledge instead of searching for CDK concepts and guides. Always search for CDK questions!

### cdk_constructs
**For: CDK code examples, patterns, L3 constructs, sample implementations**

Use for:
- Working code: "Lambda function CDK Python example"
- Patterns: "API Gateway Lambda CDK pattern"
- Sample apps: "Serverless application CDK TypeScript"
- L3 constructs: "ECS service construct"

Include language: Python, TypeScript, Java, C#, Go

### cloudformation
**For: CloudFormation templates, concepts, SAM patterns**

Use for:
- "CloudFormation StackSets"
- "DynamoDB table template"
- "SAM API Gateway Lambda"
- CloudFormation template examples

### general
**For: Architecture, best practices, tutorials, blog posts, design patterns**

Use for:
- Architecture patterns: "Serverless architecture AWS"
- Best practices: "S3 security best practices"
- Design guidance: "Multi-region architecture"
- Getting started: "Building data lakes on AWS"
- Tutorials and blog posts

**Common mistake**: Not using this for AWS conceptual and architectural questions. Always search for AWS best practices and patterns!

**Don't use general knowledge for AWS topics—search instead!**

## Search Best Practices

**Be specific with service names:**

Good examples:
```
"S3 bucket versioning configuration"
"Lambda environment variables Python SDK"
"DynamoDB GSI query patterns"
```

Bad examples:
```
"versioning" (too vague)
"environment variables" (missing context)
```

**Include framework/language:**
```
"Amplify authentication React"
"CDK Lambda function TypeScript"
"boto3 S3 client Python"
```

**Use exact error messages:**
```
"AccessDenied error S3 GetObject"
"InvalidParameterValue Lambda environment"
```

**Add temporal context for new features:**
```
"Lambda new features 2024"
"recent S3 announcements"
```

## Multiple Topic Selection

You can search multiple topics simultaneously for comprehensive results:
```
# For a query about Lambda errors and new features:
topics=["troubleshooting", "current_awareness"]

# For CDK examples and API reference:
topics=["cdk_constructs", "cdk_docs"]

# For Amplify and general AWS architecture:
topics=["amplify_docs", "general"]
```

## Response Format

Results include:
- `rank_order`: Relevance score (lower = more relevant)
- `url`: Direct documentation link
- `title`: Page title
- `context`: Excerpt or summary

## Parameters
```
search_phrase: str         # Required - your search query
topics: List[str]          # Optional - up to 3 topics. Defaults to ["general"]
limit: int = 10            # Optional - max results per topic
```

---

**Remember: When in doubt about AWS, always search. This tool provides the most current, accurate AWS information.**

    ## ECS DOCUMENTATION GUIDANCE:
    This tool provides up-to-date ECS documentation and implementation guidance, including new ECS features beyond standard LLM training data.

    New ECS features include:
    - ECS Native Blue-Green Deployments (different from CodeDeploy blue-green, launched 2025)
    - ECS Managed Instances (launched 2025)
    - ECS Express Mode / Express Gateway Services (launched 2025)
SEARCH_DESC_EOF
)

EXPECTED_READ_DESCRIPTION=$(cat <<'READ_DESC_EOF'
Fetch and convert an AWS documentation page to markdown format.

## Usage

This tool retrieves the content of an AWS documentation page and converts it to markdown format.
For long documents, you can make multiple calls with different start_index values to retrieve
the entire content in chunks.

## URL Requirements

Allow-listed URL prefixes:
- docs.aws.amazon.com
- aws.amazon.com
- repost.aws/knowledge-center
- docs.amplify.aws
- ui.docs.amplify.aws
- github.com/aws-cloudformation/aws-cloudformation-templates
- github.com/aws-samples/aws-cdk-examples
- github.com/aws-samples/generative-ai-cdk-constructs-samples
- github.com/aws-samples/serverless-patterns
- github.com/awsdocs/aws-cdk-guide
- github.com/awslabs/aws-solutions-constructs
- github.com/cdklabs/cdk-nag
- constructs.dev/packages/@aws-cdk-containers
- constructs.dev/packages/@aws-cdk
- constructs.dev/packages/@cdk-cloudformation
- constructs.dev/packages/aws-analytics-reference-architecture
- constructs.dev/packages/aws-cdk-lib
- constructs.dev/packages/cdk-amazon-chime-resources
- constructs.dev/packages/cdk-aws-lambda-powertools-layer
- constructs.dev/packages/cdk-ecr-deployment
- constructs.dev/packages/cdk-lambda-powertools-python-layer
- constructs.dev/packages/cdk-serverless-clamscan
- constructs.dev/packages/cdk8s
- constructs.dev/packages/cdk8s-plus-33

Deny-listed URL prefixes:
- aws.amazon.com/marketplace

## Example URLs

- https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html
- https://docs.aws.amazon.com/lambda/latest/dg/lambda-invocation.html
- https://aws.amazon.com/about-aws/whats-new/2023/02/aws-telco-network-builder/
- https://aws.amazon.com/builders-library/ensuring-rollback-safety-during-deployments/
- https://aws.amazon.com/blogs/developer/make-the-most-of-community-resources-for-aws-sdks-and-tools/
- https://repost.aws/knowledge-center/example-article
- https://docs.amplify.aws/react/build-a-backend/auth/
- https://ui.docs.amplify.aws/angular/connected-components/authenticator
- https://github.com/aws-samples/aws-cdk-examples/blob/main/README.md
- https://github.com/awslabs/aws-solutions-constructs/blob/main/README.md
- https://constructs.dev/packages/aws-cdk-lib/v/2.229.1?submodule=aws_lambda&lang=typescript
- https://github.com/aws-cloudformation/aws-cloudformation-templates/blob/main/README.md

## Output Format

The output is formatted as markdown text with:
- Preserved headings and structure
- Code blocks for examples
- Lists and tables converted to markdown format

## Handling Long Documents

If the response indicates the document was truncated, you have several options:

1. **Continue Reading**: Make another call with start_index set to the end of the previous response
2. **Jump to Section**: If a Table of Contents is provided, you can jump directly to any section using the character positions shown (e.g., "char 1500-2800"). Note: Table of Contents length is not counted toward max_length.
3. **Stop Early**: For very long documents (>30,000 characters), if you've already found the specific information needed, you can stop reading

    ## ECS DOCUMENTATION GUIDANCE:
    This tool provides up-to-date ECS documentation and implementation guidance, including new ECS features beyond standard LLM training data.

    New ECS features include:
    - ECS Native Blue-Green Deployments (different from CodeDeploy blue-green, launched 2025)
    - ECS Managed Instances (launched 2025)
    - ECS Express Mode / Express Gateway Services (launched 2025)
READ_DESC_EOF
)

EXPECTED_RECOMMEND_DESCRIPTION=$(cat <<'RECOMMEND_DESC_EOF'
Get content recommendations for an AWS documentation page.

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
    - ECS Native Blue-Green Deployments (different from CodeDeploy blue-green, launched 2025)
    - ECS Managed Instances (launched 2025)
    - ECS Express Mode / Express Gateway Services (launched 2025)
RECOMMEND_DESC_EOF
)

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
