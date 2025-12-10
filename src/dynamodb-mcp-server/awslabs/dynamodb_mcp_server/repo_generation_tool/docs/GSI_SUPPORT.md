# Global Secondary Index (GSI) Support

This document provides comprehensive information about GSI support in the DynamoDB code generator.

## 🎯 Overview

The generator provides full support for DynamoDB Global Secondary Indexes (GSIs), automatically generating:

- GSI key builder methods for entities
- GSI prefix helper methods for queries
- Repository methods with complete GSI query examples
- Comprehensive validation of GSI configurations

**Note:** Range query support (begins_with, between, >=, <=, >, <) works for both GSI sort keys and main table sort keys. For complete range query documentation, see [Range Queries](RANGE_QUERIES.md).

## 📋 Schema Structure

### Table Configuration with GSIs

Define GSIs in the `gsi_list` array within `table_config`. GSIs can have sort keys for sorted queries, or be partition-key-only for simple lookups:

```json
{
  "table_config": {
    "table_name": "UserAnalytics",
    "partition_key": "pk",
    "sort_key": "sk"
  },
  "gsi_list": [
    {
      "name": "StatusIndex",
      "partition_key": "status_pk",
      "sort_key": "last_active_sk"
    },
    {
      "name": "LocationIndex",
      "partition_key": "country_pk",
      "sort_key": "city_sk"
    },
    {
      "name": "CategoryIndex",
      "partition_key": "category_pk"
    }
  ]
}
```

**Note**: The `sort_key` field is optional. Omit it for partition-key-only GSIs used for simple lookups.

### Entity GSI Mappings

Map entity fields to GSI keys using `gsi_mappings`. The `sk_template` is optional for partition-key-only GSIs:

```json
{
  "entity_type": "USER",
  "pk_template": "USER#{user_id}",
  "sk_template": "PROFILE",
  "gsi_mappings": [
    {
      "name": "StatusIndex",
      "pk_template": "STATUS#{status}",
      "sk_template": "{last_active}"
    },
    {
      "name": "LocationIndex",
      "pk_template": "COUNTRY#{country}",
      "sk_template": "CITY#{city}"
    },
    {
      "name": "CategoryIndex",
      "pk_template": "{category_id}"
    }
  ]
}
```

**Note**: When a GSI has no sort key, omit the `sk_template` field. The generator will only create partition key builder methods for that GSI.

### GSI Access Patterns

Define access patterns that use GSIs:

```json
{
  "pattern_id": 2,
  "name": "get_active_users",
  "description": "Get users by status",
  "operation": "Query",
  "index_name": "StatusIndex",
  "parameters": [{ "name": "status", "type": "string" }],
  "return_type": "entity_list"
}
```

## 🔑 Generated GSI Methods

For each GSI mapping, the generator creates methods based on whether the GSI has a sort key:

### Partition-Key-Only GSIs

For GSIs without sort keys, only partition key methods are generated:

```python
@classmethod
def build_gsi_pk_for_lookup_categoryindex(cls, category_id) -> str:
    """Build GSI partition key for CategoryIndex lookup operations"""
    return f"{category_id}"

def build_gsi_pk_categoryindex(self) -> str:
    """Build GSI partition key for CategoryIndex from entity instance"""
    return f"{self.category_id}"

@classmethod
def get_gsi_pk_prefix_categoryindex(cls) -> str:
    """Get GSI partition key prefix for CategoryIndex query operations"""
    return ""
```

### GSIs with Sort Keys

For GSIs with sort keys, the generator creates three types of methods:

### 1. Class Methods (for lookups)

Used when building queries with specific parameter values:

```python
@classmethod
def build_gsi_pk_for_lookup_statusindex(cls, status) -> str:
    """Build GSI partition key for StatusIndex lookup operations"""
    return f"STATUS#{status}"

@classmethod
def build_gsi_sk_for_lookup_statusindex(cls, last_active) -> str:
    """Build GSI sort key for StatusIndex lookup operations"""
    return f"{last_active}"
```

### 2. Instance Methods (for entity instances)

Used when an entity instance needs to generate its GSI keys:

```python
def build_gsi_pk_statusindex(self) -> str:
    """Build GSI partition key for StatusIndex from entity instance"""
    return f"STATUS#{self.status}"

def build_gsi_sk_statusindex(self) -> str:
    """Build GSI sort key for StatusIndex from entity instance"""
    return f"{self.last_active}"
```

### 3. Prefix Helper Methods

Used for range queries and pattern matching:

