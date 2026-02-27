# Range Query Support

This document provides comprehensive information about range query support for both main table sort keys and Global Secondary Index (GSI) sort keys in the DynamoDB code generator.

## 🎯 Overview

The generator provides full support for DynamoDB range queries on both:
- **Main Table Sort Keys (SK)** - Query patterns on the primary table's sort key
- **GSI Sort Keys** - Query patterns on Global Secondary Index sort keys

Range queries automatically generate:
- Validation for range conditions and parameter counts
- Repository method stubs with detailed implementation hints
- Complete query examples in generated code comments

## 📋 Supported Range Conditions

All DynamoDB range query operators are supported:

| Condition      | Description                          | Parameters Required | Use Case                            |
| -------------- | ------------------------------------ | ------------------- | ----------------------------------- |
| `begins_with`  | Prefix matching                      | 1 range parameter   | Find items starting with a prefix   |
| `between`      | Range between two values             | 2 range parameters  | Items within a range                |
| `>=`           | Greater than or equal                | 1 range parameter   | Items after a threshold             |
| `<=`           | Less than or equal                   | 1 range parameter   | Items before a threshold            |
| `>`            | Greater than                         | 1 range parameter   | Items strictly after a value        |
| `<`            | Less than                            | 1 range parameter   | Items strictly before a value       |

## 🔑 Main Table Range Queries

### Schema Structure

Define range queries on the main table by specifying `range_condition` without `index_name`:

```json
{
  "access_patterns": [
    {
      "pattern_id": 1,
      "name": "get_user_posts_after_date",
      "description": "Get all posts by a user after a specific date",
      "operation": "Query",
      "parameters": [
        { "name": "user_id", "type": "string" },
        { "name": "since_date", "type": "string" }
      ],
      "return_type": "entity_list",
      "range_condition": ">="
    }
  ]
}
```

**Key Points:**
- No `index_name` field = main table query
- `operation` must be `"Query"`
- Parameter count must match range condition requirements

### Generated Code Example

```python
def get_user_posts_after_date(self, user_id: str, since_date: str) -> list[Post]:
    """Get all posts by a user after a specific date

    Access Pattern #1: Get all posts by a user after a specific date
    Operation: Query
    Index: Main Table
    Range Condition: >=
    Query Type: Range Query

    Key Conditions:
    - Partition Key: USER#{user_id}
    - Sort Key: POST#{timestamp}

    Range Query Implementation:
    - Use Key('sk').>=(comparison_value)
    - Requires 1 range parameter in addition to partition key
    - Example: Find all items where sort key is greater than or equal to a value

    Main Table Query Implementation:
    - Use table.query() or table.get_item() depending on operation
    - Build keys using Post.build_pk_for_lookup() and Post.build_sk_for_lookup()
    """
    # TODO: Implement this access pattern
    # Main Table Query Example:
    # response = self.table.query(
    #     KeyConditionExpression=Key('pk').eq(pk_value) & Key('sk').>=(range_value)
    # )
    pass
```

## 🔍 GSI Range Queries

### Schema Structure

Define range queries on GSI by specifying both `index_name` and `range_condition`:

```json
{
  "gsi_list": [
    {
      "name": "StatusIndex",
      "partition_key": "status_pk",
      "sort_key": "last_active_sk"
    }
  ],
  "entities": {
    "User": {
      "gsi_mappings": [
        {
          "name": "StatusIndex",
          "pk_template": "STATUS#{status}",
          "sk_template": "{last_active}"
        }
      ],
      "access_patterns": [
        {
          "pattern_id": 1,
          "name": "get_recent_active_users",
          "description": "Get recently active users by status",
          "operation": "Query",
          "index_name": "StatusIndex",
          "parameters": [
            { "name": "status", "type": "string" },
            { "name": "since_date", "type": "string" }
          ],
          "return_type": "entity_list",
          "range_condition": ">="
        }
      ]
    }
  }
}
```

