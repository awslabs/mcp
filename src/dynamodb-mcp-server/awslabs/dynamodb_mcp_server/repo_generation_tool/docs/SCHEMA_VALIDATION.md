# Schema Validation

The generator includes comprehensive schema validation that runs automatically before code generation.

## Validation Features

### Comprehensive Validation

The generator includes robust schema validation with clear error reporting:

#### Structure Validation

- **Required Sections**: Ensures `table_config` and `entities` sections exist
- **Required Fields**: Validates all required fields are present in each section
- **Data Types**: Checks that fields have correct data types (string, integer, boolean, array)
- **Non-Empty Arrays**: Ensures arrays like `fields` and `access_patterns` are not empty

#### Enum Validation

- **Field Types**: Validates against `FieldType` enum with suggestions for typos
- **Return Types**: Validates against `ReturnType` enum
- **Operations**: Validates against `DynamoDBOperation` enum
- **Parameter Types**: Validates against `ParameterType` enum

#### Business Logic Validation

- **Unique Pattern IDs**: Ensures `pattern_id` is unique across all entities
- **Unique Names**: Validates pattern names are unique within each entity
- **Unique Parameters**: Ensures parameter names are unique within each pattern
- **Unique Fields**: Validates field names are unique within each entity
- **Entity References**: Checks that `entity_type` references in parameters exist
- **Array Item Types**: Ensures array fields specify `item_type`
- **Entity Parameters**: Validates entity parameters have `entity_type`

#### Error Reporting

Clear, actionable error messages with suggestions:

```bash
❌ Schema validation failed:
  • entities.UserProfile.access_patterns[0].return_type: Invalid return_type value 'single_entitty'
    💡 Did you mean 'single_entity'? Valid options: single_entity, entity_list, success_flag, mixed_data, void

  • entities.Post.access_patterns[2].pattern_id: Duplicate pattern_id '3'
    💡 Pattern IDs must be unique across all entities

  • entities.Comment.fields[1].type: Invalid type value 'strng'
    💡 Did you mean 'string'? Valid options: string, integer, number, boolean, array, object, timestamp, uuid, email
```

## Schema Structure

### Validated Schema Structure

The schema is validated against strict rules with helpful error messages:

```json
{
  "tables": [
    {
      "table_config": {
        "table_name": "string",      // Required
        "partition_key": "string",   // Required
        "sort_key": "string",        // Optional: Omit for partition-key-only tables
        "gsi_list": [                // Optional: GSI definitions
          {
            "name": "string",        // Required: GSI name
            "partition_key": "string",  // Required: GSI PK attribute
            "sort_key": "string"     // Optional: GSI SK attribute (omit for PK-only GSIs)
          }
        ]
      },
      "entities": {
        "EntityName": {
          "entity_type": "ENTITY_PREFIX",                    // Required
          "pk_template": "{field}|TENANT#{tenant_id}#USER#{user_id}",  // Required
          "sk_template": "STATIC_VALUE|PREFIX#{param}",      // Optional: Omit for PK-only entities
          "gsi_mappings": [                                  // Optional: GSI key templates
            {
              "name": "string",                              // Required: Must match gsi_list
              "pk_template": "PREFIX#{field}",               // Required
              "sk_template": "{field}|STATIC"                // Optional: Omit for PK-only GSIs
            }
          ],
          "fields": [...],                                   // Required, non-empty
          "access_patterns": [...]                           // Optional
        }
      }
    }
  ]
}
```

### Validated Enums

All schema values are validated against predefined enums:

#### Field Types

- `"string"`, `"integer"`, `"float"`, `"boolean"`
- `"array"`, `"object"`, `"uuid"`

#### Return Types

- `"single_entity"` - Returns `T | None`
- `"entity_list"` - Returns `list[T]` (homogeneous results)
- `"success_flag"` - Returns `bool`
- `"mixed_data"` - Returns `list[dict[str, Any]]` (item collections with multiple entity types)
- `"void"` - Returns `None`

#### DynamoDB Operations

- `"GetItem"`, `"PutItem"`, `"DeleteItem"`
- `"Query"`, `"Scan"`, `"UpdateItem"`
- `"BatchGetItem"`, `"BatchWriteItem"`

#### Parameter Types

- `"string"`, `"integer"`, `"boolean"`
- `"entity"` - Must include `entity_type` field

## Range Query Validation

The generator validates range queries for both main table sort keys and GSI sort keys:

### Main Table Range Queries

