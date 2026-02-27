# DynamoDB Entity and Repository Code Generator

> **Note**: This tool is a module within the `dynamodb-mcp-server` package. All commands in this documentation should be run from the `src/dynamodb-mcp-server/` directory.

## 🎯 Purpose

This code generation system transforms DynamoDB data model specifications into fully functional, type-safe entities and repositories with clean architecture patterns. The system is designed with a **language-agnostic architecture** and currently supports **Python**, with TypeScript, Java, and other languages planned for future releases.

### 📋 Generation Pipeline

```
dynamodb_data_model.md → schema.json → Templates → Generated Code
```

1. **Source**: `dynamodb_data_model.md` - Contains DynamoDB table design, access patterns, and business requirements
2. **Schema**: `schema.json` - Structured JSON representation with rich field descriptors
3. **Templates**: Jinja2 templates for code generation
4. **Output**: Type-safe entities and repositories with CRUD operations and access pattern stubs

## 🚀 Quick Start

### Prerequisites

This tool is a module within the `dynamodb-mcp-server` package. Navigate to the package root before running commands:

```bash
# Navigate to the dynamodb-mcp-server root directory
cd src/dynamodb-mcp-server
```

**Optional**: For realistic sample data in usage examples, create a `usage_data.json` file alongside your schema. See [docs/USAGE_DATA.md](docs/USAGE_DATA.md) for details.

### Installation

Dependencies are managed by the parent package. Ensure you have all dependencies installed:

```bash
# Install all dependencies including dev tools (from dynamodb-mcp-server root)
uv sync --all-groups

# Or just install main dependencies (ruff linting will be skipped)
uv sync
```

**Note**: The code generator requires `pydantic`, `boto3`, and `jinja2` (included in main dependencies). The `ruff` linter is optional but recommended for code quality checks (included in dev dependencies).

### Basic Usage

```bash
# Generate Python code from schema
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema schema.json

# Generate with usage examples
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema schema.json --generate_sample_usage

# Generate with realistic sample data from usage_data.json
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema schema.json --generate_sample_usage --usage-data-path usage_data.json

# Validate schema only
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema schema.json --validate-only
```

### CLI Options

| Option                    | Description                                  | Default                           |
| ------------------------- | -------------------------------------------- | --------------------------------- |
| `--schema`                | Path to schema JSON file                     | `schema.json`                     |
| `--output`                | Output directory for generated code          | `generated/{language}`            |
| `--language`              | Target programming language                  | `python`                          |
| `--templates-dir`         | Custom Jinja2 templates directory            | `languages/{language}/templates/` |
| `--generate_sample_usage` | Generate usage examples file                 | `False`                           |
| `--usage-data-path`       | Path to usage data JSON for realistic samples| `None` (uses defaults)            |
| `--no-lint`               | Skip running language-specific linter        | `False`                           |
| `--no-fix`                | Skip auto-fixing linting issues              | `False`                           |
| `--validate-only`         | Only validate schema without generating code | `False`                           |

## 🌍 Language Support

| Language       | Status          | File Extension | Linter       | Notes                                        |
| -------------- | --------------- | -------------- | ------------ | -------------------------------------------- |
| **Python**     | ✅ Full Support | `.py`          | Ruff         | Complete implementation with type hints      |
| **TypeScript** | 🚧 Planned      | `.ts`          | ESLint       | Interface-based entities, class repositories |
| **Java**       | 🚧 Planned      | `.java`        | Checkstyle   | One class per file, Maven integration        |
| **C#**         | 🚧 Planned      | `.cs`          | EditorConfig | Namespace organization, NuGet packages       |

## 📊 Schema Structure

### Simple Example (Partition Key Only)

For simple key-value lookups, you can omit the sort key:

```json
{
  "tables": [
    {
      "table_config": {
        "table_name": "Users",
        "partition_key": "user_id"
      },
      "entities": {
        "User": {
          "entity_type": "USER",
          "pk_template": "{user_id}",
          "fields": [
            { "name": "user_id", "type": "string", "required": true },
            { "name": "username", "type": "string", "required": true },
            { "name": "email", "type": "string", "required": true }
          ],
          "access_patterns": [
            {
              "pattern_id": 1,
              "name": "get_user",
              "description": "Get user by ID",
              "operation": "GetItem",
              "parameters": [{ "name": "user_id", "type": "string" }],
              "return_type": "single_entity"
            }
          ]
        }
      }
    }
  ]
}
```

### Composite Key Example (Partition Key + Sort Key)

For hierarchical data or one-to-many relationships:

```json
{
  "tables": [
    {
      "table_config": {
        "table_name": "UserData",
        "partition_key": "pk",
        "sort_key": "sk"
      },
      "entities": {
        "UserProfile": {
          "entity_type": "PROFILE",
          "pk_template": "USER#{user_id}",
          "sk_template": "PROFILE",
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
    }
  ]
}
```

