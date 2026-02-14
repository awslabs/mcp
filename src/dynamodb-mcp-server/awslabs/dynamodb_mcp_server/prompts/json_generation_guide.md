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

## Complete JSON Schema

```json
{
  "tables": [
    {
      "AttributeDefinitions": [
        // Base table key attributes
        {"AttributeName": "partition_key_name", "AttributeType": "S|N|B"},
        {"AttributeName": "sort_key_name", "AttributeType": "S|N|B"},

        // Single-attribute GSI key attributes
        {"AttributeName": "gsi_partition_key", "AttributeType": "S|N|B"},
        {"AttributeName": "gsi_sort_key", "AttributeType": "S|N|B"},

        // Multi-attribute GSI key attributes (EACH attribute must be defined)
        {"AttributeName": "gsi_pk_attr1", "AttributeType": "S|N|B"},
        {"AttributeName": "gsi_pk_attr2", "AttributeType": "S|N|B"},
        {"AttributeName": "gsi_pk_attr3", "AttributeType": "S|N|B"},
        {"AttributeName": "gsi_pk_attr4", "AttributeType": "S|N|B"},
        {"AttributeName": "gsi_sk_attr1", "AttributeType": "S|N|B"},
        {"AttributeName": "gsi_sk_attr2", "AttributeType": "S|N|B"},
        {"AttributeName": "gsi_sk_attr3", "AttributeType": "S|N|B"},
        {"AttributeName": "gsi_sk_attr4", "AttributeType": "S|N|B"}
      ],
      "TableName": "TableName",
      "KeySchema": [
        {"AttributeName": "partition_key_name", "KeyType": "HASH"},
        {"AttributeName": "sort_key_name", "KeyType": "RANGE"}
      ],
      "GlobalSecondaryIndexes": [
        {
          "IndexName": "GSIName",
          "KeySchema": [
            {"AttributeName": "gsi_partition_key", "KeyType": "HASH"},
            {"AttributeName": "gsi_sort_key", "KeyType": "RANGE"}
          ],
          "Projection": {
            "ProjectionType": "ALL|KEYS_ONLY|INCLUDE",
            "NonKeyAttributes": ["attr1", "attr2"]
          }
        },
        {
          "IndexName": "MultiAttributeGSIName",
          "KeySchema": [
            {"AttributeName": "gsi_pk_attr1", "KeyType": "HASH"},
            {"AttributeName": "gsi_pk_attr2", "KeyType": "HASH"},
            {"AttributeName": "gsi_pk_attr3", "KeyType": "HASH"},
            {"AttributeName": "gsi_pk_attr4", "KeyType": "HASH"},
            {"AttributeName": "gsi_sk_attr1", "KeyType": "RANGE"},
            {"AttributeName": "gsi_sk_attr2", "KeyType": "RANGE"},
            {"AttributeName": "gsi_sk_attr3", "KeyType": "RANGE"},
            {"AttributeName": "gsi_sk_attr4", "KeyType": "RANGE"}
          ],
          "Projection": {
            "ProjectionType": "ALL|KEYS_ONLY|INCLUDE",
            "NonKeyAttributes": ["attr1", "attr2"]
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
            "partition_key": {"S": "value"},
            "sort_key": {"S": "value"},
            "attribute": {"S|N|B|SS|NS|BS|M|L|BOOL|NULL": "value"}
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
      "index": "GSIName|null",
      "dynamodb_operation": "Query|GetItem|PutItem|UpdateItem|DeleteItem|BatchGetItem|TransactWrite",
      "implementation": "aws dynamodb [operation] --table-name TableName --key-condition-expression 'pk = :pk' --expression-attribute-values '{\":pk\":{\"S\":\"value\"}}'",
      "reason": "Optional: Why pattern cannot be implemented in DynamoDB"
    }
  ]
}
```

## JSON Generation Rules

### Tables Section Rules

Generate boto3 `create_table` format with AttributeDefinitions, TableName, KeySchema, GlobalSecondaryIndexes, BillingMode:

