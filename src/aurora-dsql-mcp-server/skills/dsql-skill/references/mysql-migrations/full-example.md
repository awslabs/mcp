# MySQL to DSQL Migration: Full Example

End-to-end example migrating a complete MySQL CREATE TABLE to DSQL.

**MUST read [type-mapping.md](type-mapping.md) first** for data type mappings and the CRITICAL Destructive Operations Warning.
**MUST read [ddl-operations.md](ddl-operations.md)** for DDL operation patterns.

---

## Original MySQL Schema

```sql
CREATE TABLE products (
  id INT AUTO_INCREMENT PRIMARY KEY,
  tenant_id INT NOT NULL,
  name VARCHAR(255) NOT NULL,
  description MEDIUMTEXT,
  price DECIMAL(10,2) NOT NULL,
  category ENUM('electronics', 'clothing', 'food', 'other') DEFAULT 'other',
  tags SET('sale', 'new', 'featured'),
  metadata JSON,
  stock INT UNSIGNED DEFAULT 0,
  is_active TINYINT(1) DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  INDEX idx_tenant (tenant_id),
  INDEX idx_category (category),
  FULLTEXT INDEX idx_name_desc (name, description)
) ENGINE=InnoDB;
```

---

## Migrated DSQL Schema

```sql
-- Step 1: Create table (one DDL per transaction)
transact([
  "CREATE TABLE products (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     tenant_id VARCHAR(255) NOT NULL,
     name VARCHAR(255) NOT NULL,
     description TEXT,
     price DECIMAL(10,2) NOT NULL,
     category VARCHAR(255) DEFAULT 'other' CHECK (category IN ('electronics', 'clothing', 'food', 'other')),
     tags TEXT,
     metadata TEXT,
     stock INTEGER DEFAULT 0 CHECK (stock >= 0),
     is_active BOOLEAN DEFAULT true,
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   )"
])

-- Step 2: Create indexes (each in separate transaction, MUST use ASYNC)
transact(["CREATE INDEX ASYNC idx_products_tenant ON products(tenant_id)"])
transact(["CREATE INDEX ASYNC idx_products_category ON products(tenant_id, category)"])
-- MUST implement text search at application layer for FULLTEXT index equivalent
```

---

## Migration Decisions Summary

| MySQL Feature                 | DSQL Decision                                                                                                                                          |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `AUTO_INCREMENT`              | UUID with `gen_random_uuid()`, or IDENTITY column with CACHE, or SEQUENCE (see [AUTO_INCREMENT Migration](ddl-auto-increment.md#auto_increment-migration)) |
| `INT` tenant_id               | `VARCHAR(255)` for multi-tenant pattern                                                                                                                |
| `MEDIUMTEXT`                  | `TEXT`                                                                                                                                                 |
| `ENUM(...)`                   | `VARCHAR(255)` with `CHECK` constraint                                                                                                                 |
| `SET(...)`                    | `TEXT` (comma-separated)                                                                                                                               |
| `JSON`                        | `TEXT` (JSON.stringify)                                                                                                                                |
| `UNSIGNED`                    | `CHECK (col >= 0)`                                                                                                                                     |
| `TINYINT(1)`                  | `BOOLEAN`                                                                                                                                              |
| `DATETIME`                    | `TIMESTAMP`                                                                                                                                            |
| `ON UPDATE CURRENT_TIMESTAMP` | Application-layer `SET updated_at = CURRENT_TIMESTAMP`                                                                                                 |
| `FOREIGN KEY`                 | Application-layer referential integrity                                                                                                                |
| `INDEX`                       | `CREATE INDEX ASYNC`                                                                                                                                   |
| `FULLTEXT INDEX`              | Application-layer text search                                                                                                                          |
| `ENGINE=InnoDB`               | MUST omit                                                                                                                                              |

---

## Best Practices Summary

### User Verification (CRITICAL)

- **MUST present** complete migration plan to user before any execution
- **MUST obtain** explicit user confirmation before DROP TABLE operations
- **MUST verify** with user at each checkpoint during migration
- **MUST obtain** explicit user approval before proceeding with destructive actions
- **MUST recommend** testing migrations on non-production data first
- **MUST confirm** user has backup or accepts data loss risk

### MySQL-Specific Migration Rules

- **MUST map** all MySQL data types to DSQL equivalents before creating tables
- **MUST convert** AUTO_INCREMENT to UUID with gen_random_uuid(), IDENTITY column with `GENERATED AS IDENTITY (CACHE ...)`, or explicit SEQUENCE -- ALWAYS use `GENERATED AS IDENTITY` for auto-incrementing columns (see [AUTO_INCREMENT Migration](ddl-auto-increment.md#auto_increment-migration))
- **MUST replace** ENUM with VARCHAR and CHECK constraint
- **MUST replace** SET with TEXT (comma-separated)
- **MUST replace** JSON columns with TEXT
- **MUST replace** FOREIGN KEY constraints with application-layer referential integrity
- **MUST replace** ON UPDATE CURRENT_TIMESTAMP with application-layer updates
- **MUST convert** all index creation to use CREATE INDEX ASYNC
- **MUST omit** ENGINE, CHARSET, COLLATE, and other MySQL-specific table options
- **MUST replace** UNSIGNED with CHECK (col >= 0) constraint
- **MUST convert** TINYINT(1) to BOOLEAN

### Technical Requirements

- **MUST validate** data compatibility before type changes
- **MUST batch** tables exceeding 3,000 rows
- **MUST verify** row counts before and after migration
- **MUST recreate** indexes after table swap using ASYNC
- **MUST verify** new table before dropping original table
- **PREFER** cursor-based batching for very large tables
- **PREFER** batches of 500-1,000 rows for optimal throughput