### GSI Example (With Global Secondary Indexes)

GSIs can have sort keys for sorted queries, or be partition-key-only for simple lookups:

```json
{
  "tables": [
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
          "name": "CategoryIndex",
          "partition_key": "category_pk"
        }
      ],
      "entities": {
        "User": {
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
              "name": "CategoryIndex",
              "pk_template": "{category_id}"
            }
          ],
          "fields": [
            { "name": "user_id", "type": "string", "required": true },
            { "name": "status", "type": "string", "required": true },
            { "name": "last_active", "type": "string", "required": true },
            { "name": "category_id", "type": "string", "required": true }
          ],
          "access_patterns": [
            {
              "pattern_id": 1,
              "name": "get_active_users",
              "description": "Get users by status",
              "operation": "Query",
              "index_name": "StatusIndex",
              "parameters": [{ "name": "status", "type": "string" }],
              "return_type": "entity_list"
            },
            {
              "pattern_id": 2,
              "name": "get_recent_active_users",
              "description": "Get recently active users",
              "operation": "Query",
              "index_name": "StatusIndex",
              "range_condition": ">=",
              "parameters": [
                { "name": "status", "type": "string" },
                { "name": "since_date", "type": "string" }
              ],
              "return_type": "entity_list"
            },
            {
              "pattern_id": 3,
              "name": "get_users_by_category",
              "description": "Get all users in a category (partition key only GSI)",
              "operation": "Query",
              "index_name": "CategoryIndex",
              "parameters": [{ "name": "category_id", "type": "string" }],
              "return_type": "entity_list"
            }
          ]
        }
      }
    }
  ]
}
```

### Multi-Attribute Keys Example (Advanced GSI Pattern)

Multi-attribute keys allow GSIs to use up to 4 attributes per key, enabling hierarchical queries without synthetic key concatenation:

```json
{
  "tables": [
    {
      "table_config": {
        "table_name": "Orders",
        "partition_key": "order_id"
      },
      "gsi_list": [
        {
          "name": "StoreActiveDeliveries",
          "partition_key": "store_id",
          "sort_key": ["status", "created_at"],
          "projection": "INCLUDE",
          "included_attributes": ["driver_id"]
        }
      ],
      "entities": {
        "Order": {
          "entity_type": "ORDER",
          "pk_template": "{order_id}",
          "gsi_mappings": [
            {
              "name": "StoreActiveDeliveries",
              "pk_template": "{store_id}",
              "sk_template": ["{status}", "{created_at}"]
            }
          ],
          "fields": [
            { "name": "order_id", "type": "string", "required": true },
            { "name": "store_id", "type": "string", "required": true },
            { "name": "status", "type": "string", "required": true },
            { "name": "created_at", "type": "string", "required": true },
            { "name": "driver_id", "type": "string", "required": true }
          ],
          "access_patterns": [
            {
              "pattern_id": 1,
              "name": "get_store_deliveries",
              "description": "Get all deliveries for a store",
              "operation": "Query",
              "index_name": "StoreActiveDeliveries",
              "parameters": [{ "name": "store_id", "type": "string" }],
              "return_type": "entity_list"
            },
            {
              "pattern_id": 2,
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
  ]
}
```

**Multi-Attribute Key Rules:**
- Partition key: ALL attributes must be specified with equality conditions
- Sort key: Query left-to-right without skipping attributes
- Range conditions: Only on the LAST sort key attribute in your query
- Generated key builders return tuples for multi-attribute keys

### Consistent Read Example

Control read consistency for your access patterns. Strongly consistent reads ensure you get the most up-to-date data, while eventually consistent reads (default) offer better performance and lower cost:

```json
{
  "tables": [
    {
      "table_config": {
        "table_name": "Orders",
        "partition_key": "order_id",
        "sort_key": "sk"
      },
      "gsi_list": [
        {
          "name": "CustomerIndex",
          "partition_key": "customer_id",
          "sort_key": "order_date"
        }
      ],
      "entities": {
        "Order": {
          "entity_type": "ORDER",
          "pk_template": "ORDER#{order_id}",
          "sk_template": "METADATA",
          "gsi_mappings": [
            {
              "name": "CustomerIndex",
              "pk_template": "CUSTOMER#{customer_id}",
              "sk_template": "{order_date}"
            }
          ],
          "fields": [
            { "name": "order_id", "type": "string", "required": true },
            { "name": "customer_id", "type": "string", "required": true },
            { "name": "order_date", "type": "string", "required": true },
            { "name": "total", "type": "decimal", "required": true }
          ],
          "access_patterns": [
            {
              "pattern_id": 1,
              "name": "get_order",
              "description": "Get order with strong consistency",
              "operation": "GetItem",
              "consistent_read": true,
              "parameters": [{ "name": "order_id", "type": "string" }],
              "return_type": "single_entity"
            },
            {
              "pattern_id": 2,
              "name": "query_orders",
              "description": "Query orders (eventually consistent)",
              "operation": "Query",
              "consistent_read": false,
              "parameters": [{ "name": "order_id", "type": "string" }],
              "return_type": "entity_list"
            },
            {
              "pattern_id": 3,
              "name": "get_customer_orders",
              "description": "Get customer orders via GSI (always eventually consistent)",
              "operation": "Query",
              "index_name": "CustomerIndex",
              "parameters": [{ "name": "customer_id", "type": "string" }],
              "return_type": "entity_list"
            }
          ]
        }
      }
    }
  ]
}
```

