# Usage Data

The `usage_data.json` file provides realistic sample data for generated code examples, replacing generic placeholders with meaningful business values.

## Structure

```json
{
  "entities": {
    "EntityName": {
      "sample_data": {},
      "access_pattern_data": {},
      "update_data": {}
    }
  }
}
```

| Section               | Purpose                                      |
| --------------------- | -------------------------------------------- |
| `sample_data`         | Values for creating entities                 |
| `access_pattern_data` | Values for query/get parameters              |
| `update_data`         | Values for updating entities                 |

## Value Resolution

The system resolves field values using a fallback mechanism:

1. **Primary**: Checks the requested section (`sample_data`, `access_pattern_data`, or `update_data`)
2. **Fallback**: If not found, falls back to `sample_data`
3. **Default**: If still not found, uses a generic placeholder (e.g., `"sample_field_name"`)

**Example:**
```python
# For field "email" in access_pattern_data:
1. usage_data["entities"]["User"]["access_pattern_data"]["email"]  # Try specific section
2. usage_data["entities"]["User"]["sample_data"]["email"]          # Fallback
3. "sample_email"                                                  # Default
```

## Data Type Handling

The system maintains an implicit contract between data loading and code formatting:

**Values in usage_data.json** should be raw values without language-specific formatting:

```json
{
  "user_id": "user-123",     // String - no quotes needed
  "score": 850,              // Number - not a string
  "price": 19.99,            // Decimal - not a string
  "active": true             // Boolean - not a string
}
```

**Generated code** adds language-specific syntax automatically:

| JSON Type | JSON Value | Generated Python Code |
| --------- | ---------- | --------------------- |
| String    | `"user-123"` | `"user-123"` |
| Integer   | `850` | `850` |
| Decimal   | `19.99` | `Decimal("19.99")` |
| Boolean   | `true` | `True` |

**Important**: Store numbers as JSON numbers, not strings, to ensure correct type handling in generated code.

## Complete Example

```json
{
  "entities": {
    "User": {
      "sample_data": {
        "user_id": "user-67890",
        "username": "dealseeker123",
        "email": "john.doe@example.com",
        "display_name": "John Doe",
        "created_at": "2024-01-10T08:30:00Z",
        "last_login": "2024-01-15T09:45:00Z"
      },
      "access_pattern_data": {
        "user_id": "user_id123",
        "username": "sample_username",
        "email": "sample_email",
        "display_name": "sample_display_name",
        "created_at": "sample_created_at",
        "last_login": "sample_last_login"
      },
      "update_data": {
        "username": "dealhunter123",
        "display_name": "John D. Smith",
        "last_login": "2024-01-16T14:20:00Z"
      }
    }
  }
}
```

### Generated Code Impact

**Create Operation (uses `sample_data`):**
```python
user = User(
    user_id="user-67890",
    username="dealseeker123",
    email="john.doe@example.com",
    display_name="John Doe",
    created_at="2024-01-10T08:30:00Z",
    last_login="2024-01-15T09:45:00Z"
)
created_user = user_repo.create_user(user)
```

**Get Operation (uses `access_pattern_data`):**
```python
retrieved_user = user_repo.get_user("user_id123")
```

**Update Operation (uses `update_data`):**
```python
user.username = "dealhunter123"
user.display_name = "John D. Smith"
user.last_login = "2024-01-16T14:20:00Z"
updated_user = user_repo.update_user(user)
```

## Field Types

### String Fields
```json
{
  "user_id": "user-67890",
  "email": "john.doe@example.com",
  "status": "active"
}
```

### Numeric Fields
```json
{
  "price": 149.99,
  "quantity": 5,
  "engagement_score": 850
}
```

### Timestamp Fields
```json
{
  "created_at": "2024-01-15T10:00:00Z",
  "last_login": "2024-01-15T09:45:00Z"
}
```

### Complex/Object Fields
```json
{
  "details": {
    "deal_id": "deal-12345",
    "source": "homepage",
    "duration_seconds": 45
  }
}
```

### Array Fields
```json
{
  "tags": ["electronics", "premium", "wireless"],
  "categories": ["audio", "headphones"]
}
```

## Best Practices

### Use Realistic Values

**Good:**
```json
{
  "email": "john.doe@example.com",
  "price": 149.99,
  "status": "active"
}
```

**Avoid:**
```json
{
  "email": "test@test.com",
  "price": 1.00,
  "status": "test"
}
```

### Include All Required Fields

Ensure `sample_data` includes all required fields from your schema:

```json
{
  "sample_data": {
    "user_id": "user-67890",
    "username": "dealseeker123",
    "email": "john@example.com"
  }
}
```

### Use Domain-Appropriate Values

**E-commerce:**
```json
{
  "product_id": "prod-12345",
  "price": 29.99,
  "category": "electronics"
}
```

**Social Media:**
```json
{
  "user_id": "user-67890",
  "username": "johndoe",
  "followers": 1250
}
```

## Validation

`usage_data.json` is automatically validated during code generation:

```bash
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen \
  --schema schema.json \
  --usage-data-path usage_data.json
```

**Validation checks:**
- ✅ Valid JSON format
- ✅ Presence of 'entities' key
- ✅ All schema entities are present
- ⚠️ Warnings for unknown entities
- ❌ Errors for missing entities

**Example errors:**
```
ERROR: usage_data.json: Missing required entities: ['Post', 'Comment']
ERROR: usage_data.json: Invalid JSON format
```

**Example warnings:**
```
WARNING: usage_data.json: Unknown entities (not in schema): ['Comment']
```

## Usage

```bash
# Generate with usage data
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen \
  --schema schema.json \
  --generate_sample_usage \
  --usage-data-path usage_data.json
```

## Example Files

Complete examples are available in test fixtures:

- `tests/repo_generation_tool/fixtures/valid_usage_data/deals_app/deals_usage_data.json`
- `tests/repo_generation_tool/fixtures/valid_usage_data/ecommerce_app/ecommerce_usage_data.json`
- `tests/repo_generation_tool/fixtures/valid_usage_data/elearning_platform/elearning_usage_data.json`
- `tests/repo_generation_tool/fixtures/valid_usage_data/gaming_leaderboard/gaming_leaderboard_usage_data.json`
- `tests/repo_generation_tool/fixtures/valid_usage_data/saas_app/project_management_usage_data.json`
- `tests/repo_generation_tool/fixtures/valid_usage_data/social_media_app/social_media_app_usage_data.json`
- `tests/repo_generation_tool/fixtures/valid_usage_data/user_analytics/user_analytics_usage_data.json`
