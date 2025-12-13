# Handler Conversion Prompt Template

Use this prompt template to convert MCP server handlers from the old Response(CallToolResult) pattern to the new Data(BaseModel) pattern.

## Background

Due to CallToolResult Union compatibility issues, we need to convert handler response models from inheriting CallToolResult to using BaseModel data classes, then wrapping them in CallToolResult format.

## Conversion Steps

### 1. Update Import Statements

**Replace old Response imports with new Data imports:**

```python
# OLD (Remove these imports)
from awslabs.aws_dataprocessing_mcp_server.models.{service}_models import (
    CreateResourceResponse,
    DeleteResourceResponse,
    GetResourceResponse,
    ListResourceResponse,
    UpdateResourceResponse,
)

# NEW (Add these imports)
from awslabs.aws_dataprocessing_mcp_server.models.{service}_models import (
    CreateResourceData,
    DeleteResourceData,
    GetResourceData,
    ListResourceData,
    UpdateResourceData,
)
```

### 2. Convert Response Return Statements

**Replace all return statements following this pattern:**

```python
# OLD PATTERN - Remove this
return CreateResourceResponse(
    isError=False,
    content=[TextContent(type='text', text=success_message)],
    resource_id=resource_id,
    operation='create-resource'
)

# NEW PATTERN - Use this instead
success_message = f'Successfully created resource {resource_id}'
data = CreateResourceData(resource_id=resource_id, operation='create-resource')
return CallToolResult(
    isError=False,
    content=[
        TextContent(type='text', text=success_message),
        TextContent(type='text', text=json.dumps(data.model_dump())),
    ],
)
```

### 3. Convert Error Response Return Statements

```python
# OLD PATTERN - Remove this
return CreateResourceResponse(
    isError=True,
    content=[TextContent(type='text', text=error_message)],
    resource_id='',
    operation='create-resource'
)

# NEW PATTERN - Use this instead
data = CreateResourceData(resource_id='', operation='create-resource')
return CallToolResult(
    isError=True,
    content=[
        TextContent(type='text', text=error_message),
        TextContent(type='text', text=json.dumps(data.model_dump())),
    ],
)
```

### 4. Required Import Addition

**Ensure these imports are present:**

```python
from mcp.types import CallToolResult, TextContent
import json
```

## Complete Conversion Example

### Before:
```python
# Create operation
response = service_client.create_resource(**params)
return CreateResourceResponse(
    isError=False,
    content=[TextContent(type='text', text=f'Successfully created {name}')],
    resource_id=response['ResourceId'],
    operation='create-resource'
)

# Error handling
except Exception as e:
    error_message = f'Error creating resource: {str(e)}'
    return CreateResourceResponse(
        isError=True,
        content=[TextContent(type='text', text=error_message)],
        resource_id='',
        operation='create-resource'
    )
```

### After:
```python
# Create operation
response = service_client.create_resource(**params)
success_message = f'Successfully created {name}'
data = CreateResourceData(resource_id=response['ResourceId'], operation='create-resource')
return CallToolResult(
    isError=False,
    content=[
        TextContent(type='text', text=success_message),
        TextContent(type='text', text=json.dumps(data.model_dump())),
    ],
)

# Error handling
except Exception as e:
    error_message = f'Error creating resource: {str(e)}'
    data = CreateResourceData(resource_id='', operation='create-resource')
    return CallToolResult(
        isError=True,
        content=[
            TextContent(type='text', text=error_message),
            TextContent(type='text', text=json.dumps(data.model_dump())),
        ],
    )
```

## Key Points to Remember

1. **Always create a data object** with appropriate fields for each return statement
2. **Always include both success message and JSON data** in the content array
3. **Update all imports** from Response classes to Data classes
4. **Ensure json import** is present for `json.dumps(data.model_dump())`
5. **Maintain consistent error handling** patterns across all operations
6. **Keep the same operation names** as defined in the original Response models

## Checklist for Each Handler File

- [ ] Replace all Response imports with Data imports
- [ ] Add `import json` if not present
- [ ] Convert all successful return statements to new pattern
- [ ] Convert all error return statements to new pattern
- [ ] Update exception handling return statements
- [ ] Verify all operations maintain their original behavior
- [ ] Test that all response data is properly serialized

## Search and Replace Patterns

Use these regex patterns to help with bulk conversion:

**Find Response imports:**
```regex
from.*models.*import.*Response
```

**Find old return patterns:**
```regex
return \w+Response\(
```

**Find CallToolResult content arrays:**
```regex
content=\[TextContent\(type='text', text=.*?\)\]
```

This template ensures consistent conversion across all handler files while maintaining the same functionality and data structure.
