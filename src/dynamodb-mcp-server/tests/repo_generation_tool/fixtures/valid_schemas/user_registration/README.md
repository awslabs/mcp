# User Registration - Cross-Table Transaction Example

This example demonstrates a user registration system using **cross-table atomic transactions** to enforce email uniqueness constraints across two partition-key-only tables.

## Architecture Overview

The schema is designed around two tables with **atomic transaction patterns**:
- **Users**: Partition-key-only table for user account data
- **EmailLookup**: Partition-key-only table for email uniqueness enforcement

This design showcases DynamoDB's **TransactWriteItems** and **TransactGetItems** APIs for maintaining data consistency across multiple tables.

## Tables and Entities

### Users (Partition Key Only)
- **User**: Core user account information
- **Key Design**: `USER#{user_id}` - simple user lookups
- **Fields**: user_id, email, full_name, created_at
- **Use Case**: User authentication and profile management

### EmailLookup (Partition Key Only)
- **EmailLookup**: Email-to-user mapping for uniqueness
- **Key Design**: `EMAIL#{email}` - email-based lookups
- **Fields**: email, user_id
- **Use Case**: Email uniqueness enforcement and reverse lookups

## Why Two Tables?

### The Email Uniqueness Problem

In DynamoDB, you cannot enforce uniqueness constraints on non-key attributes. Consider these approaches:

#### ❌ Single Table with GSI (Insufficient)
```json
{
  "table": "Users",
  "partition_key": "user_id",
  "gsi": {
    "name": "EmailIndex",
    "partition_key": "email"
  }
}
```
**Problem**: GSIs don't support condition expressions like `attribute_not_exists()`. You can query to check if an email exists, but another user could register with the same email between your check and write (race condition).

#### ❌ Single Table with Conditional Write (Race Condition)
```python
# Check if email exists
response = table.query(IndexName='EmailIndex', KeyConditionExpression='email = :email')
if response['Items']:
    raise Exception("Email already exists")

# Write user (RACE CONDITION HERE!)
table.put_item(Item=user_data)
```
**Problem**: Between the query and put_item, another request could create a user with the same email.

#### ✅ Two Tables with Transaction (Atomic)
```python
# Atomic transaction - both succeed or both fail
dynamodb.transact_write_items(
    TransactItems=[
        {
            'Put': {
                'TableName': 'Users',
                'Item': user_data,
                'ConditionExpression': 'attribute_not_exists(pk)'
            }
        },
        {
            'Put': {
                'TableName': 'EmailLookup',
                'Item': email_lookup_data,
                'ConditionExpression': 'attribute_not_exists(pk)'
            }
        }
    ]
)
```
**Solution**: The transaction ensures both writes succeed atomically. If the email already exists in EmailLookup, the entire transaction fails, preventing duplicate emails.

### Benefits of Two-Table Design

1. **Atomic Uniqueness**: Email uniqueness is guaranteed by DynamoDB's transaction semantics
2. **No Race Conditions**: Condition expressions in transactions prevent concurrent duplicates
3. **Referential Integrity**: User and EmailLookup are always in sync
4. **Efficient Lookups**: Both user-by-id and user-by-email are O(1) operations
5. **Clean Rollback**: Failed transactions leave no partial state

## Key Features Demonstrated

### Cross-Table Atomic Transactions
- **TransactWrite**: Atomic creates, updates, and deletes across tables
- **TransactGet**: Atomic reads from multiple tables
- **Condition Expressions**: Enforce constraints atomically
- **All-or-Nothing**: Either all operations succeed or all fail

### Transaction Patterns

#### Pattern #100: Register User (TransactWrite)
```json
{
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
  ]
}
```
**Use Case**: Create user and email lookup atomically with duplicate prevention

#### Pattern #101: Delete User with Email (TransactWrite)
```json
{
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
  ]
}
```
**Use Case**: Delete user and email lookup atomically, ensuring referential integrity

#### Pattern #102: Get User and Email (TransactGet)
```json
{
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
  ]
}
```
**Use Case**: Atomically read user and email lookup for consistency verification

### Partition-Key-Only Tables
- **Simple lookups**: Direct GetItem operations with only partition key
- **Lower latency**: Faster access without sort key evaluation
- **Cost optimization**: Simpler keys reduce storage costs
- **Clear intent**: Schema structure matches access patterns

## Sample Use Cases

1. **User Registration**: Atomic user creation with email uniqueness guarantee
2. **Email Validation**: Check if email is already registered before signup
3. **User Deletion**: Remove user and email lookup atomically
4. **Account Cleanup**: Ensure no orphaned email lookups remain
5. **Consistency Verification**: Atomically verify user and email lookup match
6. **Duplicate Prevention**: Race-condition-free email uniqueness enforcement

## Transaction Benefits

### Atomicity Guarantees
- **All-or-Nothing**: Both tables updated or neither is updated
- **No Partial Failures**: Eliminates inconsistent state
- **Automatic Rollback**: Failed conditions roll back all operations