**Key Points:**
- `index_name` field references a GSI from `gsi_list`
- GSI must be defined in `gsi_list` before use
- Entity must have corresponding `gsi_mappings` entry

### Multi-Attribute Keys with Range Queries

GSIs can use multi-attribute keys (up to 4 attributes per key). Range conditions apply to the LAST sort key attribute:

```json
{
  "gsi_list": [
    {
      "name": "StoreActiveDeliveries",
      "partition_key": "store_id",
      "sort_key": ["status", "created_at"],
      "projection": "ALL"
    }
  ],
  "entities": {
    "Order": {
      "gsi_mappings": [
        {
          "name": "StoreActiveDeliveries",
          "pk_template": "{store_id}",
          "sk_template": ["{status}", "{created_at}"]
        }
      ],
      "access_patterns": [
        {
          "pattern_id": 1,
          "name": "get_store_in_transit_deliveries",
          "description": "Get in-transit deliveries filtered by status",
          "operation": "Query",
          "index_name": "StoreActiveDeliveries",
          "range_condition": "begins_with",
          "parameters": [
            { "name": "store_id", "type": "string" },
            { "name": "status", "type": "string" },
            { "name": "created_at", "type": "string" }
          ],
          "return_type": "entity_list"
        }
      ]
    }
  }
}
```

**Multi-Attribute Range Query Rules:**
- Sort key attributes must be queried left-to-right — you can stop at any point
- The range condition applies to the LAST QUERIED SK attribute, not necessarily the last attribute in the GSI definition
- Minimum parameter count = PK attributes + range parameters (range on first SK attribute)
- Maximum parameter count = PK attributes + (SK attributes - 1) + range parameters (all SK equality + range on last)
- Example with 1 PK + 2 SK attributes (`begins_with`):
  - Minimum: 1 PK + 1 range = 2 params (range on first SK)
  - Maximum: 1 PK + 1 SK equality + 1 range = 3 params (equality on first SK, range on second)
- Generated query: `Key('status').eq(status) & Key('created_at').begins_with(prefix)`

### Generated Code Example

```python
def get_recent_active_users(self, status: str, since_date: str) -> list[User]:
    """Get recently active users by status

    Access Pattern #1: Get recently active users by status
    Operation: Query
    Index: StatusIndex (GSI)
    Range Condition: >=
    Query Type: Range Query

    Key Conditions:
    - GSI Partition Key: STATUS#{status}
    - GSI Sort Key: {last_active}

    Range Query Implementation:
    - Use Key('last_active_sk').>=(comparison_value)
    - Requires 1 range parameter in addition to partition key

    GSI Query Implementation:
    - Use table.query() with IndexName='StatusIndex'
    - Build GSI keys using User.build_gsi_pk_for_lookup_statusindex()
      and User.build_gsi_sk_for_lookup_statusindex()
    """
    # TODO: Implement this access pattern
    # GSI Query Example:
    # response = self.table.query(
    #     IndexName='StatusIndex',
    #     KeyConditionExpression=Key('status_pk').eq(gsi_pk_value) & Key('last_active_sk').>=(range_value)
    # )
    pass
```

## 📝 Complete Examples

### Example 1: Main Table - Posts by Date Range

```json
{
  "table_config": {
    "table_name": "UserPosts",
    "partition_key": "pk",
    "sort_key": "sk"
  },
  "entities": {
    "Post": {
      "entity_type": "POST",
      "pk_template": "USER#{user_id}",
      "sk_template": "POST#{timestamp}",
      "fields": [
        { "name": "user_id", "type": "string", "required": true },
        { "name": "timestamp", "type": "string", "required": true },
        { "name": "title", "type": "string", "required": true }
      ],
      "access_patterns": [
        {
          "pattern_id": 1,
          "name": "get_user_posts_in_date_range",
          "description": "Get posts within a date range",
          "operation": "Query",
          "parameters": [
            { "name": "user_id", "type": "string" },
            { "name": "start_date", "type": "string" },
            { "name": "end_date", "type": "string" }
          ],
          "return_type": "entity_list",
          "range_condition": "between"
        }
      ]
    }
  }
}
```

