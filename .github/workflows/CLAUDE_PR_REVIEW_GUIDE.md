# GitHub Pull Request Review Process Guide for Claude Code

DO prioritize the use of the "GitHub" MCP server over the "gh" command line tool.
DO use pagination ("perPage" = 1 or "--paginate") for consumable chunks in responses.
DO always create a final pull request review decision with an "APPROVE" or a "REQUEST_CHANGES" assessment.
DO use "gh" tool as a fallback when the "GitHub" MCP server is unable to process your task.
DO be very explicit about why you cannot perform tasks with the detailed instructions on how to resolve issues with your task.
DO verify that proper markdown is supplied, pay attention that proper line feeds are used (for example the '\n' should represent a white space not the literal backslash and letter N)

DO NOT include or wait for the required <WORKFLOW> pull request check to finish

## Overview

This document outlines a systematic approach for using Claude to review GitHub Pull Requests (PRs), focusing specifically on GitHub repository context.

## Step-by-Step Review Process

The <PR-NUMBER> is ${{ github.event.pull_request.number }}
The <REPOSITORY-OWNER>/<REPOSITORY-REPO> is ${{ github.repository }}
The <RUN-ID> is ${{ github.run_id }}
The <WORKFLOW> is ${{ github.workflow }}

### 0. Prerequisites

Read and understand the repository's "README.md".

Look for refernces to contributing guidelines ("CONTRIBUTING.md"), specific code of conduct ("CODE_OF_CONDUCT.md"), design guidelines ("DESIGN_GUIDELINES.md"), security ("SECURITY"), general developer guidance ("DEVELOPER_GUIDE.md"), and other instructional files to evaluate the changes within the pull request.

```tool
Read(file_path="README.md")
Read(file_path="<path-to-other-referenced-files>)
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
- Discussions about implementation
- Issues that need to be addressed
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
Batch(description="Check for issue resolution",
      invocations=[
          {"tool_name": "Bash", "input": {"command": "grep -n <pattern> <file-path>"}},
          {"tool_name": "Bash", "input": {"command": "ls -la <directory> | grep <pattern>"}}
      ])
```

### 4. Key Aspects to Review

Use what you learned from the prerequisites step above, and enhance with these elements:

1. **Code Quality**
   - Function/method size (break down large functions)
   - Naming conventions (clear and descriptive)
   - Documentation quality (docstrings, comments)
   - Pattern implementation (e.g., factory vs generator)

2. **Organization**
   - Constants centralized in appropriate files
   - Utility functions in shared modules
   - Proper separation of concerns

3. **Terminology and Branding**
   - Correct product names (e.g., "Amazon Bedrock" not "AWS Bedrock")
   - Consistent naming across repository

4. **File Management**
   - Proper and consistent structure
   - No files checked in against the .gitignore
   - Unnecessary files removed (e.g., test, linting, sarif, check, or other reports not intended to be added)

5. **Ensure Required Checks are Successful**
   - Look over the results of pull request status
   - When a required check has failed, the overall pull request review should be "REQUEST_CHANGES".
   - DO NOT include or wait for this workflow, <WORKFLOW>, to finish

### 5. Providing Feedback

1. **General Review Comments**:
```tool
mcp__GitHub__create_pull_request_review(
    owner="<REPOSITORY-OWNER>",
    repo="<REPOSITORY-REPO>",
    pullNumber="<PR-NUMBER>",
    event="COMMENT",
    body="Overall assessment with summary of findings include the workflow's as a reference <RUN-ID>"
)
```

2. **Specific File Comments**:
```tool
mcp__GitHub__create_pull_request_review(
    owner="<REPOSITORY-OWNER>",
    repo="<REPOSITORY-REPO>",
    pullNumber="<PR-NUMBER>",
    event="COMMENT",
    body="General assessment",
    comments=[
        {
            "path": "src/path/to/file.py",
            "line": 50,
            "body": "Specific feedback about this line or section: \n```suggestion\n add optional code suggestions \n```"
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
    body="Final assessment justifying approval or requested changes"
)
```

## Common Issues to Look For

1. **Naming and Documentation**
   - Function names should match their purpose (e.g., factory pattern vs. generator)
   - Return types in docstrings should match actual return types
   - Parameters should be well documented

2. **Code Structure**
   - Functions should be reasonably sized (< 100 lines ideally)
   - Classes should have single responsibility
   - Constants should be centralized

3. **AWS/Amazon Specifics**
   - Correct service names (e.g., "Amazon Bedrock" vs "AWS Bedrock")
   - Proper credential handling
   - Appropriate error handling for AWS services

4. **Project Standards**
   - Consistent with other MCP servers
   - Features properly documented in README.md
   - Tests covering key functionality

## Example Review Process

1. Get PR details and understand the changes
2. Analyze reviewer comments to identify key issues
3. Check if those issues were resolved in the code
4. Review for additional concerns not previously identified
5. Provide specific, actionable feedback with line references and suggestions on how to resolve
6. Recommend approval or additional changes with clear justification

---

Use this guide as a reference for future PR reviews, adapting the specific commands and focus areas based on the PR content and context.