```python
@classmethod
def get_gsi_pk_prefix_statusindex(cls) -> str:
    """Get GSI partition key prefix for StatusIndex query operations"""
    return "STATUS#"

@classmethod
def get_gsi_sk_prefix_statusindex(cls) -> str:
    """Get GSI sort key prefix for StatusIndex query operations"""
    return ""
```

## 🔍 Range Conditions

GSI access patterns support DynamoDB range conditions for sort keys:

| Condition      | Description                          | Parameters Required | Example Use Case                    |
| -------------- | ------------------------------------ | ------------------- | ----------------------------------- |
| `begins_with`  | Prefix matching                      | 1 range parameter   | Find cities starting with "Sea"     |
| `between`      | Range between two values             | 2 range parameters  | Users with 10-100 sessions          |
| `>=`           | Greater than or equal                | 1 range parameter   | Active since a specific date        |
| `<=`           | Less than or equal                   | 1 range parameter   | Sessions below threshold            |
| `>`            | Greater than                         | 1 range parameter   | After a specific timestamp          |
| `<`            | Less than                            | 1 range parameter   | Before a specific date              |

### Range Condition Example

```json
{
  "pattern_id": 3,
  "name": "get_recent_active_users",
  "description": "Get recently active users by status",
  "operation": "Query",
  "index_name": "StatusIndex",
  "range_condition": ">=",
  "parameters": [
    { "name": "status", "type": "string" },
    { "name": "since_date", "type": "string" }
  ],
  "return_type": "entity_list"
}
```

## 📝 Generated Repository Code

### Simple GSI Query

For access patterns without range conditions:

```python
def get_active_users(self, status: str) -> list[User]:
    """Get users by status

    Access Pattern #2: Get users by status
    Operation: Query
    Index: StatusIndex (GSI)
    Query Type: Simple Query

    GSI Query Implementation:
    - Use table.query() with IndexName='StatusIndex'
    - Build GSI keys using User.build_gsi_pk_for_lookup_statusindex()
      and User.build_gsi_sk_for_lookup_statusindex()
    """
    # TODO: Implement this access pattern
    # GSI Query Example:
    # response = self.table.query(
    #     IndexName='StatusIndex',
    #     KeyConditionExpression=Key('status_pk').eq(gsi_pk_value) & Key('last_active_sk').eq(gsi_sk_value)
    # )
    pass
```

### Range Query with begins_with

```python
def get_users_by_country_prefix(self, country: str, city_prefix: str) -> list[User]:
    """Get users by country with city prefix

    Access Pattern #5: Get users by country with city prefix
    Operation: Query
    Index: LocationIndex (GSI)
    Range Condition: begins_with
    Query Type: Range Query

    Range Query Implementation Hints:
    - Use Key('sort_key').begins_with(prefix_value)
    - Requires 1 range parameter in addition to partition key
    """
    # TODO: Implement this access pattern
    # GSI Query Example:
    # response = self.table.query(
    #     IndexName='LocationIndex',
    #     KeyConditionExpression=Key('country_pk').eq(gsi_pk_value) & Key('city_sk').begins_with(range_value)
    # )
    pass
```

### Range Query with between

```python
def get_highly_engaged_users_by_session_range(
    self, engagement_level: str, min_sessions: int, max_sessions: int
) -> list[User]:
    """Get highly engaged users within session count range

    Range Condition: between
    Range Query Implementation Hints:
    - Use Key('sort_key').between(start_value, end_value)
    - Requires 2 range parameters in addition to partition key
    """
    # TODO: Implement this access pattern
    # GSI Query Example:
    # response = self.table.query(
    #     IndexName='EngagementIndex',
    #     KeyConditionExpression=Key('engagement_level_pk').eq(gsi_pk_value) & Key('session_count_sk').between(range_value)
    # )
    pass
```

## 🔧 Template Syntax

### Static Text

Use literal strings for fixed prefixes:

```json
{
  "pk_template": "STATUS#active"
}
```

### Field References

Use `{field_name}` to reference entity fields:

```json
{
  "sk_template": "{last_active}"
}
```

### Combined

Mix static text and field references:

```json
{
  "pk_template": "STATUS#{status}",
  "sk_template": "CITY#{city}"
}
```

### Complex Multi-Part Keys

Build hierarchical keys:

```json
{
  "pk_template": "TENANT#{tenant_id}#USER#{user_id}",
  "sk_template": "DOC#{document_id}#VERSION#{version}"
}
```

## ✅ GSI Validation

The generator performs comprehensive validation:

### 1. GSI Name Matching

- GSI names in `gsi_list` must match names in entity `gsi_mappings`
- Warns about unused GSIs defined in `gsi_list`
- Errors on undefined GSIs referenced in `gsi_mappings`

