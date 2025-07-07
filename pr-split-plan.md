# PR Split Plan for ccapi-mcp-server

## Goal
Split your new ccapi-mcp-server into 3 manageable PRs:
1. **Base server** (core functionality + IAM improvements)
2. **Default tagging feature** (base + tagging)
3. **Checkov validation feature** (base + tagging + optional Checkov)

## Execution Plan

### Section 1: Create Branch Copies
```bash
# Ensure you're on your current feature branch
git checkout ccapi-mcp-server-clean

# Create two copies of current state
git branch ccapi-mcp-server-default-tagging
git branch ccapi-mcp-server-checkov-support
```

### Section 2: PR #1 - Base ccapi-mcp-server (Current Branch)
```bash
# Stay on current branch
git checkout ccapi-mcp-server-clean

# Strip to core server functionality
# - Keep core ccapi-mcp-server implementation
# - Keep IAM improvements (SSO support, error handling)
# - Remove default tagging features
# - Remove Checkov functionality entirely
# - Update tests for base functionality only

# Commit changes
git add .
git commit -m "Add new ccapi-mcp-server with IAM improvements"

# Check against upstream
git fetch upstream
git log --oneline upstream/main..HEAD
```

### Section 3: PR #2 - Add Default Tagging
```bash
# Switch to tagging branch
git checkout ccapi-mcp-server-default-tagging

# Remove only Checkov, keep base + tagging
# - Keep base ccapi-mcp-server + IAM improvements
# - Keep default tagging features
# - Remove Checkov code/imports/tests
# - Update tests for base + tagging functionality

# Commit changes  
git add .
git commit -m "Add default tagging support to ccapi-mcp-server"

# Check against upstream
git fetch upstream
git log --oneline upstream/main..HEAD
```

### Section 4: PR #3 - Add Optional Checkov
```bash
# Switch to checkov branch
git checkout ccapi-mcp-server-checkov-support

# Make Checkov optional via environment variable
# - Keep base + tagging + add optional Checkov
# - Add env var like ENABLE_CHECKOV_VALIDATION=true/false
# - Modify code to skip Checkov when disabled
# - Update tests for all scenarios including Checkov

# Commit changes
git add .
git commit -m "Add optional Checkov security validation to ccapi-mcp-server"

# Check against upstream
git fetch upstream  
git log --oneline upstream/main..HEAD
```

### Section 5: Submit PRs and Handle Merges
```bash
# Submit all 3 PRs within the hour

# After PR #1 merges:
git checkout ccapi-mcp-server-default-tagging
git fetch upstream
git rebase upstream/main
# Handle conflicts if any, then update PR #2

# After PR #2 merges:
git checkout ccapi-mcp-server-checkov-support  
git fetch upstream
git rebase upstream/main
# Handle conflicts if any, then update PR #3
```

## Branch Status Tracker
- [ ] ccapi-mcp-server-clean (PR #1) - Base server
- [ ] ccapi-mcp-server-default-tagging (PR #2) - + Default tagging  
- [ ] ccapi-mcp-server-checkov-support (PR #3) - + Optional Checkov