### Example 2: GSI - Users by Activity

```json
{
  "table_config": {
    "table_name": "Users",
    "partition_key": "pk",
    "sort_key": "sk"
  },
  "gsi_list": [
    {
      "name": "ActivityIndex",
      "partition_key": "activity_pk",
      "sort_key": "last_login_sk"
    }
  ],
  "entities": {
    "User": {
      "entity_type": "USER",
      "pk_template": "USER#{user_id}",
      "sk_template": "PROFILE",
      "gsi_mappings": [
        {
          "name": "ActivityIndex",
          "pk_template": "ACTIVE",
          "sk_template": "{last_login}"
        }
      ],
      "fields": [
        { "name": "user_id", "type": "string", "required": true },
        { "name": "last_login", "type": "string", "required": true }
      ],
      "access_patterns": [
        {
          "pattern_id": 1,
          "name": "get_users_logged_in_after",
          "description": "Get users who logged in after a date",
          "operation": "Query",
          "index_name": "ActivityIndex",
          "parameters": [
            { "name": "since_date", "type": "string" }
          ],
          "return_type": "entity_list",
          "range_condition": ">="
        }
      ]
    }
  }
}
```

### Example 3: Prefix Matching with begins_with

```json
{
  "access_patterns": [
    {
      "pattern_id": 1,
      "name": "get_user_posts_by_month",
      "description": "Get posts in a specific month",
      "operation": "Query",
      "parameters": [
        { "name": "user_id", "type": "string" },
        { "name": "month_prefix", "type": "string" }
      ],
      "return_type": "entity_list",
      "range_condition": "begins_with"
    }
  ]
}
```

**Usage:**
```python
# Get all posts from January 2024
posts = repo.get_user_posts_by_month("user123", "2024-01")
```

## ✅ Validation Rules

The generator performs comprehensive validation:

### 1. Range Condition Validation
- Must be one of: `begins_with`, `between`, `>`, `<`, `>=`, `<=`
- Case-sensitive validation
- Clear error messages with suggestions

### 2. Parameter Count Validation
- For single-attribute keys: `between` requires exactly 3 parameters (PK + 2 range values), all others require exactly 2 (PK + 1 range value)
- For multi-attribute keys: parameter count must be between minimum (PK count + range values) and maximum (PK count + SK count - 1 + range values), following the left-to-right SK query rule
- Helpful error messages indicate how many parameters to add/remove

### 3. Operation Compatibility
- Range conditions only work with `Query` operations
- Error if used with `GetItem`, `PutItem`, etc.

### 4. Index Reference Validation (GSI only)
- `index_name` must reference an existing GSI in `gsi_list`
- GSI must have corresponding `gsi_mappings` entry in entity

## 🔧 Implementation Guide

### Step 1: Define Your Schema

Choose whether you need main table or GSI range queries:

**Main Table:**
```json
{
  "access_patterns": [
    {
      "pattern_id": 1,
      "name": "query_name",
      "operation": "Query",
      "parameters": [...],
      "return_type": "entity_list",
      "range_condition": ">="
    }
  ]
}
```

**GSI:**
```json
{
  "gsi_list": [...],
  "entities": {
    "EntityName": {
      "gsi_mappings": [...],
      "access_patterns": [
        {
          "pattern_id": 1,
          "name": "query_name",
          "operation": "Query",
          "index_name": "YourGSI",
          "parameters": [...],
          "return_type": "entity_list",
          "range_condition": ">="
        }
      ]
    }
  }
}
```

### Step 2: Validate Your Schema

```bash
# From dynamodb-mcp-server root
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema schema.json --validate-only
```

### Step 3: Generate Code