Range queries on the main table's sort key are validated for:

- **Range Condition Syntax**: Validates against supported operators (`begins_with`, `between`, `>`, `<`, `>=`, `<=`)
- **Parameter Count**: Ensures correct number of parameters for each range condition
- **Operation Compatibility**: Range conditions only work with `Query` operations

**Example:**

```json
{
  "access_patterns": [
    {
      "pattern_id": 1,
      "name": "get_user_posts_after_date",
      "description": "Get posts after a specific date",
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

**Validation Rules:**
- No `index_name` field = main table query
- `operation` must be `"Query"` (not `GetItem`, `PutItem`, etc.)
- Parameter count must match range condition:
  - `between`: 3 parameters (partition key + 2 range values)
  - All others: 2 parameters (partition key + 1 range value)

**For complete range query documentation, see [Range Queries](RANGE_QUERIES.md)**

## GSI Validation

The generator includes comprehensive validation for Global Secondary Indexes (GSIs):

### GSI Structure Validation

- **GSI List**: Validates `gsi_list` array in `table_config`
- **GSI Names**: Ensures GSI names are unique within a table
- **GSI Keys**: Validates partition_key and sort_key are specified for each GSI
- **GSI Mappings**: Validates `gsi_mappings` array in entity definitions

### GSI Name Matching

The validator ensures consistency between table GSI definitions and entity GSI mappings:

```json
{
  "table_config": {
    "gsi_list": [
      {
        "name": "StatusIndex", // Must match entity gsi_mappings
        "partition_key": "status_pk",
        "sort_key": "last_active_sk"
      }
    ]
  },
  "entities": {
    "User": {
      "gsi_mappings": [
        {
          "name": "StatusIndex", // Must match gsi_list name
          "pk_template": "STATUS#{status}",
          "sk_template": "{last_active}"
        }
      ]
    }
  }
}
```

**Validation Rules:**

- GSI names in `gsi_mappings` must exist in table's `gsi_list`
- Warns about unused GSIs defined in `gsi_list` but not used in any entity
- Provides clear error messages for mismatched GSI names

### GSI Template Validation

GSI templates are validated using the same rules as main table templates:

- **Template Syntax**: Validates `{field_name}` syntax
- **Field References**: All fields referenced in templates must exist in entity
- **Parameter Extraction**: Automatically extracts and validates parameters
- **Static Text**: Validates static prefixes and separators

**Example Validation:**

```json
{
  "gsi_mappings": [
    {
      "name": "LocationIndex",
      "pk_template": "COUNTRY#{country}", // ✅ 'country' must be in fields
      "sk_template": "CITY#{city}" // ✅ 'city' must be in fields
    }
  ],
  "fields": [
    { "name": "country", "type": "string", "required": true },
    { "name": "city", "type": "string", "required": true }
  ]
}
```

### GSI Access Pattern Validation

Access patterns that use GSIs are validated for:

- **Index Name**: `index_name` must reference an existing GSI
- **Range Conditions**: Validates range_condition values
- **Parameter Count**: Ensures correct number of parameters for range conditions

**Supported Range Conditions:**

- `"begins_with"` - Requires 1 range parameter
- `"between"` - Requires 2 range parameters
- `">="`, `"<="`, `">"`, `"<"` - Requires 1 range parameter

**Example Validation:**

```json
{
  "pattern_id": 3,
  "name": "get_recent_active_users",
  "operation": "Query",
  "index_name": "StatusIndex", // ✅ Must exist in gsi_list
  "range_condition": ">=", // ✅ Must be valid operator
  "parameters": [
    { "name": "status", "type": "string" },
    { "name": "since_date", "type": "string" } // ✅ Correct count for ">="
  ],
  "return_type": "entity_list"
}
```

### GSI Validation Error Examples

**Missing GSI Definition:**

```bash
❌ Schema validation failed:
  • entities.User.gsi_mappings[0].name: GSI 'StatusIdx' not found in table gsi_list
    💡 Available GSIs: StatusIndex, LocationIndex
    💡 Did you mean 'StatusIndex'?
```

**Invalid Field Reference:**

```bash
❌ Schema validation failed:
  • entities.User.gsi_mappings[0].pk_template: Field 'user_status' not found in entity fields
    💡 Template references field 'user_status' but entity only has: user_id, status, email
    💡 Did you mean 'status'?
