# Advanced Usage

## Multi-Tenant Operations

### Complex Key Patterns

The system supports sophisticated multi-tenant architectures with hierarchical keys:

```python
from generated.complex_demo.entities import TenantUser, TenantDocument
from generated.complex_demo.repositories import TenantUserRepository, TenantDocumentRepository

# Multi-tenant repositories
tenant_user_repo = TenantUserRepository(table_name="MultiTenantApp")
tenant_doc_repo = TenantDocumentRepository(table_name="MultiTenantApp")

# Create tenant user
tenant_user = TenantUser(
    tenant_id="acme_corp",
    user_id="user123",
    username="john_doe",
    email="john@acme.com",
    role="admin",
    timestamp=int(time.time())
)

# Multi-parameter operations
created_user = tenant_user_repo.create_tenant_user(tenant_user)
retrieved_user = tenant_user_repo.get_tenant_user("acme_corp", "user123")
deleted = tenant_user_repo.delete_tenant_user("acme_corp", "user123")

# Complex document operations
document = TenantDocument(
    tenant_id="acme_corp",
    user_id="user123",
    document_id="doc456",
    version="v1.0",
    title="Project Plan",
    content="...",
    timestamp=int(time.time())
)

created_doc = tenant_doc_repo.create_tenant_document(document)
retrieved_doc = tenant_doc_repo.get_tenant_document("acme_corp", "user123", "doc456", "v1.0")
```

## Symmetric PK/SK Template System

### Key Features

- **Consistent Approach**: Both PK and SK use the same template-based system
- **Simple Fields**: `{user_id}` for basic field references (equivalent to old `pk_field`)
- **Complex Patterns**: `TENANT#{tenant_id}#USER#{user_id}` for multi-tenant architectures
- **Flexible Parameters**: Support for any number of parameters in templates

### Template Examples

#### Simple Field Templates

```json
{
  "pk_template": "{user_id}",
  "pk_params": ["user_id"],
  "sk_template": "PROFILE",
  "sk_params": []
}
```

**Generated:**

```python
pk_builder=lambda entity: f"{entity.user_id}"
pk_lookup_builder=lambda user_id: f"{user_id}"
sk_builder=lambda entity: "PROFILE"
sk_lookup_builder=lambda: "PROFILE"
```

#### Complex Multi-Tenant Templates

```json
{
  "pk_template": "TENANT#{tenant_id}#USER#{user_id}",
  "pk_params": ["tenant_id", "user_id"],
  "sk_template": "DOC#{document_id}#{version}",
  "sk_params": ["document_id", "version"]
}
```

**Generated:**

```python
pk_builder=lambda entity: f"TENANT#{entity.tenant_id}#USER#{entity.user_id}"
pk_lookup_builder=lambda tenant_id, user_id: f"TENANT#{tenant_id}#USER#{user_id}"
sk_builder=lambda entity: f"DOC#{entity.document_id}#{entity.version}"
sk_lookup_builder=lambda document_id, version: f"DOC#{document_id}#{version}"
```

### Benefits

- ✅ **Consistency**: PK and SK work the same way
- ✅ **Flexibility**: Support simple fields AND complex patterns
- ✅ **Maintainability**: One approach instead of mixed systems
- ✅ **Scalability**: Easy to add new pattern types
- ✅ **Multi-Tenant Ready**: Built-in support for hierarchical keys

## Key Generation Examples

```python
# Simple PK (equivalent to old pk_field)
user_pk = UserProfile.build_pk_for_lookup("user123")  # "user123"

# Complex PK (multi-tenant)
tenant_pk = TenantUser.build_pk_for_lookup("tenant123", "user456")  # "TENANT#tenant123#USER#user456"

# Static SK (UserProfile)
profile_sk = UserProfile.build_sk_for_lookup()  # "PROFILE"

# Dynamic SK (Post)
post_sk = Post.build_sk_for_lookup("post456")  # "POST#post456"

# Complex SK (Comment)
comment_sk = Comment.build_sk_for_lookup("post456", "comment789")  # "COMMENT#post456#comment789"

# Prefix for queries
post_prefix = Post.get_sk_prefix()  # "POST#"
```

## Customization

### Adding New Entities

1. **Update Schema**: Add entity definition to `schema.json`
2. **Regenerate**: Run `uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema schema.json`
3. **Implement**: Fill in access pattern method bodies

### Extending Base Classes

```python
# Custom base repository with additional functionality
class EnhancedBaseRepository(BaseRepository[T]):
    def batch_create(self, entities: List[T]) -> List[T]:
        # Custom batch operations
        pass
```

## Schema Structure Examples

### Multi-Table Schema

The schema format supports multiple DynamoDB tables in a single schema file:

```json
{
  "tables": [
    {
      "table_config": {
        "table_name": "UserData",
        "partition_key": "user_id",
        "sort_key": "data_type"
      },
      "entities": {
        "UserProfile": {
          "entity_type": "PROFILE",
          "pk_template": "{user_id}",
          "pk_params": ["user_id"],
          "sk_template": "PROFILE",
          "sk_params": [],
          "fields": [
            { "name": "user_id", "type": "string", "required": true },
            { "name": "username", "type": "string", "required": true },
            { "name": "email", "type": "string", "required": true }
          ],
          "access_patterns": [
            {
              "pattern_id": 1,
              "name": "get_user_profile",
              "description": "Get user profile",
              "operation": "GetItem",
              "parameters": [{ "name": "user_id", "type": "string" }],
              "return_type": "single_entity"
            }
          ]
        }
      }
    },
    {
      "table_config": {
        "table_name": "ContentData",
        "partition_key": "content_id",
        "sort_key": "version"
      },
      "entities": {
        "Article": {
          "entity_type": "ARTICLE",
          "pk_template": "{article_id}",
          "pk_params": ["article_id"],
          "sk_template": "v{version}",
          "sk_params": ["version"],
          "fields": [
            { "name": "article_id", "type": "string", "required": true },
            { "name": "version", "type": "integer", "required": true },
            { "name": "title", "type": "string", "required": true }
          ],
          "access_patterns": [
            {
              "pattern_id": 2,
              "name": "get_article",
              "description": "Get article by ID and version",
              "operation": "GetItem",
              "parameters": [
                { "name": "article_id", "type": "string" },
                { "name": "version", "type": "integer" }
              ],
              "return_type": "single_entity"
            }
          ]
        }
      }
    }
  ]
}
```

