# MySQL to DSQL: Type Alternatives

Part of [MySQL to DSQL DDL Migration](ddl-operations.md). See [Common Verify & Swap Pattern](ddl-operations.md#common-verify--swap-pattern) for the shared migration end-pattern.

---

## ENUM Type Migration

**MySQL syntax:**

```sql
CREATE TABLE orders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  status ENUM('pending', 'processing', 'shipped', 'delivered') NOT NULL
);
```

**DSQL equivalent using VARCHAR with CHECK:**

```sql
transact([
  "CREATE TABLE orders (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     status VARCHAR(255) NOT NULL CHECK (status IN ('pending', 'processing', 'shipped', 'delivered'))
   )"
])
```

### Migrating Existing ENUM Data

```sql
-- ENUM values are already stored as strings; direct copy is safe
transact([
  "INSERT INTO orders_new (id, status)
   SELECT gen_random_uuid(), status
   FROM orders"
])
```

---

## SET Type Migration

**MySQL syntax:**

```sql
CREATE TABLE user_preferences (
  id INT AUTO_INCREMENT PRIMARY KEY,
  permissions SET('read', 'write', 'delete', 'admin')
);
```

**DSQL equivalent using TEXT (comma-separated):**

```sql
transact([
  "CREATE TABLE user_preferences (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     permissions TEXT  -- Stored as comma-separated: 'read,write,admin'
   )"
])
```

**Note:** Application layer MUST validate and parse SET values. MySQL stores SET values as comma-separated strings internally, so direct migration preserves the format.

---

## ON UPDATE CURRENT_TIMESTAMP Migration

**MySQL syntax:**

```sql
CREATE TABLE records (
  id INT AUTO_INCREMENT PRIMARY KEY,
  data TEXT,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**DSQL equivalent:**

```sql
transact([
  "CREATE TABLE records (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     data TEXT,
     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   )"
])
```

**MUST explicitly set** `updated_at = CURRENT_TIMESTAMP` in every UPDATE statement to replicate `ON UPDATE CURRENT_TIMESTAMP` behavior:

```sql
transact([
  "UPDATE records SET data = 'new_value', updated_at = CURRENT_TIMESTAMP
   WHERE id = 'record-uuid'"
])
```

---

## FOREIGN KEY Migration

**MySQL syntax:**

```sql
CREATE TABLE orders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  customer_id INT,
  FOREIGN KEY (customer_id) REFERENCES customers(id)
);
```

**MUST implement referential integrity at the application layer:**

```sql
-- Create table with reference column (enforce integrity in application layer)
transact([
  "CREATE TABLE orders (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     customer_id UUID NOT NULL
   )"
])

-- Create index for the reference column
transact(["CREATE INDEX ASYNC idx_orders_customer ON orders(customer_id)"])
```

**Application layer MUST enforce referential integrity:**

```sql
-- Before INSERT: validate parent exists
readonly_query(
  "SELECT id FROM customers WHERE id = 'customer-uuid'"
)
-- MUST abort INSERT if parent not found

-- Before DELETE of parent: check for dependents
readonly_query(
  "SELECT COUNT(*) as dependent_count FROM orders
   WHERE customer_id = 'customer-uuid'"
)
-- MUST abort DELETE if dependent_count > 0
```
