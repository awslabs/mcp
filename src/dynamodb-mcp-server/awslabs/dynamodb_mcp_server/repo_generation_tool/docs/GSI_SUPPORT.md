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

### Multi-Attribute Keys (Advanced)

GSIs support multi-attribute keys with up to 4 attributes per partition key and 4 per sort key. This eliminates the need for synthetic key concatenation:

```json
{
  "gsi_list": [
    {
      "name": "StoreActiveDeliveries",
      "partition_key": "store_id",
      "sort_key": ["status", "created_at"],
      "projection": "INCLUDE",
      "included_attributes": ["driver_id"]
    },
    {
      "name": "TournamentRegionIndex",
      "partition_key": ["tournament_id", "region"],
      "sort_key": ["round", "bracket", "match_id"],
      "projection": "ALL"
    }
  ]
}
```

**Multi-Attribute Key Rules:**
- Use arrays for multi-attribute keys: `["attr1", "attr2"]`
- Partition key: 1-4 attributes (all must be queried with equality)
- Sort key: 1-4 attributes (query left-to-right without skipping)
- Range conditions: Only on the LAST sort key attribute
- Backward compatible: Single-attribute keys use string format

**Entity Mappings for Multi-Attribute Keys:**

```json
{
  "gsi_mappings": [
    {
      "name": "StoreActiveDeliveries",
      "pk_template": "{store_id}",
      "sk_template": ["{status}", "{created_at}"]
    },
    {
      "name": "TournamentRegionIndex",
      "pk_template": ["{tournament_id}", "{region}"],
      "sk_template": ["{round}", "{bracket}", "{match_id}"]
    }
  ]
}
```

**Generated Key Builders:**

Multi-attribute key builders return tuples:

```python
# Single-attribute (returns KeyType)
gsi_pk = Order.build_gsi_pk_for_lookup_storeindex(store_id)

# Multi-attribute (returns tuple)
gsi_sk_tuple = Order.build_gsi_sk_for_lookup_storeindex(status, created_at)
# Returns: (f"{status}", f"{created_at}")
```

**Query Patterns:**

```python
# Query with multi-attribute sort key
query_parameters = {
    'IndexName': 'StoreActiveDeliveries',
    'KeyConditionExpression': (
        Key('store_id').eq(gsi_pk) &
        Key('status').eq(status) &              # First SK attribute (equality)
        Key('created_at').begins_with(prefix)   # Second SK attribute (range - must be last)
    )
}
```

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

## 🎨 GSI Projection Types

DynamoDB GSIs support three projection types that control which attributes are copied to the index. This affects both storage costs and query capabilities.

### Projection Types Overview

| Projection | Attributes Copied | Return Type | Use Case |
|------------|------------------|-------------|----------|
| `ALL` | All attributes | `list[Entity]` | Need full entity data from queries |
| `KEYS_ONLY` | Only key attributes | `list[dict[str, Any]]` | Identify items, fetch full data separately |
| `INCLUDE` | Keys + specified attributes | `list[Entity]` or `list[dict[str, Any]]`* | Need specific attribute subset |

\* **Smart Detection:** Returns `list[Entity]` when all non-projected fields are optional, otherwise `list[dict[str, Any]]`

### Schema Configuration

```json
{
  "gsi_list": [
    {
      "name": "StatusIndex",
      "partition_key": "status_pk",
      "sort_key": "last_active_sk",
      "projection": "ALL"
    },
    {
      "name": "CategoryIndex",
      "partition_key": "category_pk",
      "projection": "KEYS_ONLY"
    },
    {
      "name": "BrandIndex",
      "partition_key": "brand_pk",
      "projection": "INCLUDE",
      "included_attributes": ["user_id", "target_name", "created_at"]
    }
  ]
}
```

### Generated Code Examples

**ALL Projection (default):**

```python
def get_deals_by_brand(self, brand_id: str) -> tuple[list[Deal], dict | None]:
    """Get all deals for a brand

    Projection: ALL
    All entity attributes are available.
    """
    # Returns full Deal entities
    pass
```

**KEYS_ONLY Projection:**

```python
def get_brand_watchers(self, brand_id: str) -> tuple[list[dict[str, Any]], dict | None]:
    """Get all users watching a specific brand

    Projection: KEYS_ONLY
    Returns dict with keys: brand_id, user_id, user_id (table PK), watch_key (table SK)

    Note: Returns dict because only key attributes are projected.
    """
    # Returns dicts with key attributes only
    pass
```

**INCLUDE Projection (Safe - Returns Entity):**