**Important Notes:**
- `consistent_read` is optional and defaults to `false` (eventually consistent)
- Only applies to read operations: GetItem, Query, Scan, BatchGetItem, TransactGetItems
- **Cannot be `true` for GSI queries** - DynamoDB GSIs only support eventually consistent reads
- Strongly consistent reads (`true`) consume 2x the read capacity units compared to eventually consistent reads
- The validator will reject schemas that specify `consistent_read: true` for GSI queries

### Key Features

- **Multi-Table Support**: Define multiple DynamoDB tables in a single schema
- **Cross-Table Transaction Support**: Atomic operations across multiple tables using TransactWriteItems and TransactGetItems ([details](docs/TRANSACTIONS.md))
- **Flexible Key Design**: Support for both composite keys (PK+SK) and partition-key-only tables
- **Template-Based Keys**: Flexible PK/SK generation with parameter substitution
- **Multi-Attribute Keys**: GSIs can use up to 4 attributes per partition key and 4 per sort key
  - Follows AWS DynamoDB multi-attribute key specifications
  - Automatic tuple-based key builders for multi-attribute keys
  - Correct KeyConditionExpression generation with left-to-right SK queries
  - Validation for 1-4 attribute limit per key
- **Numeric Key Support**: Full support for `integer` and `decimal` partition/sort keys
  - Numeric keys return raw values (not f-strings) for correct DynamoDB sorting
  - Repository methods use correct parameter types (`int`, `Decimal`)
  - Works on both main table and GSI keys
- **Full GSI Support**: Global Secondary Indexes with automatic key builders and query helpers ([details](docs/GSI_SUPPORT.md))
  - Supports GSIs with or without sort keys
  - Supports single-attribute and multi-attribute keys
  - Automatic generation of appropriate key builder methods
- **Consistent Read Support**: Optional `consistent_read` parameter for read operations
  - Control read consistency at the access pattern level
  - Supports `true` (strongly consistent) or `false` (eventually consistent, default)
  - Automatically validated - GSI queries cannot use strongly consistent reads
  - Applies to GetItem, Query, Scan, BatchGetItem, and TransactGetItems operations
  - **Projection control**: ALL, KEYS_ONLY, INCLUDE projections with smart return types
- **Access Pattern Stubs**: Generate method signatures for complex queries
- **Range Query Support**: Full support for range conditions on both main table and GSI sort keys ([details](docs/RANGE_QUERIES.md))
  - Operators: `begins_with`, `between`, `>=`, `<=`, `>`, `<`
  - Works on main table sort keys and GSI sort keys
  - Supports multi-attribute sort keys with range conditions on last attribute
  - Automatic validation and helpful error messages
- **Filter Expression Support**: Server-side filtering on non-key attributes for Query and Scan operations ([details](docs/FILTER_EXPRESSIONS.md))
  - Comparison operators: `=`, `<>`, `<`, `<=`, `>`, `>=`
  - Range and set operators: `between`, `in`
  - Functions: `contains`, `begins_with`, `attribute_exists`, `attribute_not_exists`, `size`
  - Logical operators: `AND`, `OR` for combining multiple conditions
  - Comprehensive validation with helpful error messages
- **Type Safety**: Language-specific type mappings and validation

## 🔑 GSI (Global Secondary Index) Support

The generator provides full GSI support with automatic generation of:

- GSI key builder methods (class and instance methods)
- GSI prefix helper methods for range queries
- Repository methods with complete GSI query examples
- Comprehensive GSI validation

**For complete GSI documentation, see [GSI Support Guide](docs/GSI_SUPPORT.md)**

## 🏗️ Generated Code Structure

