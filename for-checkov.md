# Implementation Guide: Adding Default Tagging + Transparency Features to Checkov Branch

## Overview
This guide shows how to add the default tagging fixes and transparency features from `ccapi-mcp-server-default-tagging` branch to the `ccapi-mcp-server-checkov-support` branch while preserving Checkov functionality.

## Features to Add

### 1. Fixed Default Tagging (Critical Bug Fix)
- **Problem**: Default management tags not added during UPDATE operations
- **Solution**: Always call `add_default_tags()` for both CREATE and UPDATE operations

### 2. Transparency Features
- **Problem**: Users can't see what infrastructure will be created (including default tags)
- **Solution**: Added `explain_infrastructure` tool with mandatory workflow

## Implementation Steps

### Step 1: Fix Default Tagging in `cloud_control_utils.py`

**File**: `src/ccapi-mcp-server/awslabs/ccapi_mcp_server/cloud_control_utils.py`

**Change**: Make `add_default_tags()` always try to add tags (ignore schema):

```python
def add_default_tags(properties: Dict, schema: Dict) -> Dict:
    """Add default tags to resource properties. Always tries to add tags - let AWS reject if unsupported."""
    if not properties:
        return {}

    properties_with_tags = properties.copy()
    
    # Always try to add tags - don't check schema since it can be unreliable
    if 'Tags' not in properties_with_tags:
        properties_with_tags['Tags'] = []
    
    tags = properties_with_tags['Tags']
    # Add default tags if they don't exist
    managed_by_exists = any(tag.get('Key') == 'MANAGED_BY' for tag in tags)
    source_exists = any(tag.get('Key') == 'MCP_SERVER_SOURCE_CODE' for tag in tags)
    version_exists = any(tag.get('Key') == 'MCP_SERVER_VERSION' for tag in tags)

    if not managed_by_exists:
        tags.append({'Key': 'MANAGED_BY', 'Value': 'CCAPI-MCP-SERVER'})
    if not source_exists:
        tags.append(
            {
                'Key': 'MCP_SERVER_SOURCE_CODE',
                'Value': 'https://github.com/awslabs/mcp/tree/main/src/ccapi-mcp-server',
            }
        )
    if not version_exists:
        from awslabs.ccapi_mcp_server import __version__
        tags.append({'Key': 'MCP_SERVER_VERSION', 'Value': __version__})

    properties_with_tags['Tags'] = tags

    return properties_with_tags
```

### Step 2: Fix UPDATE Operations in `infrastructure_generator.py`

**File**: `src/ccapi-mcp-server/awslabs/ccapi_mcp_server/infrastructure_generator.py`

**Find the UPDATE section** and ensure `add_default_tags()` is called:

```python
# In the UPDATE operation section:
if is_update:
    # ... existing logic to get current_properties and apply patches ...
    
    # V1: Always add required MCP server identification tags for updates too
    properties_with_tags = add_default_tags(update_properties, schema)
    
    operation = 'update'
else:
    # CREATE operation - should already have this:
    properties_with_tags = add_default_tags(properties, schema)
    operation = 'create'
```

### Step 3: Add `explain_infrastructure` Tool to `server.py`

**File**: `src/ccapi-mcp-server/awslabs/ccapi_mcp_server/server.py`

**Add after `generate_infrastructure_code` tool**:

```python
@mcp.tool()
async def explain_infrastructure(
    properties_token: str = Field(default="", description="Properties token from generate_infrastructure_code"),
    content: dict = Field(default_factory=dict, description="Raw infrastructure content to explain"),
    operation: str = Field(description="Operation type: create, update, delete, analyze"),
    user_intent: str = Field(default="", description="Optional: User's stated purpose for this infrastructure")
) -> dict:
    """Explain infrastructure in clear, human-readable format.
    
    This tool forces the LLM to provide a clear explanation of what infrastructure
    will be created, updated, or deleted. Always highlight default management tags.
    """
    if properties_token:
        # Get properties from token
        if properties_token not in _properties_store:
            raise ClientError("Invalid properties token")
        
        properties = _properties_store[properties_token]
        # Mark as explained
        if not hasattr(_properties_store, '_metadata'):
            _properties_store._metadata = {}
        _properties_store._metadata[properties_token] = {'explained': True, 'operation': operation}
        
        explanation_content = properties
    else:
        # Use provided content
        explanation_content = content
    
    instruction = f"""You MUST provide a clear, bulleted explanation of this {operation} operation.
    
Highlight:
• What resources will be {operation}d
• All tags (especially default management tags: MANAGED_BY, MCP_SERVER_SOURCE_CODE, MCP_SERVER_VERSION)
• Key configuration details
• Any security or compliance considerations
"""
    
    if user_intent:
        instruction += f"\n• How this serves the user's intent: {user_intent}"
    
    return {
        "infrastructure_content": explanation_content,
        "operation": operation,
        "instruction_to_llm": instruction,
        "user_intent": user_intent
    }
```