- **Map attribute types**: string→S, number→N, binary→B
- **Include ONLY key attributes** used in KeySchemas in AttributeDefinitions (table keys AND GSI keys)
- **CRITICAL**: Never include attributes in AttributeDefinitions that aren't used in any KeySchema - this violates DynamoDB validation
- **Extract partition_key and sort_key** from table description
- **Include GlobalSecondaryIndexes array** with GSI definitions from `### GSIName GSI` sections
- **If no GSIs exist** for a table, omit the GlobalSecondaryIndexes field entirely
- **If multiple GSIs exist** for a table, include all of them in the GlobalSecondaryIndexes array
- **For each GSI**: Include IndexName, KeySchema, Projection with correct ProjectionType
- **Use INCLUDE projection** with NonKeyAttributes from "Per‑Pattern Projected Attributes" section
- **CRITICAL - NonKeyAttributes**: When using INCLUDE projection, NEVER include key attributes in NonKeyAttributes array. Key attributes (partition key, sort key, base table keys, and ALL multi-attribute key components) are automatically projected. Only include non-key attributes.

#### Multi-Attribute Keys in GSIs (Only When Detected)

**IMPORTANT: Multi-attribute keys are NOT the default. Only use when explicitly indicated in dynamodb_data_model.md.**

**What are Multi-Attribute Keys?**
Multi-attribute keys allow GSI keys to be composed of multiple discrete attributes (up to 4 per key type). For the partition key, all attributes use `KeyType: 'HASH'`. For the sort key, all attributes use `KeyType: 'RANGE'`. This is a native DynamoDB feature - NOT string concatenation.

**CRITICAL: Multi-Attribute Keys vs Concatenated Strings**
- ❌ **WRONG - Concatenated String**: `{"AttributeName": "composite_key", "AttributeType": "S"}` with value `"TOURNAMENT#WINTER2024#REGION#NA-EAST"`
- ✅ **CORRECT - Multi-Attribute Key**: Multiple KeySchema entries with same KeyType:
  ```json
  {"AttributeName": "tournamentId", "KeyType": "HASH"},
  {"AttributeName": "region", "KeyType": "HASH"}
  ```

**Detecting Multi-Attribute Keys:**
Look in `dynamodb_data_model.md` for:
- GSI table showing multiple attributes in keys (e.g., "Partition Key: factory_id, status (2 attributes)" or "Sort Key: status, created_at (multi-attribute)")
- Mentions of "multi-attribute keys", "composite keys", or "Multi-Attribute Key Decision"
- GSI documentation stating "Sort Key: attr1, attr2 (multi-attribute)" format

**If NOT detected: Use standard single-attribute keys** (one HASH, optionally one RANGE per GSI)

**If detected, How to Generate:**
- Multiple attributes with same KeyType (HASH or RANGE) in GSI KeySchema
- ALL attributes must be in AttributeDefinitions with their native types (S, N, or B)
- Each attribute is a separate entry in KeySchema - DO NOT concatenate values into a single attribute
- Example: `{"AttributeName": "factory_id", "KeyType": "HASH"}, {"AttributeName": "status", "KeyType": "HASH"}` creates 2-attribute partition key

### Items Section Rules

Generate boto3 `batch_write_item` format grouped by TableName:

- **Each table contains array** of 5-10 PutRequest objects with Item data
- **Convert values to DynamoDB format**: strings→S, numbers→N, booleans→BOOL with True/False (Python-style capitalization: True not true), etc.
- **Create one PutRequest per data row**
- **Include ALL item definitions** found in markdown - do not skip any items
- **Generate realistic test data** that demonstrates the table's entity types and access patterns

### Access Patterns Section Rules

Convert to new format with keys: pattern, description, table/index (optional), dynamodb_operation (optional), implementation (optional), reason (optional):

- **Use "table" key** for table operations (queries/scans on main table)
- **Use both "table" and "index" keys** for GSI operations (queries/scans on indexes)
- **For external services** or patterns that don't involve DynamoDB operations, omit table/index, dynamodb_operation, and implementation keys and include "reason" key explaining why it was skipped
- **Convert DynamoDB Operations** to dynamodb_operation values: Query, Scan, GetItem, PutItem, UpdateItem, DeleteItem, BatchGetItem, BatchWriteItem, TransactGetItems, TransactWriteItems
- **Convert Implementation Notes** to valid AWS CLI commands in implementation field with complete syntax:
  - Include `--table-name <TableName>` for all operations
  - Include both partition and sort keys in `--key` parameters
  - **ALWAYS use `--expression-attribute-names`** for all attributes (not just reserved keywords)
  - **Use single quotes** around all JSON parameters (--expression-attribute-values, --item, --key, --transact-items, etc.)
  - **Use correct AWS CLI boolean syntax**: `--flag` for true, `--no-flag` for false (e.g., `--no-scan-index-forward` NOT `--scan-index-forward false`)
  - **Commands must be executable** and syntactically correct with valid JSON syntax
  - **CRITICAL - Query Filter Expressions**: For Query operations, NEVER use `--filter-expression` on key attributes (partition key, sort key, or any GSI key attributes including multi-attribute key components). Key attributes can ONLY be used in `--key-condition-expression`. Filter expressions can only reference non-key attributes. Note: Scan operations CAN use key attributes in filter expressions.
  - **CRITICAL - Handling != Operator with Sparse GSI**: If Implementation Notes contain `!=` or `<>` on a key attribute AND mention "Sparse GSI" (or if GSI documentation mentions "Sparse:" with an attribute name), the sparse GSI already excludes those items at the index level. Generate query with ONLY the partition key (and optionally other sort key attributes for filtering) in key-condition-expression. Do NOT try to implement the != condition in the query - it's handled by the sparse GSI design.
