# Prometheus MCP Server - Workspace Selection Changes

## Overview
Modified the Prometheus MCP Server to support dynamic workspace selection when no workspace is initially configured. The server now prompts users to select a workspace when they first try to use any of the main tools.

## Changes Made

### 1. Added Global Workspace Tracking
- Added `workspace_selected` global flag to track if user has selected a workspace
- This prevents repeated prompts once a workspace is chosen

### 2. New Functions Added

#### `get_available_workspaces()`
- Uses AWS SDK (boto3) to query available Prometheus workspaces
- Returns list of workspaces with ID, alias, status, and creation date
- Handles AWS session creation with current profile/region settings

#### `check_workspace_selection(ctx: Context)`
- Checks if a workspace is already selected
- If not selected, queries available workspaces and prompts user
- Returns `True` if workspace is selected, `False` if user needs to select one
- Displays formatted list of available workspaces to help user choose

#### `list_workspaces()` - New MCP Tool
- New tool that users can call to see all available workspaces
- Shows workspace ID, alias, status, and region information
- Useful for users to explore available options before selecting

### 3. Modified Existing Tools
Updated all main tools to check workspace selection before executing:

#### `execute_query()`
- Added workspace selection check at the beginning
- Returns error if no workspace selected

#### `execute_range_query()`
- Added workspace selection check at the beginning
- Returns error if no workspace selected

#### `list_metrics()`
- Added workspace selection check at the beginning
- Returns empty list if no workspace selected

#### `get_server_info()`
- Added workspace selection check at the beginning
- Shows "No workspace selected" status if none chosen

#### `set_prometheus_workspace()`
- Now sets the `workspace_selected` flag to `True` when successful
- This prevents future prompts for workspace selection

### 4. Modified Initialization Logic

#### `setup_environment()`
- Removed requirement for Prometheus URL to be configured
- Now validates URL only if provided
- Allows server to start without a workspace configured

#### `async_main()`
- Only tests Prometheus connection if URL is configured
- Sets `workspace_selected = True` if connection successful
- Logs appropriate message if no URL configured

#### `main()`
- Removed auto-discovery of workspace during startup
- Server now starts successfully without a workspace
- Workspace selection happens on first tool use

## User Experience

### Before Changes
- Server required Prometheus URL or would auto-select first active workspace
- No user choice in workspace selection
- Failed to start if no workspace found

### After Changes
1. Server starts successfully without workspace configuration
2. When user first calls `ExecuteQuery`, `ExecuteRangeQuery`, `ListMetrics`, or `GetServerInfo`:
   - Server queries available workspaces using AWS SDK
   - Displays formatted list of available workspaces
   - Prompts user to use `SetPrometheusWorkspace` tool to select one
3. User can also call `ListWorkspaces` tool to explore options
4. Once workspace is selected via `SetPrometheusWorkspace`, all tools work normally
5. No further prompts for workspace selection in the same session

## Example User Flow

```
1. User: calls ExecuteQuery tool
   Server: "No Prometheus workspace selected. Please choose from available workspaces:
           - ws-12345678-abcd-1234-efgh-123456789012 (prod-monitoring) - Status: ACTIVE
           - ws-87654321-dcba-4321-hgfe-210987654321 (dev-monitoring) - Status: ACTIVE
           Use the SetPrometheusWorkspace tool to select a workspace."

2. User: calls SetPrometheusWorkspace with workspace_id="ws-12345678-abcd-1234-efgh-123456789012"
   Server: Successfully connects and returns server info

3. User: calls ExecuteQuery tool again
   Server: Executes query normally (no workspace prompt)
```

## Benefits
- **User Choice**: Users can see and choose from available workspaces
- **Flexibility**: Server works without pre-configuration
- **Better UX**: Clear prompts guide users to select appropriate workspace
- **No Interruption**: Once selected, workspace choice persists for the session
- **Discovery**: New `ListWorkspaces` tool helps users explore options
