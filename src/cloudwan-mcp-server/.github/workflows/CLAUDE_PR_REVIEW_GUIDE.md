# GitHub Pull Request Review Process Guide for CloudWAN MCP Server

DO prioritize the use of the "GitHub" MCP server over the "gh" command line tool.
DO use pagination ("perPage" = 1 or "--paginate") for consumable chunks in responses.
DO always create a final pull request review decision with an "APPROVE" or a "REQUEST_CHANGES" assessment.
DO use "gh" tool as a fallback when the "GitHub" MCP server is unable to process your task.
DO be very explicit about why you cannot perform tasks with the detailed instructions on how to resolve issues with your task.
DO verify that proper markdown is supplied to the "body", paying extra special attention that proper line feeds are used so it is rendered properly.

DO NOT include or wait for the required <WORKFLOW> pull request check to finish.

## Overview

This document outlines a systematic approach for using Claude to review GitHub Pull Requests (PRs) for the CloudWAN MCP Server project, focusing specifically on AWS networking, MCP protocol compliance, and CloudWAN-specific functionality.

## Step-by-Step Review Process

### 0. Prerequisites

Read and understand the repository's "README.md" and CloudWAN-specific documentation.

Look for references to contributing guidelines ("CONTRIBUTING.md"), design guidelines ("DESIGN_GUIDELINES.md"), security ("SECURITY"), developer guidance ("DEVELOPER_GUIDE.md"), and other instructional files to evaluate the changes within the pull request.

```tool
Read(file_path="README.md")
Read(file_path="<path-to-other-referenced-files>")
```

### 1. Initial PR Assessment

```tool
mcp__GitHub__get_pull_request(
    owner="<REPOSITORY-OWNER>",
    repo="<REPOSITORY-REPO>",
    pullNumber="<PR-NUMBER>"
)
```

Examine:
- Title and description
- Size of changes (files, additions, deletions)
- Labels and metadata
- Author's affiliation
- Impact on CloudWAN functionality

### 2. Fetch PR Comments

```tool
mcp__GitHub__get_pull_request_comments(
    owner="<REPOSITORY-OWNER>",
    repo="<REPOSITORY-REPO>",
    pullNumber="<PR-NUMBER>"
)
```

This reveals:
- Review feedback from other developers
- Discussions about CloudWAN implementation
- AWS networking concerns
- MCP protocol compliance issues
- Changes requested by reviewers

### 3. Analyze Code Changes

For files with comments:
```tool
Read(file_path="<path-to-file>")
```

For specific patterns:
```tool
Grep(pattern="<pattern>", path="<directory>")
```

Check if issues were addressed:
```tool
Bash(command="grep -n <pattern> <file-path>")
```

### 4. Key Aspects to Review

Use what you learned from the prerequisites step above, and enhance with these CloudWAN-specific elements:

1. **Code Quality**
   - Function/method size (break down large functions)
   - Naming conventions (clear and descriptive, AWS-compliant)
   - Documentation quality (docstrings, comments)
   - AWS SDK integration patterns
   - FastMCP framework compliance

2. **CloudWAN Specifics**
   - Core Network policy validation
   - Transit Gateway integration correctness
   - Network Function Group handling
   - AWS Network Firewall compatibility (if applicable)
   - Region-aware implementations

3. **AWS Integration**
   - Proper boto3 client usage
   - Thread-safe AWS client caching patterns
   - Custom endpoint support implementation
   - AWS Labs coding standards compliance
   - Error handling for AWS service failures

4. **MCP Protocol Compliance**
   - Tool registration and parameter validation
   - Response formatting consistency
   - Error propagation patterns
   - Type annotations and validation

5. **Testing and Validation**
   - Unit test coverage for new functionality
   - Integration test updates for AWS service changes
   - Mocking patterns for AWS services
   - TokenBucketRateLimiter usage for rate limiting

6. **Security and Credentials**
   - Credential sanitization in responses
   - No hardcoded AWS credentials or endpoints
   - Proper secret handling in CI/CD
   - AWS IAM role assumptions