#### Key Features

- **Tables Array**: Define one or more DynamoDB tables in a single schema file
- **Table-Specific Configuration**: Each table has its own `table_config` with `table_name`, `partition_key`, and `sort_key`
- **Entity Scoping**: Entities are scoped to their parent table and use that table's configuration
- **Global Pattern IDs**: Access pattern IDs must be unique across all tables in the schema
- **Unique Entity Names**: Entity names must be unique across all tables in the schema

## Realistic Sample Data Generation

The code generator supports providing realistic sample data through `usage_data.json` to enhance generated usage examples with meaningful business values instead of generic placeholders.

### Benefits

- **Realistic Examples**: Generated code uses actual business values (e.g., "john.doe@example.com" instead of "sample_email")
- **Better Documentation**: Code examples are more understandable and serve as better documentation
- **Testing Ready**: Sample data can be used directly for integration testing
- **Domain Context**: Values reflect your actual domain model and business logic

### Usage

```bash
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen \
  --schema schema.json \
  --generate_sample_usage \
  --usage-data-path usage_data.json
```

### Structure

```json
{
  "entities": {
    "EntityName": {
      "sample_data": {
        "field_name": "value"
      },
      "access_pattern_data": {
        "field_name": "value"
      },
      "update_data": {
        "field_name": "value"
      }
    }
  }
}
```

### Before/After Example

**Without usage_data.json (default placeholders):**
```python
user = User(
    user_id="sample_user_id",
    email="sample_email"
)
```

**With usage_data.json (realistic values):**
```python
user = User(
    user_id="user-67890",
    email="john.doe@example.com"
)
```

For complete documentation, see [USAGE_DATA.md](USAGE_DATA.md).

## Item Collections (mixed_data)

Item collections are DynamoDB patterns where multiple entity types share the same partition key, distinguished by different sort key prefixes. Use `"return_type": "mixed_data"` for queries that return heterogeneous results.

### When to Use

Use `mixed_data` when your query returns multiple entity types from the same partition:

```json
{
  "pattern_id": 4,
  "name": "get_task_details",
  "description": "Get task with subtasks and comments",
  "operation": "Query",
  "parameters": [{"name": "taskId", "type": "string"}],
  "return_type": "mixed_data"
}
```

### Generated Code

Returns `tuple[list[dict[str, Any]], dict | None]` instead of typed entities:

```python
def get_task_details(
    self, taskId: str, limit: int = 100, exclusive_start_key: dict | None = None
) -> tuple[list[dict[str, Any]], dict | None]:
    """Get task with subtasks and comments (item collection)."""
    pk = Task.build_pk_for_lookup(taskId)
    query_params = {
        'KeyConditionExpression': Key('taskId').eq(pk),
        'Limit': limit
    }
    if exclusive_start_key:
        query_params['ExclusiveStartKey'] = exclusive_start_key

    response = self.table.query(**query_params)
    return self._parse_query_response_raw(response)
```

### Parsing Results

Parse items based on sort key pattern:

```python
items, next_page = task_repo.get_task_details("task_001")

task = None
subtasks = []
comments = []

for item in items:
    sk = item.get('SK', '')

    if sk == 'METADATA':
        task = Task(**item)
    elif sk.startswith('SUBTASK#'):
        subtasks.append(Subtask(**item))
    elif sk.startswith('COMMENT#'):
        comments.append(Comment(**item))
```

## Troubleshooting

### Common Issues

1. **Schema Validation Errors**: Check validation output for specific field issues and suggestions
2. **Invalid Enum Values**: Use suggested values from validation error messages
3. **Duplicate IDs**: Ensure `pattern_id` values are unique across all entities
4. **Missing Required Fields**: Add all required fields as shown in validation errors
5. **Import Errors**: Ensure generated code directory is in Python path
6. **Jinja2 Missing**: Install with `pip install jinja2` for Jinja2 templates
7. **Template Errors**: Check template syntax and variable names

### Debug Mode

```bash
# Generate with verbose output (from dynamodb-mcp-server root)
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema schema.json --no-lint -v

# Skip linting for debugging
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema schema.json --no-lint

# Validate schema only
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema schema.json --validate-only
```

### Template Development

When developing custom templates:

1. **Start Simple**: Begin with existing templates as base
2. **Test Incrementally**: Generate small schemas first
3. **Use Debug Mode**: Skip linting during template development
4. **Check Variables**: Ensure all template variables are available
5. **Validate Output**: Run generated code to catch syntax errors

### Performance Considerations

- **Large Schemas**: Consider splitting into multiple smaller schemas
- **Complex Templates**: Profile template rendering for performance
- **Linting**: Skip linting during development, enable for final generation
- **Batch Operations**: Use batch operations for multiple entity creation