### Step 4: Add Validation to `create_resource()` and `update_resource()`

**In `create_resource()` function**, add after token validation:

```python
# Check if infrastructure was explained
if hasattr(_properties_store, '_metadata') and properties_token in _properties_store._metadata:
    if not _properties_store._metadata[properties_token].get('explained', False):
        raise ClientError(
            'You must call explain_infrastructure() first to review what will be created'
        )
else:
    raise ClientError(
        'You must call explain_infrastructure() first to review what will be created'
    )
```

**In `update_resource()` function**, add similar validation:

```python
# Check if infrastructure was explained
if hasattr(_properties_store, '_metadata') and properties_token in _properties_store._metadata:
    if not _properties_store._metadata[properties_token].get('explained', False):
        raise ClientError(
            'You must call explain_infrastructure() first to review what will be updated'
        )
else:
    raise ClientError(
        'You must call explain_infrastructure() first to review what will be updated'
    )
```

### Step 5: Update Token Cleanup

**In both `create_resource()` and `update_resource()`**, update cleanup:

```python
# Clean up used token and metadata
del _properties_store[properties_token]
if hasattr(_properties_store, '_metadata') and properties_token in _properties_store._metadata:
    del _properties_store._metadata[properties_token]
```

### Step 6: Update System Prompt

**In the system prompt section**, update the mandatory workflow:

```python
## MANDATORY Tool Usage Sequence
• ALWAYS follow this exact sequence for resource creation:
  1. generate_infrastructure_code() with aws_session_info and ALL tags included in properties
  2. explain_infrastructure() with properties_token - YOU MUST provide clear explanation
  3. run_checkov() with security_check_token for security scanning
  4. create_resource() with aws_session_info and properties_token
• ALWAYS follow this exact sequence for resource updates:
  1. generate_infrastructure_code() with identifier and patch_document
  2. explain_infrastructure() with properties_token - YOU MUST provide clear explanation
  3. run_checkov() with security_check_token for security scanning
  4. update_resource() with properties_token
• For deletions: get_resource() → explain_infrastructure() → delete_resource()
```

## Expected Workflow After Implementation

### CREATE Flow:
```
1. generate_infrastructure_code() → properties_token
2. explain_infrastructure(properties_token, "create") → LLM explains what will be created
3. run_checkov(security_check_token) → security scan with default tags visible
4. create_resource(properties_token) → creates resource with default tags
```

### UPDATE Flow:
```
1. generate_infrastructure_code(identifier, patch_document) → properties_token  
2. explain_infrastructure(properties_token, "update") → LLM explains changes
3. run_checkov(security_check_token) → security scan
4. update_resource(properties_token) → updates resource with default tags
```

## Benefits of This Implementation

1. **Fixed Default Tagging**: Management tags now work for both CREATE and UPDATE
2. **Transparency**: Users see exactly what will be created including default tags
3. **Security**: Checkov still scans with all tags visible
4. **Enforcement**: LLM must explain before any destructive operations
5. **Better UX**: Clear workflow with human-readable explanations

## Testing

After implementation, test:
1. CREATE operation includes 3 default management tags
2. UPDATE operation includes 3 default management tags  
3. `explain_infrastructure` shows all tags clearly
4. Checkov scans show default tags in CloudFormation template
5. Skipping `explain_infrastructure` causes clear error messages

## Files Modified

- `src/ccapi-mcp-server/awslabs/ccapi_mcp_server/cloud_control_utils.py`
- `src/ccapi-mcp-server/awslabs/ccapi_mcp_server/infrastructure_generator.py`
- `src/ccapi-mcp-server/awslabs/ccapi_mcp_server/server.py`