### Consistency Enforcement
- **Uniqueness Constraints**: Email uniqueness guaranteed by transaction
- **Referential Integrity**: User and EmailLookup always in sync
- **Condition Expressions**: Enforce business rules atomically

### Concurrency Safety
- **No Race Conditions**: Transactions serialize conflicting operations
- **Optimistic Locking**: Condition expressions prevent conflicts
- **Isolation**: Each transaction sees consistent snapshot

## Design Philosophy

This schema demonstrates the principle of **using transactions for cross-table consistency**:

- **Atomic operations** → TransactWrite for creates/updates/deletes
- **Consistency checks** → TransactGet for atomic reads
- **Uniqueness constraints** → Separate lookup table + transaction
- **Referential integrity** → Coordinated updates across tables

By using transactions, the schema achieves strong consistency guarantees that would be impossible with separate operations.

## Comparison with Non-Transactional Approach

### Without Transactions (Race Condition)
```python
# Step 1: Check email
email_exists = email_lookup_repo.get_by_email(email)
if email_exists:
    raise Exception("Email taken")

# Step 2: Create user (RACE CONDITION!)
user_repo.create(user)

# Step 3: Create email lookup (COULD FAIL!)
email_lookup_repo.create(email_lookup)
```
**Problems**:
- Race condition between check and create
- Partial failure leaves inconsistent state
- No atomicity guarantee

### With Transactions (Atomic)
```python
# Single atomic operation
transaction_service.register_user(user, email_lookup)
```
**Benefits**:
- No race conditions
- All-or-nothing guarantee
- Consistent state always

## When to Use This Pattern

Choose cross-table transactions when:
- ✅ Uniqueness constraints on non-key attributes
- ✅ Referential integrity across tables required
- ✅ Atomic multi-table updates needed
- ✅ Race conditions must be prevented
- ✅ Consistency is more important than latency

Avoid transactions when:
- ❌ Single table operations are sufficient
- ❌ Eventual consistency is acceptable
- ❌ High throughput is critical (transactions have limits)
- ❌ Operations span more than 100 items

## Transaction Limitations

### DynamoDB Transaction Constraints
- **Max 100 items**: Up to 100 items across all tables
- **Max 4 MB**: Total request size limit
- **Same region**: All tables must be in same region
- **No global tables**: Transactions don't work across regions
- **Higher latency**: Transactions are slower than single operations
- **Higher cost**: Transactions cost 2x normal writes

### Best Practices
- **Keep transactions small**: Fewer items = better performance
- **Use condition expressions**: Prevent conflicts and ensure consistency
- **Handle failures gracefully**: Implement retry logic with exponential backoff
- **Monitor costs**: Transactions are more expensive than regular operations

## Code Generation

This schema generates:
- **entities.py**: User and EmailLookup Pydantic models
- **repositories.py**: UserRepository and EmailLookupRepository (single-table operations)
- **transaction_service.py**: TransactionService with cross-table methods
- **access_pattern_mapping.json**: Includes transaction patterns with `transaction_type: "cross_table"`

### Generated TransactionService Methods

```python
class TransactionService:
    def register_user(self, user: User, email_lookup: EmailLookup) -> bool:
        """Create user and email lookup atomically."""
        # TODO: Implement with TransactWriteItems
        pass

    def delete_user_with_email(self, user_id: str, email: str) -> bool:
        """Delete user and email lookup atomically."""
        # TODO: Implement with TransactWriteItems
        pass

    def get_user_and_email(self, user_id: str, email: str) -> dict:
        """Get user and email lookup atomically."""
        # TODO: Implement with TransactGetItems
        pass
```

## Testing Strategy

### Unit Tests
- Validate schema structure
- Test transaction pattern definitions
- Verify condition expressions

### Integration Tests
- Test atomic user registration
- Test duplicate email prevention
- Test atomic deletion
- Test transaction rollback on failure

### Property-Based Tests
- Verify no duplicate emails possible
- Verify referential integrity maintained
- Verify atomicity under concurrent load

## Related Documentation

- [DynamoDB Transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html)
- [TransactWriteItems API](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_TransactWriteItems.html)
- [TransactGetItems API](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_TransactGetItems.html)
- [Condition Expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html)

## Summary

This schema showcases DynamoDB's cross-table transaction capabilities for enforcing uniqueness constraints and maintaining referential integrity. It demonstrates that while DynamoDB doesn't have built-in uniqueness constraints, you can achieve the same guarantees using transactions with condition expressions across multiple tables.

The two-table design with atomic transactions provides:
- **Strong consistency**: Email uniqueness guaranteed
- **No race conditions**: Atomic operations prevent conflicts
- **Referential integrity**: User and EmailLookup always in sync
- **Clean failure handling**: All-or-nothing semantics

This pattern is essential for any DynamoDB application requiring uniqueness constraints on non-key attributes.