```bash
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema schema.json
```

### Step 4: Implement Query Logic

The generated repository methods include detailed comments. Example implementation:

```python
def get_user_posts_after_date(self, user_id: str, since_date: str) -> list[Post]:
    """Get all posts by a user after a specific date"""
    # Build partition key
    pk = Post.build_pk_for_lookup(user_id)

    # Build sort key prefix for the range query
    sk_prefix = f"POST#{since_date}"

    # Query with range condition
    response = self.table.query(
        KeyConditionExpression=Key('pk').eq(pk) & Key('sk').gte(sk_prefix)
    )

    # Process and return results
    items = response.get('Items', [])
    return [Post(**item) for item in items]
```

## 🎯 Best Practices

### 1. Sort Key Design

Design sort keys to support your range queries:

**Good:**
```json
{
  "sk_template": "POST#{timestamp}",
  "range_condition": ">="
}
```
- Timestamp in sort key enables date-based range queries
- Consistent format allows reliable comparisons

**Also Good:**
```json
{
  "sk_template": "SCORE#{score}#USER#{user_id}",
  "range_condition": "between"
}
```
- Score prefix enables score-based range queries
- Additional user_id ensures uniqueness

### 2. Parameter Naming

Use descriptive parameter names:

**Good:**
```json
{
  "parameters": [
    { "name": "user_id", "type": "string" },
    { "name": "since_date", "type": "string" }
  ]
}
```

**Avoid:**
```json
{
  "parameters": [
    { "name": "pk", "type": "string" },
    { "name": "value", "type": "string" }
  ]
}
```

### 3. Choose the Right Condition

| Use Case                          | Condition      | Example                                |
| --------------------------------- | -------------- | -------------------------------------- |
| Items after a date                | `>=` or `>`    | Posts since yesterday                  |
| Items before a date               | `<=` or `<`    | Orders before cutoff                   |
| Items within a range              | `between`      | Scores between 80-100                  |
| Items matching a prefix           | `begins_with`  | Posts in January (prefix: "2024-01")   |

### 4. Validation During Development

Run validation frequently:

```bash
# Quick validation (from dynamodb-mcp-server root)
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema schema.json --validate-only

# Generate and test
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema schema.json --generate_sample_usage
```

## 🔍 Troubleshooting

### Common Issues

**Issue**: Invalid range condition error

```
Error: Invalid range_condition 'greater_than'
```

**Solution**: Use the exact operator: `>`, `>=`, `<`, `<=`, `begins_with`, or `between`

---

**Issue**: Wrong parameter count

```
Error: Range condition '>=' requires exactly 2 parameters (partition key + 1 range value), got 3
```

**Solution**: Check your parameters array - you have too many parameters for this condition

---

**Issue**: Range condition with GetItem

```
Error: Range conditions require 'Query' operation, got 'GetItem'
```

**Solution**: Change `operation` to `"Query"` or remove `range_condition`

---

**Issue**: GSI not found

```
Error: Access pattern references unknown GSI 'StatusIndex'
```

**Solution**: Ensure the GSI is defined in `gsi_list` and the name matches exactly

## 📚 Related Documentation

- [GSI Support](GSI_SUPPORT.md) - Complete guide to Global Secondary Index support
- [Schema Validation](SCHEMA_VALIDATION.md) - Detailed validation rules
- [Advanced Usage](ADVANCED_USAGE.md) - Complex patterns and troubleshooting

## 🚀 Next Steps

1. **Design your access patterns** - Identify which queries need range conditions
2. **Choose main table vs GSI** - Decide based on your query requirements
3. **Define your schema** - Add range_condition to access patterns
4. **Validate** - Run with `--validate-only` flag
5. **Generate** - Create your code with `--generate_sample_usage`
6. **Implement** - Fill in the repository method bodies
7. **Test** - Verify your range queries work as expected

---

For more information, see the complete documentation in the `documentation/` directory.