```
generated/
├── python/                        # Python-specific generated code
│   ├── entities.py                # Entity classes with GSI key builders and prefix helpers
│   ├── repositories.py            # Repository classes with CRUD + GSI access patterns
│   ├── base_repository.py         # Base repository class
│   ├── transaction_service.py     # Cross-table transaction service (when cross_table_access_patterns exist)
│   ├── ruff.toml                  # Linting configuration
│   ├── access_pattern_mapping.json # Access pattern mapping including GSI queries
│   └── usage_examples.py          # Interactive examples with GSI usage (optional, uses realistic data from usage_data.json if provided)
├── typescript/                    # Future: TypeScript-specific generated code
└── java/                          # Future: Java-specific generated code
```

**Note**: When `--usage-data-path` is provided, `usage_examples.py` will use realistic sample data from your `usage_data.json` file instead of generic placeholder values.

## 📝 Basic Usage Example

```python
from generated.entities import UserProfile
from generated.repositories import UserProfileRepository

# Create repository
user_repo = UserProfileRepository(table_name="UserData")

# Create entity
user = UserProfile(
    user_id="user123",
    username="john_doe",
    email="john@example.com"
)

# Repository operations
created_user = user_repo.create_user_profile(user)
retrieved_user = user_repo.get_user_profile("user123")
updated_user = user_repo.update_user_profile(user)
deleted = user_repo.delete_user_profile("user123")
```

## 🔧 Template System

Templates use `{field_name}` syntax to reference entity fields:

```json
{
  "pk_template": "USER#{user_id}",
  "sk_template": "PROFILE",
  "gsi_mappings": [
    {
      "name": "StatusIndex",
      "pk_template": "STATUS#{status}",
      "sk_template": "{last_active}"
    }
  ]
}
```

**For advanced template patterns, see [GSI Support Guide](docs/GSI_SUPPORT.md)**

## 🎨 Customization

### Custom Templates

```bash
# Use custom templates
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema schema.json --templates-dir custom/templates/
```

### Adding New Entities

1. **Update Schema**: Add entity definition to `schema.json`
2. **Regenerate**: Run `uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema schema.json`
3. **Implement**: Fill in access pattern method bodies

## 🧪 Testing

All tests should be run from the `dynamodb-mcp-server` root directory:

```bash
# Run all tests
uv run pytest tests/repo_generation_tool/ -v

# Run unit tests only
uv run pytest tests/repo_generation_tool/ -m unit -v

# Validate snapshots
uv run python tests/repo_generation_tool/scripts/manage_snapshots.py test
```

## 📚 Documentation

For comprehensive information, see the detailed documentation:

- **[Cross-Table Transactions](docs/TRANSACTIONS.md)** - Complete guide to atomic transaction support across multiple tables
- **[Range Queries](docs/RANGE_QUERIES.md)** - Complete guide to range query support for main table and GSI sort keys
- **[Filter Expressions](docs/FILTER_EXPRESSIONS.md)** - Complete guide to server-side filter expression support
- **[GSI Support](docs/GSI_SUPPORT.md)** - Complete guide to Global Secondary Index support
- **[Schema Validation](docs/SCHEMA_VALIDATION.md)** - Detailed validation rules, error handling, and schema structure
- **[Testing Framework](docs/TESTING.md)** - Complete testing guide with unit, integration, and snapshot tests
- **[Language Configuration](docs/LANGUAGE_CONFIGURATION.md)** - Language system architecture and configuration
- **[Adding New Languages](docs/ADDING_NEW_LANGUAGES.md)** - Step-by-step guide for implementing new language support
- **[Advanced Usage](docs/ADVANCED_USAGE.md)** - Complex examples, multi-tenant patterns, and troubleshooting

## 🔍 Troubleshooting

### Common Issues

1. **Schema Validation Errors**: Check validation output for specific field issues and suggestions
2. **Invalid Enum Values**: Use suggested values from validation error messages
3. **Import Errors**: Ensure generated code directory is in Python path
4. **Template Errors**: Check template syntax and variable names

For detailed troubleshooting, see [Advanced Usage](docs/ADVANCED_USAGE.md).

## 🏗️ Architecture

### Core Components

| Module         | Purpose                                                                              |
| -------------- | ------------------------------------------------------------------------------------ |
| **Core**       | Schema handling, validation, type mappings, GSI validation, and key template parsing |
| **Generators** | Template-based code generation with access pattern mapping and GSI support           |
| **Output**     | Language-agnostic file writing and manifest management                               |
| **Languages**  | Language-specific templates, configurations, and support files                       |

### Architecture Philosophy

- **Language-Agnostic Design**: Modular architecture supports multiple programming languages
- **Template-Driven Generation**: Powerful Jinja2 templating with language-specific customization
- **Configuration-Based**: Clean separation of data models from DynamoDB key generation logic
- **GSI-First Design**: Full support for Global Secondary Indexes with automatic key builders and query helpers
- **Multi-Tenant Ready**: Support for complex key patterns and hierarchical data

---

**Happy Coding!** 🎉

For questions or contributions, please refer to the detailed documentation or create an issue in the repository.
