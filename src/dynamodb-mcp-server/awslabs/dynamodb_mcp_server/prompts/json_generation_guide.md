# DynamoDB Data Model JSON Generation Guide

## Overview

This guide explains how to generate the `dynamodb_data_model.json` file required for data model validation. This file contains your table definitions, test data, and access pattern implementations in a format that can be automatically validated.

## When to Generate JSON

After completing your DynamoDB data model design (documented in `dynamodb_data_model.md`), you should generate the JSON implementation file. The AI will ask:

**"Would you like me to generate the JSON model and validate your DynamoDB data model? (yes/no)"**

- **If you respond yes:** The AI will generate the JSON file and proceed to validation
- **If you respond no:** The design process stops, and you can review the markdown documentation first

## JSON File Structure

The `dynamodb_data_model.json` file must contain three main sections:

### 1. Tables Section
Defines your DynamoDB tables in boto3 `create_table` format.

### 2. Items Section
Contains test data for validation in boto3 `batch_write_item` format.

### 3. Access Patterns Section
Lists all access patterns with their AWS CLI implementations for testing.

## Generation Workflow

🔴 **CRITICAL**: Generate the JSON in three sequential steps, writing to `dynamodb_data_model.json` after each step. Do NOT generate all sections in a single pass.

1. **Generate `tables`** — Read `dynamodb_data_model.md`, generate only the `"tables"` array, write the file with empty `"items": {}` and `"access_patterns": []`
2. **Generate `items`** — Reference the tables just created, generate the `"items"` section, update the file
3. **Generate `access_patterns`** — Reference both tables and items, generate the `"access_patterns"` section, update the file

All three keys must always be present in the final output, even if empty. Write JSON with 2-space indentation.

## Complete JSON Schema

```json
{
  "tables": [
    {
      "AttributeDefinitions": [
        {"AttributeName": "pk_name", "AttributeType": "S|N|B"},
        {"AttributeName": "sk_name", "AttributeType": "S|N|B"},
        {"AttributeName": "gsi_pk", "AttributeType": "S|N|B"},
        {"AttributeName": "gsi_sk", "AttributeType": "S|N|B"}
      ],
      "TableName": "TableName",
      "KeySchema": [
        {"AttributeName": "pk_name", "KeyType": "HASH"},
        {"AttributeName": "sk_name", "KeyType": "RANGE"}
      ],
      "GlobalSecondaryIndexes": [
        {
          "IndexName": "GSIName",
          "KeySchema": [
            {"AttributeName": "gsi_pk", "KeyType": "HASH"},
            {"AttributeName": "gsi_sk", "KeyType": "RANGE"}
          ],
          "Projection": {
            "ProjectionType": "ALL|KEYS_ONLY|INCLUDE",
            "NonKeyAttributes": ["attr1", "attr2"]  // Only for INCLUDE projection
          }
        }
      ],
      "BillingMode": "PAY_PER_REQUEST"
    }
  ],
  "items": {
    "TableName": [
      {
        "PutRequest": {
          "Item": {
            "pk_name": {"S": "value"},
            "sk_name": {"S": "value"},
            "attribute": {"S|N|BOOL|M|L|SS|NS|BS|NULL": "value"}
          }
        }
      }
    ]
  },
  "access_patterns": [
    {
      "pattern": "1",
      "description": "Pattern description",
      "table": "TableName",
      "index": "GSIName",
      "dynamodb_operation": "Query",
      "implementation": "aws dynamodb query --table-name TableName ..."
    }
  ]
}
```

## Tables Section Rules

🔴 **CRITICAL - CORRECT FORMAT ONLY:**

Generate boto3 `create_table` format with these EXACT field names:
- ✅ `"AttributeDefinitions"` (array of objects with `AttributeName` and `AttributeType`)
- ✅ `"TableName"` (string)
- ✅ `"KeySchema"` (array of objects with `AttributeName` and `KeyType`)
- ✅ `"GlobalSecondaryIndexes"` (array, if GSIs exist)
- ✅ `"BillingMode"` (string)