```

**Invalid Range Condition:**

```bash
❌ Schema validation failed:
  • entities.User.access_patterns[2].range_condition: Invalid range_condition 'contains'
    💡 Valid options: begins_with, between, >=, <=, >, <
```

**Incorrect Parameter Count:**

```bash
❌ Schema validation failed:
  • entities.User.access_patterns[3]: Range condition 'between' requires 2 range parameters
    💡 Found 1 parameter(s) but expected 2 for 'between' condition
```

### GSI Validation Best Practices

1. **Define GSIs First**: Add GSIs to `gsi_list` before referencing in entities
2. **Use Consistent Names**: Keep GSI names consistent between table and entities
3. **Validate Early**: Use `--validate-only` flag during schema development
4. **Check Field References**: Ensure all template fields exist in entity
5. **Test Range Conditions**: Verify parameter counts match range condition requirements

**For complete GSI documentation, see [GSI Support Guide](GSI_SUPPORT.md)**

## Field Definition

### Field Definition (Validated)

```json
{
  "name": "user_id", // Required: string
  "type": "uuid", // Required: must be valid FieldType enum
  "required": true, // Required: boolean
  "item_type": "string" // Required when type is "array"
}
```

**Validated Field Types**:

- `"string"` - String attributes (S) → `str` (use for emails, names, etc.)
- `"integer"` - Whole number attributes (N) → `int` (use for timestamps, counts, IDs, etc.)
- `"float"` - Decimal number attributes (N) → `float` (use for prices, percentages, measurements, etc.)
- `"boolean"` - Boolean attributes (BOOL) → `bool`
- `"array"` - List/Set attributes (L/SS/NS) → `list[item_type]`
- `"object"` - Map attributes (M) → `dict[str, Any]`
- `"uuid"` - UUID attributes (S) → `str` (Python/TypeScript), `Guid` (C#), `UUID` (Java)

## Access Pattern Definition

### Access Pattern Definition (Validated)

```json
{
  "pattern_id": 1, // Required: integer, unique across all entities
  "name": "get_user_profile", // Required: string, unique within entity
  "description": "User login/authentication - get user profile by user_id", // Required: string
  "operation": "GetItem", // Required: valid DynamoDBOperation enum
  "parameters": [
    // Optional: array of parameter objects
    {
      "name": "user_id", // Required: string, unique within pattern
      "type": "string" // Required: valid ParameterType enum
    },
    {
      "name": "user", // Entity parameter example
      "type": "entity", // Required: "entity" type
      "entity_type": "UserProfile" // Required when type is "entity"
    }
  ],
  "return_type": "single_entity" // Required: valid ReturnType enum
}
```

## Validation Rules

The validator enforces these business rules:

- **Unique IDs**: `pattern_id` must be unique across all entities
- **Unique Names**: Pattern names must be unique within each entity
- **Parameter Names**: Parameter names must be unique within each pattern
- **Field Names**: Field names must be unique within each entity
- **Entity References**: `entity_type` in parameters must reference existing entities
- **Required Fields**: All required fields must be present
- **Data Types**: All fields must have correct data types (string, integer, boolean, array)
- **Enum Values**: All enum fields must use valid enum values with helpful suggestions for typos

## Validate-Only Mode

For quick schema validation without code generation, use the `--validate-only` flag:

```bash
# Quick validation for development (from dynamodb-mcp-server root)
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema schema.json --validate-only

# Perfect for CI/CD pipelines
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema schemas/production.json --validate-only

# Batch validation of multiple schemas
for schema in schemas/*.json; do
  uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema "$schema" --validate-only
done
```

**Use Cases:**

- **Development**: Quick feedback while designing schemas
- **CI/CD**: Validate schemas in automated pipelines
- **Code Reviews**: Ensure schema changes are valid before merging
- **Batch Processing**: Validate multiple schemas quickly

## Cross-Table Entity References

The schema format supports limited cross-table entity references in access patterns:

```json
{
  "pattern_id": 4,
  "name": "create_post_with_user",
  "description": "Create post with user reference",
  "operation": "PutItem",
  "parameters": [
    { "name": "post", "type": "entity", "entity_type": "Post" },
    { "name": "user", "type": "entity", "entity_type": "User" }
  ],
  "return_type": "single_entity"
}
```

**Cross-Table Reference Limitations:**

- Cross-table entity references are allowed in access pattern parameters
- Entity validation ensures referenced entities exist somewhere in the schema
- Code generation handles cross-table references appropriately
- Consider the operational implications of cross-table operations in your application design