```python
def get_watches_by_type(self, watch_type: str) -> tuple[list[UserWatch], dict | None]:
    """Get watches by type

    Projection: INCLUDE
    Projected Attributes: user_id, watch_key, created_at

    Returns UserWatch entities. Non-projected optional fields will be None.
    """
    # Returns full UserWatch entities (non-projected fields are optional)
    pass
```

**INCLUDE Projection (Unsafe - Returns dict):**

```python
def get_category_watchers(self, category_id: str) -> tuple[list[dict[str, Any]], dict | None]:
    """Get all users watching a specific category

    Projection: INCLUDE
    Projected Attributes: user_id, target_name, created_at

    Returns dict because required field 'watch_type' is not in projection.
    Use dict keys to access values: result[0]['user_id']

    To return typed UserWatch entities, either:
      1. Add 'watch_type' to included_attributes
      2. Make 'watch_type' optional (required: false)
    """
    # Returns dicts because has required fields not projected
    pass
```

### Choosing the Right Projection

**Use ALL when:**
- You always need full entity data from GSI queries
- Storage cost is not a primary concern
- Simplicity is preferred over optimization

**Use KEYS_ONLY when:**
- You need to identify items but will fetch full data separately
- Minimizing GSI storage cost is important
- Query results are used for filtering before fetching full items

**Use INCLUDE when:**
- You need specific attributes for most queries
- Want to avoid fetching full items for common access patterns
- Balancing storage cost with query efficiency
- **Tip:** Make non-projected fields optional to get typed Entity returns

### Cost Implications

- **KEYS_ONLY**: Lowest storage cost (only 4 key attributes)
- **INCLUDE**: Medium storage cost (keys + selected attributes)
- **ALL**: Highest storage cost (all attributes)

Storage costs are per item per GSI, so projection choice can significantly impact costs for large tables.

### Working with Partial Data

When using KEYS_ONLY or INCLUDE projections that return dicts:

```python
# Query with KEYS_ONLY or unsafe INCLUDE
watchers = repo.get_brand_watchers("nike")  # Returns tuple[list[dict[str, Any]], dict | None]
items, next_page = watchers

# Access data using dict keys
for item in items:
    user_id = item['user_id']
    watch_key = item['watch_key']

    # If you need full entity data, fetch separately
    full_watch = repo.get_user_watch(user_id, watch_key)
```

**Why dict instead of Entity?**
- KEYS_ONLY: Only 4 key attributes returned (minimal data)
- INCLUDE (unsafe): Missing required fields would cause Pydantic validation errors
- Dict clearly signals partial data to developers

## 🔑 Generated GSI Methods

For each GSI mapping, the generator creates methods based on whether the GSI has a sort key:

### Partition-Key-Only GSIs

For GSIs without sort keys, only partition key methods are generated:

```python
@classmethod
def build_gsi_pk_for_lookup_categoryindex(cls, category_id) -> KeyType:
    """Build GSI partition key for CategoryIndex lookup operations"""
    return f"{category_id}"

def build_gsi_pk_categoryindex(self) -> KeyType:
    """Build GSI partition key for CategoryIndex from entity instance"""
    return f"{self.category_id}"

@classmethod
def get_gsi_pk_prefix_categoryindex(cls) -> str:
    """Get GSI partition key prefix for CategoryIndex query operations"""
    return ""
```

**Note:** `KeyType = str | int | Decimal` supports both string and numeric key values.

### GSIs with Sort Keys

For GSIs with sort keys, the generator creates three types of methods:

### 1. Class Methods (for lookups)

Used when building queries with specific parameter values:

```python
@classmethod
def build_gsi_pk_for_lookup_statusindex(cls, status) -> KeyType:
    """Build GSI partition key for StatusIndex lookup operations"""
    return f"STATUS#{status}"

@classmethod
def build_gsi_sk_for_lookup_statusindex(cls, last_active) -> KeyType:
    """Build GSI sort key for StatusIndex lookup operations"""
    return f"{last_active}"
```

### 2. Instance Methods (for entity instances)

Used when an entity instance needs to generate its GSI keys:

```python
def build_gsi_pk_statusindex(self) -> KeyType:
    """Build GSI partition key for StatusIndex from entity instance"""
    return f"STATUS#{self.status}"

def build_gsi_sk_statusindex(self) -> KeyType:
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

## 🔢 Numeric GSI Keys

GSI partition and sort keys can be numeric types (`integer` or `decimal`). When a GSI key template is a pure field reference like `{score}` and the field is numeric, the generator returns the raw numeric value instead of an f-string.

### Numeric GSI Sort Key Example

Schema definition:
```json
{
  "gsi_list": [
    {
      "name": "PlayerScoresIndex",
      "partition_key": "player_id",
      "sort_key": "score"
    }
  ],
  "entities": {
    "LeaderboardEntry": {
      "fields": [
        { "name": "player_id", "type": "string", "required": true },
        { "name": "score", "type": "integer", "required": true }
      ],
      "gsi_mappings": [
        {
          "name": "PlayerScoresIndex",
          "pk_template": "{player_id}",
          "sk_template": "{score}"
        }
      ]
    }
  }
}
```

Generated code for numeric GSI sort key:
```python
@classmethod
def build_gsi_sk_for_lookup_playerscoresindex(cls, score) -> KeyType:
    """Build GSI sort key for PlayerScoresIndex lookup operations"""
    return score  # Returns raw int, not f-string

def build_gsi_sk_playerscoresindex(self) -> KeyType:
    """Build GSI sort key for PlayerScoresIndex from entity instance"""
    return self.score  # Returns raw int
```

### Decimal GSI Sort Key Example

For `decimal` fields (e.g., prices, percentages):
```python
@classmethod
def build_gsi_sk_for_lookup_discountindex(cls, discount_percentage) -> KeyType:
    """Build GSI sort key for DiscountIndex lookup operations"""
    return discount_percentage  # Returns raw Decimal
```

### Benefits of Numeric GSI Keys

- **Correct sorting**: DynamoDB sorts numeric keys numerically (1, 2, 10, 100) rather than lexicographically ("1", "10", "100", "2")
- **Range queries**: Numeric comparisons work correctly with `>=`, `<=`, `between`, etc.
- **Type safety**: Generated repository methods use correct parameter types (`int` or `Decimal`)

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

## 🌟 Sparse GSIs

Sparse GSIs are a powerful DynamoDB pattern where only items with the GSI key attributes appear in the index.

### How Sparse GSIs Work

The generated code uses `model_dump(exclude_none=True)` when writing to DynamoDB, which means:
- Fields with `None` values are not written to DynamoDB
- Items without GSI key attributes don't appear in the GSI
- This happens automatically - no special code needed

### Schema Configuration

Make GSI key fields optional to enable sparse behavior:

```json
{
  "entities": {
    "UserWatch": {
      "fields": [
        { "name": "user_id", "type": "string", "required": true },
        { "name": "watch_key", "type": "string", "required": true },
        { "name": "brand_id", "type": "string", "required": false }  // Optional = sparse
      ],
      "gsi_mappings": [
        {
          "name": "WatchesByBrand",
          "pk_template": "{brand_id}",
          "sk_template": "{user_id}"
        }
      ]
    }
  }
}
```

### Example Usage

```python
# Create watch without brand - NOT indexed in WatchesByBrand GSI
watch1 = UserWatch(user_id="user123", watch_key="watch1", brand_id=None)
repo.create(watch1)  # Item stored, but not in WatchesByBrand GSI

# Create watch with brand - IS indexed in WatchesByBrand GSI
watch2 = UserWatch(user_id="user123", watch_key="watch2", brand_id="nike")
repo.create(watch2)  # Item stored and indexed in WatchesByBrand GSI

# Query by brand - only returns watch2
nike_watchers = repo.get_brand_watchers("nike")  # Returns [watch2]
```

### Combining Sparse GSIs with Projections

Sparse behavior works with all projection types:

```json
{
  "gsi_list": [
    {
      "name": "WatchesByBrand",
      "partition_key": "brand_id",
      "sort_key": "user_id",
      "projection": "KEYS_ONLY"  // Sparse + KEYS_ONLY
    }
  ]
}
```

**Benefits:**
- **Sparse**: Only items with `brand_id` are indexed
- **KEYS_ONLY**: Minimal storage per indexed item
- **Combined**: Maximum cost optimization

### Use Cases

1. **Conditional Indexing**: Only index items that meet certain criteria
2. **Cost Optimization**: Reduce GSI storage for large tables
3. **Filtering**: Query only items with specific attributes
4. **Multi-Tenant**: Index only items for active tenants

### Best Practices

**✅ Do:**
- Use sparse GSIs for optional attributes
- Mark GSI key fields as `required: false`
- Combine with KEYS_ONLY projection for maximum savings
- Document sparse behavior in access pattern descriptions

**❌ Don't:**
- Make GSI key fields required if you want sparse behavior
- Assume all items appear in sparse GSIs
- Forget to handle empty query results

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