**❌ NEVER USE THESE INCORRECT FORMATS:**
- ❌ `"table_name"` — WRONG! Use `"TableName"`
- ❌ `"partition_key": {"name": "...", "type": "..."}` — WRONG! Use `"KeySchema"` array
- ❌ `"sort_key": {"name": "...", "type": "..."}` — WRONG! Use `"KeySchema"` array
- ❌ `"gsis"` — WRONG! Use `"GlobalSecondaryIndexes"`
- ❌ `"multi_attribute_keys"` object — WRONG! Use multiple `KeySchema` entries with same `KeyType`

Rules:
- Map attribute types: string→S, number→N, binary→B
- 🔴 **CRITICAL**: `AttributeDefinitions` must contain ONLY attributes used in a KeySchema (table keys AND GSI keys). Including unused attributes violates DynamoDB validation.
- Omit `GlobalSecondaryIndexes` entirely if the table has no GSIs
- For INCLUDE projections, `NonKeyAttributes` must NOT contain key attributes — they are automatically projected

### Multi-Attribute GSI Keys

🔴 **CRITICAL**: Multi-attribute keys are NOT the default. Only use when `dynamodb_data_model.md` explicitly indicates them (e.g., "Sort Key: status, created_at (multi-attribute)").

Multi-attribute keys use multiple KeySchema entries with the same KeyType. This is a native DynamoDB feature — NOT string concatenation.

- ❌ **WRONG — Concatenated String**: `{"AttributeName": "composite_key", "AttributeType": "S"}` with value `"TOURNAMENT#WINTER2024#REGION#NA-EAST"`
- ✅ **CORRECT — Multi-Attribute Key**: Multiple KeySchema entries with same KeyType

```json
{
  "IndexName": "TournamentRegionIndex",
  "KeySchema": [
    {"AttributeName": "tournamentId", "KeyType": "HASH"},
    {"AttributeName": "region", "KeyType": "HASH"},
    {"AttributeName": "round", "KeyType": "RANGE"},
    {"AttributeName": "bracket", "KeyType": "RANGE"}
  ],
  "Projection": {"ProjectionType": "ALL"}
}
```

- Each attribute must also appear in `AttributeDefinitions` with its native type (S, N, or B)
- Each attribute is a separate entry in KeySchema — do NOT concatenate values into a single attribute

## Items Section Rules

Generate boto3 `batch_write_item` format grouped by TableName:

- Each table contains an array of 5-10 `PutRequest` objects with Item data
- Convert values to DynamoDB format: strings→S, numbers→N, booleans→BOOL with `True`/`False` (Python-style capitalization)
- Create one `PutRequest` per data row
- Include ALL item definitions found in the markdown — do not skip any
- Generate realistic test data that demonstrates the table's entity types and access patterns

## Access Patterns Section Rules

Each access pattern entry uses these keys:
- `pattern` (required): Pattern ID (e.g., "1" or "1-2" for ranges)
- `description` (required): Pattern description
- `table`: Table name (required for DynamoDB operations)
- `index`: GSI name (required for GSI operations)
- `dynamodb_operation`: Operation type (required for DynamoDB operations)
- `implementation`: Single AWS CLI command (required for DynamoDB operations)
- `reason`: Why pattern was skipped (for external service patterns)

Valid `dynamodb_operation` values: Query, Scan, GetItem, PutItem, UpdateItem, DeleteItem, BatchGetItem, BatchWriteItem, TransactGetItems, TransactWriteItems

### When to Include Which Fields

- **Pattern uses a DynamoDB operation**: Include `table`, `dynamodb_operation`, `implementation`
- **Pattern queries a GSI**: Also include `index`
- **Pattern uses an external service** (not DynamoDB): Omit `table`/`index`/`dynamodb_operation`/`implementation`, include `reason`
- **Pattern requires multiple DynamoDB operations**: Split into separate entries (e.g., "5a" and "5b"), one operation each
- **Multiple patterns share same description and operation**: Preserve pattern range (e.g., "1-2")
- **Pattern range has different operations**: Split range into separate entries per operation

### Implementation Field Rules

🔴 **CRITICAL — NO COMPOUND COMMANDS:**
- ❌ **NEVER use `&&`, `||`, `;`, or pipes** to chain multiple commands
- ❌ **NEVER combine multiple DynamoDB operations** in a single implementation field
- ✅ **ONE command per access pattern** — if a pattern requires multiple operations, split into separate pattern entries

