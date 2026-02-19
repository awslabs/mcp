# Cross-Table Transaction Support

This document provides comprehensive information about cross-table transaction support in the DynamoDB code generator.

## 🎯 Overview

The generator provides support for defining and generating cross-table atomic transactions using DynamoDB's TransactWriteItems and TransactGetItems APIs. This enables you to express atomic operations that span multiple tables, ensuring all operations succeed or all fail together.

**Key Features:**

- Define cross-table transaction patterns in your schema.json
- Automatically generate TransactionService class with method stubs
- Support for TransactWrite (Put, Update, Delete, ConditionCheck) operations
- Support for TransactGet operations for atomic reads
- Comprehensive validation of transaction patterns
- Integration with access pattern mapping
- Usage examples demonstrating transaction patterns

**Extensibility Note:** While the schema section is named `cross_table_access_patterns`, this initial implementation focuses specifically on atomic transactions (TransactWrite and TransactGet). The broader naming allows for future extensions to support other cross-table patterns (chain calls, batch operations, orchestrated workflows) without schema breaking changes.

## 📋 When to Use Transactions

### Use Transactions When You Need:

**1. Atomic Uniqueness Constraints**
- Enforce email uniqueness across Users and EmailLookup tables
- Prevent duplicate registrations with atomic checks
- Ensure username uniqueness with lookup tables

**2. Referential Integrity**
- Create order and update inventory atomically
- Delete user and cascade to related tables
- Maintain parent-child relationships across tables

**3. Coordinated Updates**
- Synchronize status across multiple tables
- Update aggregates and detail records together
- Maintain consistency in denormalized data

**4. Transfer Operations**
- Debit one account and credit another atomically
- Move items between tables with guarantees
- Swap or exchange data across tables

### Don't Use Transactions When:

- Single table operations are sufficient
- Eventual consistency is acceptable
- Operations don't require atomicity
- You need to operate on more than 100 items (DynamoDB limit)
- Cross-region operations are required (use global tables carefully)


## 📐 Schema Structure

### Top-Level Structure

Cross-table transaction patterns are defined in a top-level `cross_table_access_patterns` section in your schema.json:

```json
{
  "tables": [
    { "table_config": {...}, "entities": {...} }
  ],
  "cross_table_access_patterns": [
    {
      "pattern_id": 100,
      "name": "register_user",
      "description": "Create user and email lookup atomically",
      "operation": "TransactWrite",
      "entities_involved": [...],
      "parameters": [...],
      "return_type": "boolean"
    }
  ]
}
```

### Cross-Table Pattern Schema

Each pattern in `cross_table_access_patterns` has the following structure:

```json
{
  "pattern_id": 100,
  "name": "register_user",
  "description": "Create user and email lookup atomically",
  "operation": "TransactWrite",
  "entities_involved": [
    {
      "table": "Users",
      "entity": "User",
      "action": "Put",
      "condition": "attribute_not_exists(pk)"
    },
    {
      "table": "EmailLookup",
      "entity": "EmailLookup",
      "action": "Put",
      "condition": "attribute_not_exists(pk)"
    }
  ],
  "parameters": [
    { "name": "user", "type": "entity", "entity_type": "User" },
    { "name": "email_lookup", "type": "entity", "entity_type": "EmailLookup" }
  ],
  "return_type": "boolean"
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pattern_id` | integer | Yes | Globally unique pattern ID (across all patterns including per-table patterns) |
| `name` | string | Yes | Method name (snake_case for Python) |
| `description` | string | Yes | Human-readable description of what the transaction does |
| `operation` | string | Yes | Transaction type: `TransactWrite` or `TransactGet` |
| `entities_involved` | array | Yes | List of tables/entities participating in the transaction |
| `parameters` | array | Yes | Method parameters (entity types or primitives) |
| `return_type` | string | Yes | Return type: `boolean`, `object`, or `array` |


### Entity Involvement Schema

Each entry in `entities_involved` specifies one table/entity in the transaction:

```json
{
  "table": "Users",
  "entity": "User",
  "action": "Put",
  "condition": "attribute_not_exists(pk)"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `table` | string | Yes | Table name (must exist in schema's `tables` array) |
| `entity` | string | Yes | Entity name (must exist in the specified table) |
| `action` | string | Yes | DynamoDB action (see supported actions below) |
| `condition` | string | No | DynamoDB condition expression for this operation |

### Supported Actions

**TransactWrite Actions:**
- `Put` - Create or replace an item
- `Update` - Modify an existing item
- `Delete` - Remove an item
- `ConditionCheck` - Verify a condition without modifying data

**TransactGet Actions:**
- `Get` - Retrieve an item

### Parameter Types

Parameters can be entity types or primitive types:

**Entity Parameter:**
```json
{ "name": "user", "type": "entity", "entity_type": "User" }
```

**Primitive Parameter:**
```json
{ "name": "user_id", "type": "string" }
```

Supported primitive types: `string`, `integer`, `decimal`, `boolean`

### Return Types

| Return Type | Description | Use Case |
|-------------|-------------|----------|
| `boolean` | True/False success indicator | TransactWrite operations |
| `object` | Dictionary with results | TransactGet returning multiple items |
| `array` | List of items | TransactGet returning list of entities |


## 🏗️ Generated Code Structure

When your schema includes `cross_table_access_patterns`, the generator creates an additional file:

```
generated_dal/
├── entities.py                      # Existing - Pydantic entity classes
├── repositories.py                  # Existing - Single-table repositories
├── base_repository.py               # Existing - Base repository class
├── transaction_service.py           # NEW - Cross-table transaction service
├── access_pattern_mapping.json      # Updated - Includes transaction patterns
├── usage_examples.py                # Updated - Includes transaction examples
└── ruff.toml                        # Existing - Linter configuration
```

### TransactionService Class

The generated `transaction_service.py` contains:

```python
"""Cross-table transaction service for atomic operations."""

