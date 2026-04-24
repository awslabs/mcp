# Filter Expression Support

This document provides comprehensive information about filter expression support in the DynamoDB code generator.

## 🎯 Overview

The generator supports DynamoDB filter expressions on Query and Scan access patterns. Filter expressions are applied server-side after data is read from the table but before results are returned to the client.

**Key Characteristics:**
- Applied after data is read, before returning to client
- For Query: cannot filter on partition key or sort key (those go in KeyConditionExpression)
- For Scan: can filter on any attribute, including PK/SK (there is no KeyConditionExpression in a Scan)
- Read capacity is consumed based on data read, not filtered results
- 1 MB limit applies before filter expression is evaluated
- Best used when excluding only a small set of items

The generator produces:
- Filter parameters in repository method signatures
- Filter Expression documentation in method docstrings
- Implementation hints with FilterExpression, ExpressionAttributeNames, and ExpressionAttributeValues
- Filter metadata in access_pattern_mapping.json

## 📋 Schema Structure

Add a `filter_expression` section to any Query or Scan access pattern:

```json
{
  "access_patterns": [
    {
      "pattern_id": 1,
      "name": "get_active_customer_orders",
      "description": "Get non-cancelled orders with minimum total",
      "operation": "Query",
      "parameters": [
        { "name": "customer_id", "type": "string" },
        { "name": "excluded_status", "type": "string", "default": "CANCELLED" },
        { "name": "min_total", "type": "decimal" }
      ],
      "return_type": "entity_list",
      "filter_expression": {
        "conditions": [
          { "field": "status", "operator": "<>", "param": "excluded_status" },
          { "field": "total", "operator": ">=", "param": "min_total" }
        ],
        "logical_operator": "AND"
      }
    }
  ]
}
```

**Key Design Points:**
- Filter parameters are defined in the `parameters` array (same as key/range parameters)
- Each condition references a parameter by name via the `param` field
- Default values are specified in `parameters[].default`
- Functions like `attribute_exists` don't need a `param`
- `logical_operator` defaults to `AND` when omitted

## 🔧 Supported Filter Operations

### Comparison Operators

| Operator | Description | Schema | Generated |
|----------|-------------|--------|-----------|
| `=` | Equal | `{"field": "status", "operator": "=", "param": "val"}` | `#status = :val` |
| `<>` | Not equal | `{"field": "status", "operator": "<>", "param": "val"}` | `#status <> :val` |
| `<` | Less than | `{"field": "price", "operator": "<", "param": "max"}` | `#price < :max` |
| `<=` | Less than or equal | `{"field": "price", "operator": "<=", "param": "max"}` | `#price <= :max` |
| `>` | Greater than | `{"field": "qty", "operator": ">", "param": "min"}` | `#qty > :min` |
| `>=` | Greater than or equal | `{"field": "total", "operator": ">=", "param": "min"}` | `#total >= :min` |

### Between Operator

```json
{ "field": "price", "operator": "between", "param": "min_price", "param2": "max_price" }
```
Generated: `#price BETWEEN :min_price AND :max_price`

### In Operator

```json
{ "field": "status", "operator": "in", "params": ["status1", "status2", "status3"] }
```
Generated: `#status IN (:status1, :status2, :status3)`

### Functions

| Function | Param Required | Schema | Generated |
|----------|---------------|--------|-----------|
| `contains` | Yes | `{"field": "tags", "function": "contains", "param": "tag"}` | `contains(#tags, :tag)` |
| `begins_with` | Yes | `{"field": "name", "function": "begins_with", "param": "prefix"}` | `begins_with(#name, :prefix)` |
| `attribute_exists` | No | `{"field": "email", "function": "attribute_exists"}` | `attribute_exists(#email)` |
| `attribute_not_exists` | No | `{"field": "deleted", "function": "attribute_not_exists"}` | `attribute_not_exists(#deleted)` |

### Size Function

The `size` function requires both `function` and `operator`:

```json
{ "field": "items", "function": "size", "operator": ">", "param": "min_items" }
```
Generated: `size(#items) > :min_items`

With between:
```json
{ "field": "items", "function": "size", "operator": "between", "param": "min", "param2": "max" }
```
Generated: `size(#items) BETWEEN :min AND :max`

### Logical Operators

Combine multiple conditions with `AND` or `OR`:

```json
{
  "filter_expression": {
    "conditions": [
      { "field": "status", "operator": "<>", "param": "excluded" },
      { "field": "total", "operator": ">=", "param": "min_total" }
    ],
    "logical_operator": "AND"
  }
}
```