AWS CLI command requirements:
- Include `--table-name <TableName>` for all operations
- Include both partition and sort keys in `--key` parameters
- **ALWAYS use `--expression-attribute-names`** for all attributes (not just reserved keywords)
- **Use single quotes** around all JSON parameters (--expression-attribute-values, --item, --key, --transact-items, etc.)
- **Use correct AWS CLI boolean syntax**: `--flag` for true, `--no-flag` for false (e.g., `--no-scan-index-forward` NOT `--scan-index-forward false`)
- **Commands must be executable** and syntactically correct with valid JSON syntax

### Query-Specific Rules

🔴 **CRITICAL — Query Filter Expressions**: For Query operations, NEVER use `--filter-expression` on key attributes (partition key, sort key, or any GSI key attributes including multi-attribute key components). Key attributes can ONLY be used in `--key-condition-expression`. Filter expressions can only reference non-key attributes. Note: Scan operations CAN use key attributes in filter expressions.

🔴 **CRITICAL — Handling != Operator with Sparse GSI**: If Implementation Notes contain `!=` or `<>` on a key attribute AND mention "Sparse GSI" (or if GSI documentation mentions "Sparse:" with an attribute name), the sparse GSI already excludes those items at the index level. Generate query with ONLY the partition key (and optionally other sort key attributes for filtering) in key-condition-expression. Do NOT try to implement the != condition in the query — it's handled by the sparse GSI design.

### Multi-Attribute Key Query Rules

🔴 **CRITICAL**: These rules only apply to GSIs that use multi-attribute keys. Standard single-attribute GSIs follow normal query rules.

- **Partition Key**: ALL partition key attributes MUST be specified with equality (`=`). Cannot skip any. Cannot use inequality operators.
- **Sort Key**: Query left-to-right in KeySchema order. Cannot skip attributes (can't query attr1 + attr3 while skipping attr2). Inequality operators (`>`, `>=`, `<`, `<=`, `BETWEEN`, `begins_with()`) must be the LAST condition.

## After JSON Generation

Once the JSON file is generated, the AI will ask:

**"I've generated your `dynamodb_data_model.json` file! Now I can validate your DynamoDB data model. This comprehensive validation will:**

**Environment Setup:**
- Set up DynamoDB Local environment (tries containers first: Docker/Podman/Finch/nerdctl, falls back to Java)

**⚠️ IMPORTANT — Isolated Environment:**
- **Creates a separate DynamoDB Local instance** specifically for validation (container: `dynamodb-local-setup-for-data-model-validation` or Java process: `dynamodb.local.setup.for.data.model.validation`)
- **Does NOT affect your existing DynamoDB Local setup** — uses an isolated environment
- **Cleans up only validation tables** to ensure accurate testing

**Validation Process:**
- Create tables from your data model specification
- Insert test data items into the created tables
- Test all defined access patterns
- Save detailed validation results to `dynamodb_model_validation.json`
- Transform results to markdown format for comprehensive review

**This validation helps ensure your design works as expected and identifies any issues. Would you like me to proceed with the validation?**"

If you respond positively (yes, sure, validate, test, etc.), the AI will immediately call the `dynamodb_data_model_validation` tool.

## Handling Outdated DynamoDB Local

🔴 **CRITICAL — DO NOT AUTO-REMOVE CONTAINERS OR FILES:**

If the validation tool returns an error indicating that the DynamoDB Local container or Java installation is outdated (below minimum version), you MUST:

1. **DO NOT attempt to remove the container or files yourself** — never run any cleanup commands
2. **Display the error message to the user** exactly as provided
3. **Instruct the user to manually run the removal commands** shown in the error message in their own terminal
4. **Wait for the user to confirm** they have removed the outdated installation
5. **Only then** offer to re-run the data model validation tool

## How to Use This Guide

1. **If you haven't started modeling yet**: Call the `dynamodb_data_modeling` tool to begin the design process
2. **If you have a design but no JSON**: Provide your `dynamodb_data_model.md` content to the AI and ask it to generate the JSON following this guide
3. **If you have the JSON**: Proceed directly to calling `dynamodb_data_model_validation` tool