### 2. Field Reference Validation

- All fields referenced in GSI templates must exist in entity `fields`
- Template parameters are automatically extracted and validated
- Clear error messages for missing or invalid field references

### 3. Access Pattern Validation

- `index_name` in access patterns must reference existing GSIs
- Range conditions are validated against supported operators
- Parameter counts are validated for range conditions

### 4. Template Syntax Validation

- Validates template syntax (e.g., `{field_name}`)
- Ensures proper bracket matching
- Detects invalid characters or malformed templates

## 💡 Usage Examples

### Implementing a GSI Query

```python
def get_active_users(self, status: str) -> list[User]:
    # Build the GSI partition key
    gsi_pk = User.build_gsi_pk_for_lookup_statusindex(status)

    # Query the GSI
    response = self.table.query(
        IndexName='StatusIndex',
        KeyConditionExpression=Key('status_pk').eq(gsi_pk)
    )

    # Process and return results
    items = response.get('Items', [])
    return [User(**item) for item in items]
```

### Using Prefix Helpers for Range Queries

```python
def get_users_by_country_prefix(self, country: str, city_prefix: str) -> list[User]:
    # Build the partition key
    gsi_pk = User.build_gsi_pk_for_lookup_locationindex(country)

    # Use prefix helper to build the begins_with condition
    city_prefix_with_format = User.get_gsi_sk_prefix_locationindex() + city_prefix

    # Query with begins_with
    response = self.table.query(
        IndexName='LocationIndex',
        KeyConditionExpression=Key('country_pk').eq(gsi_pk) &
                              Key('city_sk').begins_with(city_prefix_with_format)
    )

    items = response.get('Items', [])
    return [User(**item) for item in items]
```

## 🎯 Best Practices

### 1. GSI Design

- **Choose meaningful GSI names**: Use descriptive names like `StatusIndex`, `LocationIndex`
- **Plan your access patterns**: Design GSIs based on your query requirements
- **Consider cardinality**: Ensure good distribution of partition key values

### 2. Template Design

- **Use consistent prefixes**: Help identify key types (e.g., `STATUS#`, `COUNTRY#`)
- **Keep templates simple**: Avoid overly complex multi-part keys unless necessary
- **Document your patterns**: Use clear descriptions in access patterns

### 3. Range Conditions

- **Use appropriate operators**: Choose the right range condition for your use case
- **Consider sort key design**: Design sort keys to support your range queries
- **Test edge cases**: Validate behavior with boundary values

### 4. Validation

- **Run validation early**: Use `--validate-only` flag during development
- **Fix validation errors**: Address all errors before generating code
- **Review warnings**: Consider warnings about unused GSIs

## 🔍 Troubleshooting

### Common Issues

**Issue**: GSI name mismatch error

```
Error: GSI 'StatusIdx' referenced in entity 'User' gsi_mappings but not found in table gsi_list
```

**Solution**: Ensure GSI names match exactly between `gsi_list` and `gsi_mappings`

---

**Issue**: Field reference error

```
Error: Field 'user_status' referenced in GSI template but not found in entity fields
```

**Solution**: Verify all fields referenced in templates exist in the entity's `fields` array

---

**Issue**: Invalid range condition

```
Error: Invalid range_condition 'contains' for access pattern. Supported: begins_with, between, >=, <=, >, <
```

**Solution**: Use only supported DynamoDB range conditions

---

**Issue**: Missing range parameters

```
Error: Range condition 'between' requires 2 range parameters but access pattern has 1
```

**Solution**: Ensure parameter count matches range condition requirements

## 📚 Complete Example

See the `user_analytics` schema in `tests/repo_generation_tool/fixtures/valid_schemas/user_analytics/` for a complete working example with:

- 4 different GSIs
- Multiple range conditions
- Various template patterns
- Complete access pattern definitions

## 🚀 Next Steps

1. **Review the user_analytics example**: Study the complete schema and generated code
2. **Design your GSIs**: Plan your access patterns and GSI structure
3. **Create your schema**: Define `gsi_list` and `gsi_mappings`
4. **Validate**: Run with `--validate-only` flag
5. **Generate**: Create your code with `--generate_sample_usage`
6. **Implement**: Fill in the repository method bodies
7. **Test**: Verify your GSI queries work as expected

---

For more information, see:
- [Schema Validation](SCHEMA_VALIDATION.md) - Detailed validation rules
- [Advanced Usage](ADVANCED_USAGE.md) - Complex patterns and troubleshooting
- [Testing Framework](TESTING.md) - Testing your generated code
