# Automated Code Owner Assignment System

This directory contains an automated system for assigning code owners to unassigned issues in the awslabs/mcp repository based on the CODEOWNERS file and intelligent content analysis.

## 📋 Overview

The system consists of three main components:

1. **`assign_code_owners.py`** - Main assignment script with intelligent server detection
2. **`mcp_github_client.py`** - GitHub MCP server integration wrapper
3. **`auto-assign-issues.yml`** - GitHub Actions workflow for automation

## 🎯 Key Features

- **Intelligent Assignment**: Uses content analysis to detect which MCP server(s) an issue relates to
- **CODEOWNERS Integration**: Automatically assigns based on the repository's CODEOWNERS file
- **Automated Scheduling**: Runs daily via GitHub Actions to handle all unassigned issues
- **Real-time Assignment**: Assigns new issues as soon as they're created
- **Project Board Integration**: Automatically adds assigned issues to the GitHub project board
- **Comprehensive Logging**: Detailed logs and summary reports for audit purposes
- **Dry-run Support**: Test assignments without making actual changes

## 🔧 How It Works

### Assignment Logic

1. **Server Detection**: Analyzes issue title, body, and labels for:
   - Direct server name mentions (e.g., "aws-api-mcp-server")
   - Path references (e.g., "/src/dynamodb-mcp-server")
   - Service keywords (e.g., "dynamodb" → "dynamodb-mcp-server")
   - Label patterns (e.g., "dynamodb-mcp-server" label)

2. **Owner Mapping**: Maps detected servers to code owners from CODEOWNERS file:
   - Single server → assign to specific maintainers
   - Multiple servers → assign to all relevant maintainers
   - No specific server → assign to @awslabs/mcp-maintainers (fallback)

3. **Assignment**: Updates GitHub issue with:
   - Individual assignees (filtered from team mentions)
   - Explanatory comment with assignment reasoning
   - Addition to GitHub project board

### Automation Schedule

- **Daily**: 9:00 UTC - processes all unassigned issues
- **On Issue Creation**: Immediately assigns new issues
- **Manual Trigger**: Can be run on-demand with custom options

## 🚀 Setup

### Prerequisites

- GitHub repository with CODEOWNERS file
- GitHub Actions enabled
- Docker available (for GitHub MCP server)

### Installation

1. **Files are already created** - The system is ready to use
2. **GitHub Actions will install dependencies automatically**
3. **No additional setup required** - uses repository secrets

### Configuration

The system uses these environment variables:

```bash
GITHUB_TOKEN         # GitHub personal access token (automatic in Actions)
GITHUB_PROJECT_URL   # Project board URL (set in workflow)
DRY_RUN              # Enable dry-run mode (workflow input)
VERBOSE              # Enable verbose logging (workflow input)
```

## 🎮 Usage

### Running Locally

```bash
# Install dependencies
pip install -r scripts/requirements.txt

# Set required environment variable
export GITHUB_TOKEN="your-github-token"

# Run in dry-run mode to see what would happen
python scripts/assign_code_owners.py --dry-run --verbose

# Run actual assignments
python scripts/assign_code_owners.py --verbose
```

### GitHub Actions Triggers

1. **Scheduled Run**: Automatically runs daily at 9:00 UTC
2. **Manual Trigger**: Go to Actions → "Auto-Assign Code Owners to Issues" → "Run workflow"
3. **New Issue**: Automatically runs when new issues are created

## 📊 Server Detection Patterns

The system detects MCP servers using these patterns:

| Pattern Type | Example | Result |
|-------------|---------|--------|
| Direct mention | "aws-api-mcp-server" | aws-api-mcp-server |
| Service keyword | "dynamodb issue" | dynamodb-mcp-server |
| Path reference | "/src/eks-mcp-server" | eks-mcp-server |
| Label pattern | Label: "cdk-mcp-server" | cdk-mcp-server |

## 👥 Assignment Examples

### Single Server Issue
```
Title: "DynamoDB MCP Server connection timeout"
→ Detected: dynamodb-mcp-server
→ Assigned to: @erbenmo, @shetsa-amzn, @LeeroyHannigan
```

### Multiple Server Issue
```
Title: "Integration between CDK and Terraform MCP servers"
→ Detected: cdk-mcp-server, terraform-mcp-server
→ Assigned to: @jimini55, @alexa-perlov
```

### General Issue
```
Title: "Documentation improvements needed"
→ Detected: (none specific)
→ Assigned to: @awslabs/mcp-maintainers
```

## 📈 Monitoring & Maintenance

### Logs and Reports

- **GitHub Actions Summary**: View assignment results in workflow summary
- **Detailed Logs**: Full verbose logs available in workflow runs
- **Failure Notifications**: Automatic issue creation if scheduled runs fail

### Updating Server Patterns

To add new MCP servers or update detection patterns:

1. **Update CODEOWNERS file** - Add new server entries
2. **Update `_build_server_patterns()`** - Add keyword mappings
3. **Update `_parse_codeowners()`** - Add owner mappings
4. **Test changes** - Run with `--dry-run --verbose`

### Monitoring Health

The system includes several monitoring mechanisms:

- **Failure Detection**: Creates issues when scheduled runs fail
- **Assignment Tracking**: Logs all assignment decisions
- **Coverage Reports**: Shows which issues couldn't be assigned to specific servers

## 🔒 Security Considerations

- **Token Security**: Uses GitHub's built-in `GITHUB_TOKEN` secret
- **Minimal Permissions**: Only requests necessary GitHub permissions
- **Audit Trail**: All assignments are logged and commented on issues
- **Safe Defaults**: Falls back to maintainers for unclear cases

## 🛠 Troubleshooting

### Common Issues

1. **MCP Server Connection Failed**
   - Check Docker is available in GitHub Actions
   - Verify GitHub token permissions
   - Check MCP server image availability

2. **No Issues Assigned**
   - Verify search query returns results
   - Check CODEOWNERS file format
   - Review server detection patterns

3. **Assignment Failures**
   - Check individual usernames exist
   - Verify repository permissions
   - Review GitHub API rate limits

### Debug Commands

```bash
# Test server detection only
python scripts/assign_code_owners.py --dry-run --verbose

# Check MCP server connectivity
docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN="$GITHUB_TOKEN" \
  ghcr.io/github/github-mcp-server

# Manually test specific issue
# (modify script to accept --issue-number parameter)
```

## 📚 Related Documentation

- [GitHub CODEOWNERS Documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [GitHub MCP Server Documentation](https://github.com/github/github-mcp-server)
- [awslabs/mcp Project Board](https://github.com/orgs/awslabs/projects/192)

## 🤝 Contributing

To improve the assignment system:

1. **Add Server Patterns**: Update detection keywords for better accuracy
2. **Improve Detection**: Enhance content analysis algorithms
3. **Add Features**: Extend functionality (PR assignment, discussion triage, etc.)
4. **Fix Bugs**: Submit issues for any problems discovered

---

*This automation system was designed to help maintain the awslabs/mcp repository by ensuring issues are promptly assigned to the appropriate code owners for faster resolution.*