from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError

from entities import User, EmailLookup


class TransactionService:
    """Service for cross-table transactional operations.

    Currently supports atomic transactions (TransactWrite, TransactGet).
    Future versions may support additional cross-table patterns.
    """

    def __init__(self, dynamodb_resource: boto3.resource):
        """Initialize transaction service.

        Args:
            dynamodb_resource: Boto3 DynamoDB resource for multi-table access
        """
        self.dynamodb = dynamodb_resource
        self.client = dynamodb_resource.meta.client

    def register_user(self, user: User, email_lookup: EmailLookup) -> bool:
        """Create user and email lookup atomically.

        Args:
            user: User entity to create
            email_lookup: EmailLookup entity to create

        Returns:
            bool: True if transaction succeeded

        Raises:
            ValueError: If entity validation fails
            ClientError: If transaction fails
        """
        # TODO: Implement Access Pattern #100
        # Operation: TransactWrite | Tables: Users, EmailLookup
        #
        # Cross-Table Transaction Example:
        # 1. Validate entity relationships (if needed)
        # 2. Build keys for all entities
        # User.build_pk_for_lookup(...)
        # EmailLookup.build_pk_for_lookup(...)
        # 3. Convert entities to DynamoDB items
        # user_item = user.model_dump(exclude_none=True)
        # email_lookup_item = email_lookup.model_dump(exclude_none=True)
        # 4. Execute transaction
        # response = self.client.transact_write_items(
        #     TransactItems=[
        #         {'Put': {'TableName': 'Users', 'Item': user_item, ...}},
        #         {'Put': {'TableName': 'EmailLookup', 'Item': email_item, ...}}
        #     ]
        # )
        # 5. Handle TransactionCanceledException for condition failures
        pass
```


### Access Pattern Mapping

Cross-table patterns are included in `access_pattern_mapping.json` with special markers:

```json
{
  "metadata": {
    "generated_at": { "timestamp": "2025-02-06T10:00:00Z" },
    "total_patterns": 21,
    "generator_type": "Jinja2Generator"
  },
  "access_pattern_mapping": {
    "100": {
      "pattern_id": 100,
      "description": "Create user and email lookup atomically",
      "operation": "TransactWrite",
      "service": "TransactionService",
      "method_name": "register_user",
      "parameters": [
        { "name": "user", "type": "entity", "entity_type": "User" },
        { "name": "email_lookup", "type": "entity", "entity_type": "EmailLookup" }
      ],
      "return_type": "bool",
      "entities_involved": [
        { "table": "Users", "entity": "User", "action": "Put" },
        { "table": "EmailLookup", "entity": "EmailLookup", "action": "Put" }
      ],
      "transaction_type": "cross_table"
    }
  }
}
```

**Key Differences from Single-Table Patterns:**
- `service` field instead of `repository`
- `entities_involved` array listing all tables/entities
- `transaction_type: "cross_table"` marker
- `operation` is TransactWrite/TransactGet instead of Query/GetItem


## 💻 Implementation Guide

### Step 1: Initialize the TransactionService

```python
import boto3
from transaction_service import TransactionService

# For local DynamoDB
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://localhost:8000',
    region_name='us-east-1'
)

# For AWS DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