## 🏗️ Generated Code

### Method Signature

Filter parameters appear in the method signature with appropriate Python types:

```python
def get_active_customer_orders(
    self,
    customer_id: str,
    min_total: Decimal,
    excluded_status: str = "CANCELLED",
    limit: int = 100,
    exclusive_start_key: dict | None = None,
    skip_invalid_items: bool = True
) -> tuple[list[Order], dict | None]:
```

### Docstring

```python
    """Get non-cancelled orders for a customer with minimum total

    Filter Expression: #status <> :excluded_status AND #total >= :min_total
    Note: Filter expressions are applied AFTER data is read from DynamoDB.
    Read capacity is consumed based on items read, not items returned.
    """
```

### Implementation Hints

```python
    # Filter Expression Implementation:
    #     'FilterExpression': '#status <> :excluded_status AND #total >= :min_total',
    #     'ExpressionAttributeNames': {
    #         '#status': 'status',
    #         '#total': 'total',
    #     },
    #     'ExpressionAttributeValues': {
    #         ':excluded_status': excluded_status,
    #         ':min_total': min_total,
    #     },
```

## ✅ Validation Rules

The schema validator enforces:

1. **Field existence**: All fields referenced in filters must exist in entity fields
2. **No key attributes in Query**: For Query operations, filter expressions cannot reference partition key or sort key fields (use KeyConditionExpression instead). For Scan operations, filtering on key attributes is allowed since Scan has no KeyConditionExpression.
3. **Operator validity**: Only `=`, `<>`, `<`, `<=`, `>`, `>=`, `between`, `in`
4. **Function validity**: Only `contains`, `begins_with`, `attribute_exists`, `attribute_not_exists`, `size`
5. **Logical operator validity**: Only `AND` or `OR`
6. **Operator/function exclusivity**: Only one of `operator` or `function` allowed (except `size` which requires both)
7. **Parameter requirements**: `between` requires `param` + `param2`, `in` requires `params` array, comparison operators require `param`, `contains`/`begins_with` require `param`, `attribute_exists`/`attribute_not_exists` require no params
8. **Operation compatibility**: Filter expressions only valid for `Query` and `Scan` operations
9. **Non-empty conditions**: `conditions` must be a non-empty list

### Validation Error Examples

```
❌ Field 'statuss' not found in entity fields   # intentional typo to show suggestion
   💡 Did you mean 'status'? Available fields: customer_id, order_date, status, total

❌ Cannot filter on key attribute 'customer_id' in a Query operation
   💡 For Query, key attributes must be in KeyConditionExpression. For Scan, filtering on key attributes is allowed.

❌ Invalid operator 'equals'
   💡 Valid operators: <, <=, <>, =, >, >=, between, in

❌ Filter expressions are only valid for Query and Scan operations, got 'GetItem'
   💡 Change operation to one of: Query, Scan, or remove filter_expression
```

## 📊 Usage Data

When using `usage_data.json` for realistic sample values, add a `filter_values` section per entity:

```json
{
  "entities": {
    "Order": {
      "sample_data": { ... },
      "access_pattern_data": { ... },
      "update_data": { ... },
      "filter_values": {
        "excluded_status": "CANCELLED",
        "min_total": 25.00,
        "min_fee": 3.00,
        "max_fee": 10.00
      }
    }
  }
}
```

Filter values are used in generated `usage_examples.py` when testing access patterns with filter expressions.

## 🎯 Best Practices

**✅ Do:**
- Use filter expressions for small exclusions (e.g., filtering out cancelled orders)
- Combine with efficient key conditions to minimize data read
- Use `attribute_exists`/`attribute_not_exists` for sparse data patterns
- Design sort keys to handle most filtering via KeyConditionExpression first

**❌ Don't:**
- Use filter expressions as a substitute for proper key design
- Filter on key attributes (use KeyConditionExpression instead)
- Expect filter expressions to reduce read capacity consumption
- Use filter expressions when most items will be filtered out (redesign your keys instead)

## 📚 Related Documentation

- [Range Queries](RANGE_QUERIES.md) - Range conditions on sort keys
- [GSI Support](GSI_SUPPORT.md) - Global Secondary Index support
- [Schema Validation](SCHEMA_VALIDATION.md) - Detailed validation rules
- [Testing Framework](TESTING.md) - Testing your generated code