- **Preserve pattern ranges** (e.g. "1-2") when multiple patterns share the same description, operation, and implementation
- **Split pattern ranges** when multiple operations exist (e.g. "16-19" with GetItem/UpdateItem becomes two entries: "16-19" with GetItem operation and "16-19" with UpdateItem operation)

#### Multi-Attribute Key Query Rules (Only When GSI Uses Multi-Attribute Keys)

**IMPORTANT: These rules only apply to GSIs that use multi-attribute keys. Standard single-attribute GSIs follow normal query rules.**

When generating AWS CLI commands for GSIs with multi-attribute keys:

**Partition Key Requirements:**
- ALL partition key attributes MUST be specified with equality (`=`)
- Cannot skip any partition key attribute
- Cannot use inequality operators on partition keys
- Example: GSI with `tournamentId + region` partition key requires: `tournamentId = :t AND region = :r`

**Sort Key Requirements:**
- Query left-to-right in KeySchema order
- Cannot skip attributes (can't query attr1 + attr3 while skipping attr2)
- Inequality operators (`>`, `>=`, `<`, `<=`, `BETWEEN`, `begins_with()`) must be LAST
- Example: GSI with `round + bracket` sort key allows: `round = :r` OR `round = :r AND bracket = :b` OR `round >= :r` (but NOT `bracket = :b` alone)

### Output Requirements

- Write JSON to `dynamodb_data_model.json` with 2-space indentation
- Always include all three sections: tables, items, access_patterns
- **ALWAYS include all three keys in the JSON output: "tables", "items", "access_patterns" - even if empty arrays**

## After JSON Generation

Once the JSON file is generated, the AI will ask:

**"I've generated your `dynamodb_data_model.json` file! Now I can validate your DynamoDB data model. This comprehensive validation will:**

**Environment Setup:**
- Set up DynamoDB Local environment (tries containers first: Docker/Podman/Finch/nerdctl, falls back to Java)

**⚠️ IMPORTANT - Isolated Environment:**
- **Creates a separate DynamoDB Local instance** specifically for validation (container: `dynamodb-local-setup-for-data-model-validation` or Java process: `dynamodb.local.setup.for.data.model.validation`)
- **Does NOT affect your existing DynamoDB Local setup** - uses an isolated environment
- **Cleans up only validation tables** to ensure accurate testing

**Validation Process:**
- Create tables from your data model specification
- Insert test data items into the created tables
- Test all defined access patterns
- Save detailed validation results to `dynamodb_model_validation.json`
- Transform results to markdown format for comprehensive review

**This validation helps ensure your design works as expected and identifies any issues. Would you like me to proceed with the validation?**"

If you respond positively (yes, sure, validate, test, etc.), the AI will immediately call the `dynamodb_data_model_validation` tool.

## How to Use This Guide

1. **If you haven't started modeling yet**: Call the `dynamodb_data_modeling` tool to begin the design process
2. **If you have a design but no JSON**: Provide your `dynamodb_data_model.md` content to the AI and ask it to generate the JSON following this guide
3. **If you have the JSON**: Proceed directly to calling `dynamodb_data_model_validation` tool

## Example Workflow

```
User: "I want to design a DynamoDB model for my e-commerce application"
AI: [Calls dynamodb_data_modeling tool, guides through requirements]
AI: [Creates dynamodb_requirement.md and dynamodb_data_model.md]
AI: "Would you like me to generate the JSON model and validate?"
User: "Yes"
AI: [Generates dynamodb_data_model.json following this guide]
AI: "Would you like me to proceed with validation?"
User: "Yes"
AI: [Calls dynamodb_data_model_validation tool]
```

## Need Help?

If you're unsure about any step, call the `dynamodb_data_modeling` tool and the AI will guide you through the entire process from requirements gathering to validation.