# Create service instance
tx_service = TransactionService(dynamodb)
```

### Step 2: Implement TransactWrite Pattern

Example: Atomic user registration with email uniqueness

```python
def register_user(self, user: User, email_lookup: EmailLookup) -> bool:
    """Create user and email lookup atomically."""

    # 1. Validate entity relationships
    if user.user_id != email_lookup.user_id:
        raise ValueError("user_id mismatch between user and email_lookup")

    # 2. Build keys
    user_pk = User.build_pk_for_lookup(user.user_id)
    email_pk = EmailLookup.build_pk_for_lookup(email_lookup.email)

    # 3. Convert entities to DynamoDB items
    user_item = user.model_dump(exclude_none=True)
    email_item = email_lookup.model_dump(exclude_none=True)

    # 4. Execute transaction
    try:
        response = self.client.transact_write_items(
            TransactItems=[
                {
                    'Put': {
                        'TableName': 'Users',
                        'Item': user_item,
                        'ConditionExpression': 'attribute_not_exists(pk)'
                    }
                },
                {
                    'Put': {
                        'TableName': 'EmailLookup',
                        'Item': email_item,
                        'ConditionExpression': 'attribute_not_exists(pk)'
                    }
                }
            ]
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'TransactionCanceledException':
            # One or more conditions failed
            reasons = e.response['Error'].get('CancellationReasons', [])
            for reason in reasons:
                if reason.get('Code') == 'ConditionalCheckFailed':
                    raise ValueError("User or email already exists")
        raise
```


### Step 3: Implement TransactGet Pattern

Example: Atomic read of user and email lookup

```python
def get_user_and_email(self, user_id: str, email: str) -> dict[str, Any]:
    """Get user and email lookup atomically."""

    # 1. Build keys
    user_pk = User.build_pk_for_lookup(user_id)
    email_pk = EmailLookup.build_pk_for_lookup(email)

    # 2. Execute transaction
    try:
        response = self.client.transact_get_items(
            TransactItems=[
                {
                    'Get': {
                        'TableName': 'Users',
                        'Key': {'pk': user_pk}
                    }
                },
                {
                    'Get': {
                        'TableName': 'EmailLookup',
                        'Key': {'pk': email_pk}
                    }
                }
            ]
        )

        # 3. Parse results
        responses = response.get('Responses', [])
        user_data = responses[0].get('Item')
        email_data = responses[1].get('Item')

        # 4. Convert to entities
        user = User(**user_data) if user_data else None
        email_lookup = EmailLookup(**email_data) if email_data else None

        return {
            'user': user,
            'email_lookup': email_lookup
        }
    except ClientError as e:
        raise
```

### Step 4: Implement Delete Pattern

Example: Atomic deletion from multiple tables

```python
def delete_user_with_email(self, user_id: str, email: str) -> bool:
    """Delete user and email lookup atomically."""

    # 1. Build keys
    user_pk = User.build_pk_for_lookup(user_id)
    email_pk = EmailLookup.build_pk_for_lookup(email)

    # 2. Execute transaction
    try:
        response = self.client.transact_write_items(
            TransactItems=[
                {
                    'Delete': {
                        'TableName': 'Users',
                        'Key': {'pk': user_pk},
                        'ConditionExpression': 'attribute_exists(pk)'
                    }
                },
                {
                    'Delete': {
                        'TableName': 'EmailLookup',
                        'Key': {'pk': email_pk},
                        'ConditionExpression': 'attribute_exists(pk)'
                    }
                }
            ]
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'TransactionCanceledException':
            raise ValueError("User or email not found")
        raise
```


### Step 5: Implement Update Pattern

Example: Atomic update with condition check

```python
def update_user_email(
    self,
    user_id: str,
    old_email: str,
    new_email: str,
    new_email_lookup: EmailLookup
) -> bool:
    """Update user email and email lookup atomically."""

    # 1. Build keys
    user_pk = User.build_pk_for_lookup(user_id)
    old_email_pk = EmailLookup.build_pk_for_lookup(old_email)
    new_email_pk = EmailLookup.build_pk_for_lookup(new_email)

    # 2. Prepare new email lookup item
    new_email_item = new_email_lookup.model_dump(exclude_none=True)

    # 3. Execute transaction
    try:
        response = self.client.transact_write_items(
            TransactItems=[
                {
                    'Update': {
                        'TableName': 'Users',
                        'Key': {'pk': user_pk},
                        'UpdateExpression': 'SET email = :new_email',
                        'ExpressionAttributeValues': {
                            ':new_email': new_email,
                            ':old_email': old_email
                        },
                        'ConditionExpression': 'email = :old_email'
                    }
                },
                {
                    'Delete': {
                        'TableName': 'EmailLookup',
                        'Key': {'pk': old_email_pk},
                        'ConditionExpression': 'attribute_exists(pk)'
                    }
                },
                {
                    'Put': {
                        'TableName': 'EmailLookup',
                        'Item': new_email_item,
                        'ConditionExpression': 'attribute_not_exists(pk)'
                    }
                }
            ]
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'TransactionCanceledException':
            raise ValueError("Email update failed: user not found, old email mismatch, or new email already exists")
        raise
```


## 🎨 Common Patterns

### Pattern 1: Uniqueness Constraint

**Use Case:** Enforce email uniqueness across Users and EmailLookup tables

**Schema:**
```json
{
  "cross_table_access_patterns": [
    {
      "pattern_id": 100,
      "name": "register_user",
      "description": "Create user and email lookup atomically",
      "operation": "TransactWrite",
      "entities_involved": [
        {
          "table": "Users",
          "entity": "User",
          "action": "Put",
          "condition": "attribute_not_exists(pk)"
        },
        {
          "table": "EmailLookup",
          "entity": "EmailLookup",
          "action": "Put",
          "condition": "attribute_not_exists(pk)"
        }
      ],
      "parameters": [
        { "name": "user", "type": "entity", "entity_type": "User" },
        { "name": "email_lookup", "type": "entity", "entity_type": "EmailLookup" }
      ],
      "return_type": "boolean"
    }
  ]
}
```

**Why Two Tables?**
- Email uniqueness cannot be enforced via GSI with atomic constraint checking
- Separate lookup table + transaction enables atomic uniqueness enforcement
- Transaction ensures both records are created or neither is created

### Pattern 2: Referential Integrity

**Use Case:** Create order and update inventory atomically

**Schema:**
```json
{
  "cross_table_access_patterns": [
    {
      "pattern_id": 200,
      "name": "place_order_with_inventory",
      "description": "Create order and decrement inventory atomically",
      "operation": "TransactWrite",
      "entities_involved": [
        {
          "table": "Orders",
          "entity": "Order",
          "action": "Put",
          "condition": "attribute_not_exists(pk)"
        },
        {
          "table": "Inventory",
          "entity": "InventoryItem",
          "action": "Update",
          "condition": "quantity >= :order_quantity"
        }
      ],
      "parameters": [
        { "name": "order", "type": "entity", "entity_type": "Order" },
        { "name": "product_id", "type": "string" },
        { "name": "quantity", "type": "integer" }
      ],
      "return_type": "boolean"
    }
  ]
}
```


### Pattern 3: Coordinated Status Updates

**Use Case:** Update status across multiple related tables

**Schema:**
```json
{
  "cross_table_access_patterns": [
    {
      "pattern_id": 300,
      "name": "complete_workflow",
      "description": "Mark workflow and all tasks as complete",
      "operation": "TransactWrite",
      "entities_involved": [
        {
          "table": "Workflows",
          "entity": "Workflow",
          "action": "Update"
        },
        {
          "table": "Tasks",
          "entity": "Task",
          "action": "Update"
        },
        {
          "table": "Tasks",
          "entity": "Task",
          "action": "Update"
        }
      ],
      "parameters": [
        { "name": "workflow_id", "type": "string" },
        { "name": "task_ids", "type": "array" }
      ],
      "return_type": "boolean"
    }
  ]
}
```

### Pattern 4: Transfer Operations

**Use Case:** Transfer balance between accounts atomically

**Schema:**
```json
{
  "cross_table_access_patterns": [
    {
      "pattern_id": 400,
      "name": "transfer_balance",
      "description": "Debit source account and credit destination account",
      "operation": "TransactWrite",
      "entities_involved": [
        {
          "table": "Accounts",
          "entity": "Account",
          "action": "Update",
          "condition": "balance >= :amount"
        },
        {
          "table": "Accounts",
          "entity": "Account",
          "action": "Update"
        }
      ],
      "parameters": [
        { "name": "source_account_id", "type": "string" },
        { "name": "dest_account_id", "type": "string" },
        { "name": "amount", "type": "decimal" }
      ],
      "return_type": "boolean"
    }
  ]
}
```


## 🛡️ Error Handling and Retry Strategies

### Understanding Transaction Errors

**TransactionCanceledException:**
- One or more condition expressions failed
- Check `CancellationReasons` for details on which operation failed
- Common causes: item already exists, item not found, condition not met

**ValidationException:**
- Invalid transaction structure
- Too many items (max 100)
- Invalid condition expressions

**ProvisionedThroughputExceededException:**
- Table or index capacity exceeded
- Implement exponential backoff retry

**InternalServerError:**
- Temporary AWS service issue
- Safe to retry with exponential backoff

### Error Handling Pattern

```python
from botocore.exceptions import ClientError
import time
import random

def register_user_with_retry(
    self,
    user: User,
    email_lookup: EmailLookup,
    max_retries: int = 3
) -> bool:
    """Register user with exponential backoff retry."""

    for attempt in range(max_retries):
        try:
            return self.register_user(user, email_lookup)

        except ClientError as e:
            error_code = e.response['Error']['Code']

            # Don't retry validation errors or condition failures
            if error_code in ['ValidationException', 'TransactionCanceledException']:
                raise

            # Retry with exponential backoff for throttling and server errors
            if error_code in ['ProvisionedThroughputExceededException', 'InternalServerError']:
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(wait_time)
                    continue

            # Unknown error - don't retry
            raise

    raise Exception(f"Failed after {max_retries} attempts")
```


### Handling Specific Cancellation Reasons

```python
def register_user(self, user: User, email_lookup: EmailLookup) -> bool:
    """Register user with detailed error handling."""

    try:
        response = self.client.transact_write_items(
            TransactItems=[...]
        )
        return True

    except ClientError as e:
        if e.response['Error']['Code'] == 'TransactionCanceledException':
            reasons = e.response['Error'].get('CancellationReasons', [])

            # Check which operation failed
            for idx, reason in enumerate(reasons):
                code = reason.get('Code')

                if code == 'ConditionalCheckFailed':
                    if idx == 0:
                        raise ValueError("User already exists")
                    elif idx == 1:
                        raise ValueError("Email already registered")

                elif code == 'ItemCollectionSizeLimitExceeded':
                    raise ValueError("Item collection too large")

                elif code == 'ValidationError':
                    raise ValueError(f"Validation error: {reason.get('Message')}")

            # Generic failure
            raise ValueError("Transaction failed due to condition check")

        # Re-raise other errors
        raise
```

### Idempotency Pattern

For operations that may be retried, implement idempotency:

```python
def register_user_idempotent(
    self,
    user: User,
    email_lookup: EmailLookup,
    idempotency_key: str
) -> bool:
    """Register user with idempotency support."""

    # Add idempotency key to user entity
    user.idempotency_key = idempotency_key

    try:
        return self.register_user(user, email_lookup)

    except ValueError as e:
        if "already exists" in str(e):
            # Check if it's the same request (idempotent)
            existing_user = self.get_user(user.user_id)
            if existing_user and existing_user.idempotency_key == idempotency_key:
                return True  # Already processed this request
        raise
```


## ⚠️ Limitations and Best Practices

### DynamoDB Transaction Limits

| Limit | Value | Impact |
|-------|-------|--------|
| Max items per transaction | 100 | Split large operations into multiple transactions |
| Max transaction size | 4 MB | Consider item sizes when designing transactions |
| Max item size | 400 KB | Same as standard DynamoDB limit |
| Regions | Single region only | Use global tables carefully with transactions |
| Read/Write capacity | 2x normal | Transactions consume double capacity units |

### Best Practices

**✅ Do:**

1. **Keep transactions small**: Fewer items = better performance and lower cost
2. **Use condition expressions**: Prevent race conditions and ensure data integrity
3. **Validate before transacting**: Check entity relationships before executing
4. **Handle all error cases**: Implement proper error handling and retry logic
5. **Use idempotency keys**: Make operations safe to retry
6. **Monitor transaction metrics**: Track success rates and latencies
7. **Test failure scenarios**: Verify behavior when conditions fail
8. **Document transaction semantics**: Explain what atomicity guarantees exist

**❌ Don't:**

1. **Don't use for large batch operations**: Use BatchWriteItem for non-atomic bulk operations
2. **Don't ignore capacity planning**: Transactions consume 2x capacity units
3. **Don't assume success**: Always check for TransactionCanceledException
4. **Don't use across regions**: Transactions are single-region only
5. **Don't exceed 100 items**: Split into multiple transactions if needed
6. **Don't retry blindly**: Only retry appropriate error types
7. **Don't forget about costs**: Transactions are more expensive than single operations
8. **Don't use for everything**: Use single-table operations when atomicity isn't needed

### Performance Considerations

**Transaction Latency:**
- Transactions have higher latency than single operations
- Expect 2-3x latency compared to single PutItem/GetItem
- More items = higher latency

**Capacity Consumption:**
- TransactWriteItems: 2 WCUs per item
- TransactGetItems: 2 RCUs per item (eventually consistent) or 4 RCUs (strongly consistent)
- Plan capacity accordingly

**Cost Optimization:**
- Use transactions only when atomicity is required
- Batch non-atomic operations with BatchWriteItem
- Consider eventual consistency for reads when appropriate
- Monitor and optimize transaction patterns


### Schema Design Best Practices

**Pattern ID Management:**
- Use a consistent numbering scheme (e.g., 100-199 for transactions)
- Ensure pattern IDs are globally unique across all patterns
- Document pattern ID ranges in your schema

**Entity Validation:**
- Validate entity relationships before executing transactions
- Use Pydantic validators for complex validation logic
- Check foreign key relationships

**Condition Expressions:**
- Always use conditions to prevent race conditions
- Use `attribute_not_exists(pk)` for creates
- Use `attribute_exists(pk)` for updates/deletes
- Add business logic conditions (e.g., `balance >= :amount`)

**Parameter Design:**
- Use entity types for complex objects
- Use primitives for simple values (IDs, amounts)
- Keep parameter lists manageable (< 5 parameters)
- Document parameter relationships


## 🔍 Troubleshooting

### Common Issues

**Issue 1: Pattern ID Conflict**

```
Error: Pattern ID 100 is already used by pattern 'get_user' in entity 'User'
```

**Solution:** Pattern IDs must be globally unique across all patterns (per-table and cross-table). Use a different ID range for cross-table patterns (e.g., 100-199).

---

**Issue 2: Table Not Found**

```
Error: Table 'EmailLookup' referenced in pattern 'register_user' not found in schema
```

**Solution:** Ensure all tables referenced in `entities_involved` exist in the schema's `tables` array. Check for typos in table names.

---

**Issue 3: Entity Not Found**

```
Error: Entity 'EmailLookup' not found in table 'EmailLookup'
```

**Solution:** Verify the entity exists in the specified table's `entities` object. Entity names are case-sensitive.

---

**Issue 4: Invalid Action for Operation**

```
Error: Invalid action 'Put' for operation 'TransactGet'. Valid actions: Get
```

**Solution:**
- TransactWrite supports: Put, Update, Delete, ConditionCheck
- TransactGet supports: Get only
- Check your operation type matches the actions

---

**Issue 5: Invalid Operation Type**

```
Error: Invalid operation 'TransactBatch'. Valid operations: TransactWrite, TransactGet
```

**Solution:** Only `TransactWrite` and `TransactGet` are currently supported. Future versions may support additional operation types.

---

**Issue 6: Transaction Cancelled at Runtime**

```
ClientError: TransactionCanceledException
```

**Solution:** One or more condition expressions failed. Check `CancellationReasons` in the error response to identify which operation failed and why.

```python
except ClientError as e:
    if e.response['Error']['Code'] == 'TransactionCanceledException':
        reasons = e.response['Error'].get('CancellationReasons', [])
        for idx, reason in enumerate(reasons):
            print(f"Operation {idx} failed: {reason.get('Code')} - {reason.get('Message')}")
```


---

**Issue 7: Entity Validation Mismatch**

```
ValueError: user_id mismatch between user and email_lookup
```

**Solution:** Validate entity relationships before executing transactions. Ensure foreign keys match across entities.

```python
if user.user_id != email_lookup.user_id:
    raise ValueError("user_id mismatch")
```

---

**Issue 8: TransactionService Not Generated**

**Problem:** `transaction_service.py` file not created

**Solution:**
- Ensure your schema has a `cross_table_access_patterns` section
- Verify the section is not empty
- Check for validation errors that prevent generation
- Run with `--validate-only` to see validation errors

---

**Issue 9: Import Errors in Generated Code**

```
ImportError: cannot import name 'TransactionService' from 'transaction_service'
```

**Solution:**
- Verify `transaction_service.py` was generated
- Check the file is in the same directory as other generated files
- Ensure no syntax errors in generated code (run linter)

---

**Issue 10: Capacity Exceeded**

```
ProvisionedThroughputExceededException
```

**Solution:**
- Transactions consume 2x capacity units
- Increase table capacity or use on-demand billing
- Implement exponential backoff retry
- Consider reducing transaction frequency


### Debugging Tips

**1. Enable Detailed Logging**

```python
import logging
import boto3

# Enable boto3 debug logging
boto3.set_stream_logger('boto3.resources', logging.DEBUG)

# Log transaction details
logger = logging.getLogger(__name__)
logger.info(f"Executing transaction: {pattern_id}")
logger.debug(f"TransactItems: {transact_items}")
```

**2. Validate Entities Before Transactions**

```python
def register_user(self, user: User, email_lookup: EmailLookup) -> bool:
    # Validate entities
    user_errors = user.model_validate(user)
    email_errors = email_lookup.model_validate(email_lookup)

    if user_errors or email_errors:
        raise ValueError(f"Validation errors: {user_errors}, {email_errors}")

    # Validate relationships
    if user.user_id != email_lookup.user_id:
        raise ValueError("user_id mismatch")

    # Execute transaction
    ...
```

**3. Test with DynamoDB Local**

```bash
# Start DynamoDB Local
docker run -p 8000:8000 amazon/dynamodb-local

# Point your code to local endpoint
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://localhost:8000',
    region_name='us-east-1'
)
```

**4. Use AWS X-Ray for Tracing**

```python
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

# Patch boto3
patch_all()

# Transactions will be traced automatically
@xray_recorder.capture('register_user')
def register_user(self, user: User, email_lookup: EmailLookup) -> bool:
    ...
```


## 🚀 Extensibility: Future Cross-Table Patterns

The `cross_table_access_patterns` schema section is designed for extensibility. While the current implementation focuses on atomic transactions, the architecture supports future operation types.

### Current Implementation (v1)

**Supported Operations:**
- `TransactWrite` - Atomic write operations (Put, Update, Delete, ConditionCheck)
- `TransactGet` - Atomic read operations (Get)

**Service:** `TransactionService`

**Characteristics:**
- All-or-nothing atomicity
- Up to 100 items per transaction
- Single-region operations
- 2x capacity consumption

### Future Possibilities (v2+)

The schema design allows for additional operation types without breaking changes:

#### Chain Calls Pattern

Sequential operations with intermediate results:

```json
{
  "pattern_id": 500,
  "name": "get_user_with_posts",
  "operation": "ChainCall",
  "chain_steps": [
    { "table": "Users", "entity": "User", "action": "Get" },
    { "table": "Posts", "entity": "Post", "action": "Query", "uses_result_from": "step_1" }
  ],
  "parameters": [{ "name": "user_id", "type": "string" }],
  "return_type": "object"
}
```

**Service:** `ChainCallService` or `CrossTableService`

**Characteristics:**
- Sequential execution
- Intermediate results passed between steps
- No atomicity guarantee
- Useful for complex queries

#### Batch Operations Pattern

Non-atomic bulk operations across tables:

```json
{
  "pattern_id": 600,
  "name": "bulk_create_users_and_lookups",
  "operation": "BatchWrite",
  "entities_involved": [
    { "table": "Users", "entity": "User", "action": "Put" },
    { "table": "EmailLookup", "entity": "EmailLookup", "action": "Put" }
  ],
  "parameters": [
    { "name": "users", "type": "array", "entity_type": "User" },
    { "name": "lookups", "type": "array", "entity_type": "EmailLookup" }
  ],
  "return_type": "object"
}
```

**Service:** `BatchOperationService`

**Characteristics:**
- High throughput
- No atomicity
- Partial success handling
- Up to 25 items per batch


#### Orchestrated Workflows Pattern

Complex multi-step patterns with branching:

```json
{
  "pattern_id": 700,
  "name": "process_order_workflow",
  "operation": "Workflow",
  "workflow_steps": [
    { "step": "validate_inventory", "table": "Inventory", "action": "Get" },
    { "step": "create_order", "table": "Orders", "action": "Put", "condition": "inventory_available" },
    { "step": "update_inventory", "table": "Inventory", "action": "Update" },
    { "step": "notify_user", "table": "Notifications", "action": "Put" }
  ],
  "parameters": [{ "name": "order", "type": "entity", "entity_type": "Order" }],
  "return_type": "object"
}
```

**Service:** `WorkflowService`

**Characteristics:**
- Multi-step execution
- Conditional branching
- Compensation logic for failures
- Saga pattern support

### Validation Strategy for Extensibility

The validation framework is designed to support new operation types:

1. **Operation field is required** and validated against known types
2. **Unknown operations fail validation** with helpful message suggesting supported types
3. **Each operation type** has specific validation rules for its structure
4. **Future operations** can be added without breaking existing schemas

**Example Validation:**

```python
SUPPORTED_OPERATIONS = ['TransactWrite', 'TransactGet']  # v1

# Future: SUPPORTED_OPERATIONS = ['TransactWrite', 'TransactGet', 'ChainCall', 'BatchWrite']

if pattern['operation'] not in SUPPORTED_OPERATIONS:
    raise ValidationError(
        f"Invalid operation '{pattern['operation']}'. "
        f"Supported operations: {', '.join(SUPPORTED_OPERATIONS)}"
    )
```

### Adding New Operation Types

When adding a new operation type:

1. **Update validation** to recognize the new operation
2. **Add operation-specific validation rules** for the new structure
3. **Create new service class** or extend existing service
4. **Update templates** to generate appropriate code
5. **Update documentation** with new operation examples
6. **Maintain backward compatibility** with existing operations


## 📚 Complete Example: User Registration System

This example demonstrates a complete user registration system with email uniqueness enforcement using cross-table transactions.

### Schema Definition

```json
{
  "tables": [
    {
      "table_config": {
        "table_name": "Users",
        "partition_key": "pk"
      },
      "entities": {
        "User": {
          "entity_type": "USER",
          "pk_template": "USER#{user_id}",
          "fields": [
            { "name": "user_id", "type": "string", "required": true },
            { "name": "email", "type": "string", "required": true },
            { "name": "full_name", "type": "string", "required": true },
            { "name": "created_at", "type": "string", "required": true }
          ],
          "access_patterns": []
        }
      }
    },
    {
      "table_config": {
        "table_name": "EmailLookup",
        "partition_key": "pk"
      },
      "entities": {
        "EmailLookup": {
          "entity_type": "EMAIL_LOOKUP",
          "pk_template": "EMAIL#{email}",
          "fields": [
            { "name": "email", "type": "string", "required": true },
            { "name": "user_id", "type": "string", "required": true }
          ],
          "access_patterns": []
        }
      }
    }
  ],
  "cross_table_access_patterns": [
    {
      "pattern_id": 100,
      "name": "register_user",
      "description": "Create user and email lookup atomically",
      "operation": "TransactWrite",
      "entities_involved": [
        {
          "table": "Users",
          "entity": "User",
          "action": "Put",
          "condition": "attribute_not_exists(pk)"
        },
        {
          "table": "EmailLookup",
          "entity": "EmailLookup",
          "action": "Put",
          "condition": "attribute_not_exists(pk)"
        }
      ],
      "parameters": [
        { "name": "user", "type": "entity", "entity_type": "User" },
        { "name": "email_lookup", "type": "entity", "entity_type": "EmailLookup" }
      ],
      "return_type": "boolean"
    },
    {
      "pattern_id": 101,
      "name": "delete_user_with_email",
      "description": "Delete user and email lookup atomically",
      "operation": "TransactWrite",
      "entities_involved": [
        {
          "table": "Users",
          "entity": "User",
          "action": "Delete",
          "condition": "attribute_exists(pk)"
        },
        {
          "table": "EmailLookup",
          "entity": "EmailLookup",
          "action": "Delete",
          "condition": "attribute_exists(pk)"
        }
      ],
      "parameters": [
        { "name": "user_id", "type": "string" },
        { "name": "email", "type": "string" }
      ],
      "return_type": "boolean"
    },
    {
      "pattern_id": 102,
      "name": "get_user_and_email",
      "description": "Get user and email lookup atomically",
      "operation": "TransactGet",
      "entities_involved": [
        {
          "table": "Users",
          "entity": "User",
          "action": "Get"
        },
        {
          "table": "EmailLookup",
          "entity": "EmailLookup",
          "action": "Get"
        }
      ],
      "parameters": [
        { "name": "user_id", "type": "string" },
        { "name": "email", "type": "string" }
      ],
      "return_type": "object"
    }
  ]
}
```


### Usage Example

```python
import boto3
from datetime import datetime
from entities import User, EmailLookup
from transaction_service import TransactionService

# Initialize service
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
tx_service = TransactionService(dynamodb)

# Register a new user
def register_new_user(user_id: str, email: str, full_name: str):
    """Register a new user with email uniqueness guarantee."""

    # Create entities
    user = User(
        user_id=user_id,
        email=email,
        full_name=full_name,
        created_at=datetime.utcnow().isoformat()
    )

    email_lookup = EmailLookup(
        email=email,
        user_id=user_id
    )

    # Execute transaction
    try:
        success = tx_service.register_user(user, email_lookup)
        if success:
            print(f"✅ User {user_id} registered successfully")
            return user
    except ValueError as e:
        print(f"❌ Registration failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

# Delete a user
def delete_user(user_id: str, email: str):
    """Delete user and email lookup atomically."""

    try:
        success = tx_service.delete_user_with_email(user_id, email)
        if success:
            print(f"✅ User {user_id} deleted successfully")
            return True
    except ValueError as e:
        print(f"❌ Deletion failed: {e}")
        return False

# Get user and email atomically
def get_user_data(user_id: str, email: str):
    """Retrieve user and email lookup atomically."""

    try:
        result = tx_service.get_user_and_email(user_id, email)
        user = result.get('user')
        email_lookup = result.get('email_lookup')

        if user and email_lookup:
            print(f"✅ Retrieved user: {user.email}")
            return result
        else:
            print("❌ User or email not found")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# Example usage
if __name__ == "__main__":
    # Register user
    user = register_new_user(
        user_id="user_123",
        email="user123@example.com",
        full_name="John Doe"
    )

    # Try to register with same email (will fail)
    duplicate = register_new_user(
        user_id="user_456",
        email="user123@example.com",  # Duplicate!
        full_name="Jane Doe"
    )

    # Get user data
    data = get_user_data("user_123", "user123@example.com")

    # Delete user
    delete_user("user_123", "user123@example.com")
```


## ✅ Validation Rules

The generator performs comprehensive validation of cross-table transaction patterns:

### 1. Pattern ID Uniqueness

Pattern IDs must be globally unique across all patterns (per-table and cross-table):

```
❌ Error: Pattern ID 100 is already used by pattern 'get_user' in entity 'User'
```

**Solution:** Use a different ID range for cross-table patterns (e.g., 100-199).

### 2. Table Reference Validation

All referenced tables must exist in the schema's `tables` array:

```
❌ Error: Table 'EmailLookup' referenced in pattern 'register_user' not found in schema
```

**Solution:** Ensure table names match exactly (case-sensitive).

### 3. Entity Reference Validation

All referenced entities must exist in their specified tables:

```
❌ Error: Entity 'EmailLookup' not found in table 'EmailLookup'
```

**Solution:** Verify entity exists in the table's `entities` object.

### 4. Operation Type Validation

Operation must be a supported type:

```
❌ Error: Invalid operation 'TransactBatch'. Valid operations: TransactWrite, TransactGet
```

**Solution:** Use only `TransactWrite` or `TransactGet`.

### 5. Action Compatibility Validation

Actions must match the operation type:

**TransactWrite Actions:**
- `Put`, `Update`, `Delete`, `ConditionCheck`

**TransactGet Actions:**
- `Get`

```
❌ Error: Invalid action 'Put' for operation 'TransactGet'. Valid actions: Get
```

### 6. Parameter Type Validation

Entity parameters must reference valid entity types:

```
❌ Error: Entity type 'InvalidEntity' not found in schema
```

**Solution:** Ensure `entity_type` matches an entity name in the schema.

### 7. Return Type Validation

Return type must be valid:

```
❌ Error: Invalid return_type 'list'. Valid types: boolean, object, array
```

**Solution:** Use `boolean`, `object`, or `array`.


## 🎓 FAQ

### Q: Why use two tables for email uniqueness?

**A:** Email uniqueness cannot be enforced via GSI with atomic constraint checking. A separate lookup table + transaction enables atomic uniqueness enforcement. The transaction ensures both records are created or neither is created, preventing race conditions.

### Q: Can I use transactions across AWS regions?

**A:** No. DynamoDB transactions are single-region only. If you're using global tables, be careful with transactions as they don't provide cross-region atomicity.

### Q: How much do transactions cost?

**A:** Transactions consume 2x capacity units:
- TransactWriteItems: 2 WCUs per item
- TransactGetItems: 2 RCUs per item (eventually consistent) or 4 RCUs (strongly consistent)

### Q: What's the maximum number of items in a transaction?

**A:** 100 items per transaction, with a maximum total size of 4 MB.

### Q: Can I mix Put, Update, and Delete in one transaction?

**A:** Yes! TransactWrite supports any combination of Put, Update, Delete, and ConditionCheck operations.

### Q: What happens if one operation in a transaction fails?

**A:** The entire transaction is rolled back. No operations are applied. You'll receive a `TransactionCanceledException` with details about which operation failed.

### Q: Should I use transactions for all multi-table operations?

**A:** No. Use transactions only when you need atomicity. For operations where eventual consistency is acceptable, use separate operations or BatchWriteItem for better performance and lower cost.

### Q: Can I use transactions with GSIs?

**A:** Yes, but remember that GSI updates are eventually consistent. The transaction ensures atomicity for the base table operations, but GSI updates may take a moment to propagate.

### Q: How do I test transactions locally?

**A:** Use DynamoDB Local:
```bash
docker run -p 8000:8000 amazon/dynamodb-local
```

Then point your code to `http://localhost:8000`.

### Q: Can I add more operation types in the future?

**A:** Yes! The schema is designed for extensibility. Future versions may support ChainCall, BatchWrite, Workflow, and other operation types without breaking existing schemas.


## 🚀 Next Steps

1. **Review the user_registration example**: Study the complete schema in `tests/repo_generation_tool/fixtures/valid_schemas/user_registration/`

2. **Design your transaction patterns**: Identify operations that require atomicity in your application

3. **Create your schema**: Add `cross_table_access_patterns` section to your schema.json

4. **Validate**: Run with `--validate-only` flag to check for errors
   ```bash
   uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen \
     --schema your_schema.json \
     --validate-only
   ```

5. **Generate code**: Create your TransactionService
   ```bash
   uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen \
     --schema your_schema.json \
     --output-dir generated_dal \
     --generate_sample_usage
   ```

6. **Implement transaction methods**: Fill in the method bodies in `transaction_service.py`

7. **Test thoroughly**: Test success cases, failure cases, and edge cases

8. **Monitor in production**: Track transaction success rates, latencies, and costs

---

## 📖 Related Documentation

- [Schema Validation](SCHEMA_VALIDATION.md) - Detailed validation rules and error messages
- [Advanced Usage](ADVANCED_USAGE.md) - Complex patterns and advanced techniques
- [Testing Framework](TESTING.md) - Testing your generated code
- [GSI Support](GSI_SUPPORT.md) - Global Secondary Index documentation
- [Range Queries](RANGE_QUERIES.md) - Range query patterns and operators

---

## 🤝 Contributing

Found an issue or have a suggestion? Please open an issue or submit a pull request on GitHub.

---

**Last Updated:** February 6, 2026
**Version:** 1.0.0
**Status:** Stable