7. **File Management**
   - Proper directory structure following existing patterns
   - No files checked in against the .gitignore
   - Unnecessary files removed (test reports, cache files, etc.)
   - Docker containerization compatibility

8. **Performance Considerations**
   - AWS client caching effectiveness
   - Pagination handling for large result sets
   - Memory usage in large topology analysis
   - Response time optimization

### 5. Providing Feedback

1. **General Review Comments**:
```tool
mcp__GitHub__create_pull_request_review(
    owner="<REPOSITORY-OWNER>",
    repo="<REPOSITORY-REPO>",
    pullNumber="<PR-NUMBER>",
    event="COMMENT",
    body="Overall assessment with summary of CloudWAN MCP Server findings to include the workflow's reference <RUN-ID>"
)
```

2. **Specific File Comments**:
```tool
mcp__GitHub__create_pull_request_review(
    owner="<REPOSITORY-OWNER>",
    repo="<REPOSITORY-REPO>",
    pullNumber="<PR-NUMBER>",
    event="COMMENT",
    body="General assessment focusing on CloudWAN functionality and AWS integration",
    comments=[
        {
            "path": "awslabs/cloudwan_mcp_server/server.py",
            "line": 50,
            "body": "Specific feedback about CloudWAN implementation: \n```suggestion\n# Add CloudWAN-specific code suggestions\n```"
        },
        # Additional comments...
    ]
)
```

### 6. Final Assessment

After all reviews and follow-ups:

```tool
mcp__GitHub__create_pull_request_review(
    owner="<REPOSITORY-OWNER>",
    repo="<REPOSITORY-REPO>",
    pullNumber="<PR-NUMBER>",
    event="APPROVE",  # or "REQUEST_CHANGES" if issues remain
    body="Final assessment justifying approval or requested changes for CloudWAN MCP Server functionality"
)
```

## CloudWAN-Specific Issues to Look For

1. **AWS Service Integration**
   - Correct CloudWAN API usage (networkmanager service)
   - Proper EC2 integration for VPC and Transit Gateway operations
   - CloudWatch Logs integration for Network Firewall (if applicable)
   - AWS endpoint customization for testing environments

2. **Network Analysis Logic**
   - Core Network policy parsing accuracy
   - Transit Gateway route table analysis correctness
   - Network path tracing implementation
   - IP CIDR validation and conflict detection

3. **Error Handling**
   - AWS service error propagation
   - Network topology validation failures
   - Rate limiting and throttling handling
   - Resource not found scenarios

4. **Data Models**
   - Type safety for CloudWAN resources
   - Proper serialization/deserialization
   - AWS resource ARN handling
   - Network topology data structures

5. **Testing Coverage**
   - AWS service mocking completeness
   - CloudWAN policy validation test cases
   - Network topology test scenarios
   - Integration test coverage for complex workflows

## Example Review Process for CloudWAN MCP Server

1. Get PR details and understand the CloudWAN functionality changes
2. Analyze reviewer comments to identify AWS networking concerns
3. Check if CloudWAN-specific issues were resolved in the code
4. Review for MCP protocol compliance and AWS Labs standards
5. Validate test coverage for new CloudWAN features
6. Provide specific, actionable feedback with AWS networking expertise
7. Recommend approval or additional changes with CloudWAN context

## Common CloudWAN Patterns to Validate

1. **Client Caching**: Ensure `@lru_cache` decorator usage for AWS clients
2. **Custom Endpoints**: Verify CLOUDWAN_AWS_CUSTOM_ENDPOINTS support
3. **Error Sanitization**: Check credential and sensitive data removal
4. **Type Annotations**: Validate modern Python typing (str | None vs Optional[str])
5. **Testing Patterns**: Confirm moto mocking and comprehensive test coverage

---

Use this guide as a reference for CloudWAN MCP Server PR reviews, focusing on AWS networking expertise, MCP protocol compliance, and production-ready CloudWAN functionality.