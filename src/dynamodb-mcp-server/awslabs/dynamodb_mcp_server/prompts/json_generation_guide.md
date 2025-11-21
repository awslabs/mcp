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
        {"AttributeName": "partition_key_name", "AttributeType": "S|N|B"},
        {"AttributeName": "sort_key_name", "AttributeType": "S|N|B"},
        {"AttributeName": "gsi_key_name", "AttributeType": "S|N|B"}
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
- **Preserve pattern ranges** (e.g. "1-2") when multiple patterns share the same description, operation, and implementation
- **Split pattern ranges** when multiple operations exist (e.g. "16-19" with GetItem/UpdateItem becomes two entries: "16-19" with GetItem operation and "16-19" with UpdateItem operation)

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
