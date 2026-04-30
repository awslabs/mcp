# MySQL to DSQL Migration: Type Mapping & Feature Alternatives

This guide provides migration patterns for converting MySQL DDL operations to Aurora DSQL-compatible equivalents, including the **Table Recreation Pattern** for schema modifications that require rebuilding tables.

For DDL operation details, see [ddl-operations.md](ddl-operations.md). For a full migration example, see [full-example.md](full-example.md).

---

## CRITICAL: Destructive Operations Warning

**The Table Recreation Pattern involves DESTRUCTIVE operations that can result in DATA LOSS.**

Table recreation requires dropping the original table, which is **irreversible**. If any step fails after the original table is dropped, data may be permanently lost.

### Mandatory User Verification Requirements

Agents MUST obtain explicit user approval before executing migrations on live tables:

1. **MUST present the complete migration plan** to the user before any execution
2. **MUST clearly state** that this operation will DROP the original table
3. **MUST confirm** the user has a current backup or accepts the risk of data loss
4. **MUST verify with the user** at each checkpoint before proceeding:
   - Before creating the new table structure
   - Before beginning data migration
   - Before dropping the original table (CRITICAL CHECKPOINT)
   - Before renaming the new table
5. **MUST NOT proceed** with any destructive action without explicit user confirmation
6. **MUST recommend** performing migrations on non-production environments first

### Risk Acknowledgment

Before proceeding, the user MUST confirm:

- [ ] They understand this is a destructive operation
- [ ] They have a backup of the table data (or accept the risk)
- [ ] They approve the agent to execute each step with verification
- [ ] They understand the migration cannot be automatically rolled back after DROP TABLE

---

## MySQL Data Type Mapping to DSQL

Map MySQL data types to their DSQL equivalents.

### Numeric Types

| MySQL Type                  | DSQL Equivalent                                 | Notes                                                  |
| --------------------------- | ----------------------------------------------- | ------------------------------------------------------ |
| TINYINT                     | SMALLINT                                        | DSQL has no TINYINT; SMALLINT is smallest integer type |
| SMALLINT                    | SMALLINT                                        | Direct equivalent                                      |
| MEDIUMINT                   | INTEGER                                         | DSQL has no MEDIUMINT; use INTEGER                     |
| INT / INTEGER               | INTEGER                                         | Direct equivalent                                      |
| BIGINT                      | BIGINT                                          | Direct equivalent                                      |
| TINYINT(1)                  | BOOLEAN                                         | MySQL convention for booleans maps to native BOOLEAN   |
| FLOAT                       | REAL                                            | Direct equivalent                                      |
| DOUBLE                      | DOUBLE PRECISION                                | Direct equivalent                                      |
| DECIMAL(p,s) / NUMERIC(p,s) | DECIMAL(p,s) / NUMERIC(p,s)                     | Direct equivalent                                      |
| BIT(1)                      | BOOLEAN                                         | Single bit maps to BOOLEAN                             |
| BIT(n)                      | BYTEA                                           | Multi-bit maps to BYTEA                                |
| UNSIGNED integers           | Use next-larger signed type or CHECK constraint | DSQL has no UNSIGNED; use CHECK (col >= 0)             |

### String Types

| MySQL Type        | DSQL Equivalent                    | Notes                                                                                    |
| ----------------- | ---------------------------------- | ---------------------------------------------------------------------------------------- |
| CHAR(n)           | CHAR(n)                            | Direct equivalent                                                                        |
| VARCHAR(n)        | VARCHAR(n)                         | Direct equivalent                                                                        |
| TINYTEXT          | TEXT                               | DSQL uses TEXT for all unbounded strings                                                 |
| TEXT              | TEXT                               | Direct equivalent                                                                        |
| MEDIUMTEXT        | TEXT                               | DSQL uses TEXT for all unbounded strings                                                 |
| LONGTEXT          | TEXT                               | DSQL uses TEXT for all unbounded strings                                                 |
| ENUM('a','b','c') | VARCHAR(255) with CHECK constraint | See [ENUM Migration](ddl-type-alternatives.md#enum-type-migration)                              |
| SET('a','b','c')  | TEXT                               | Store as comma-separated TEXT; see [SET Migration](ddl-type-alternatives.md#set-type-migration) |

### Date/Time Types

| MySQL Type | DSQL Equivalent | Notes                                                            |
| ---------- | --------------- | ---------------------------------------------------------------- |
| DATE       | DATE            | Direct equivalent                                                |
| DATETIME   | TIMESTAMP       | DATETIME maps to TIMESTAMP                                       |
| TIMESTAMP  | TIMESTAMP       | Direct equivalent; MUST manage auto-updates in application layer |
| TIME       | TIME            | Direct equivalent                                                |
| YEAR       | INTEGER         | Store as 4-digit integer                                         |

### Binary Types

| MySQL Type   | DSQL Equivalent | Notes                               |
| ------------ | --------------- | ----------------------------------- |
| BINARY(n)    | BYTEA           | DSQL uses BYTEA for binary data     |
| VARBINARY(n) | BYTEA           | DSQL uses BYTEA for binary data     |
| TINYBLOB     | BYTEA           | DSQL uses BYTEA for all binary data |
| BLOB         | BYTEA           | DSQL uses BYTEA for all binary data |
| MEDIUMBLOB   | BYTEA           | DSQL uses BYTEA for all binary data |
| LONGBLOB     | BYTEA           | DSQL uses BYTEA for all binary data |

### Other Types

| MySQL Type     | DSQL Equivalent                                           | Notes                                                                                            |
| -------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| JSON           | TEXT                                                      | MUST store as TEXT                                                                               |
| AUTO_INCREMENT | UUID with gen_random_uuid(), IDENTITY column, or SEQUENCE | See [AUTO_INCREMENT Migration](ddl-auto-increment.md#auto_increment-migration) for all three options |

---

## MySQL Features Requiring DSQL Alternatives

MUST use the following DSQL alternatives for these MySQL features:

| MySQL Feature                      | DSQL Alternative                                    |
| ---------------------------------- | --------------------------------------------------- |
| FOREIGN KEY constraints            | Application-layer referential integrity             |
| FULLTEXT indexes                   | Application-layer text search                       |
| SPATIAL indexes                    | Application-layer spatial queries                   |
| ENGINE=InnoDB/MyISAM               | MUST omit (DSQL manages storage automatically)      |
| ON UPDATE CURRENT_TIMESTAMP        | Application-layer timestamp management              |
| GENERATED columns (virtual/stored) | Application-layer computation                       |
| PARTITION BY                       | MUST omit (DSQL manages distribution automatically) |
| TRIGGERS                           | Application-layer logic                             |
| STORED PROCEDURES / FUNCTIONS      | Application-layer logic                             |

---

## MySQL DDL Operation Mapping

### Directly Supported Operations

These MySQL operations have direct DSQL equivalents:

| MySQL DDL                                  | DSQL Equivalent                                     |
| ------------------------------------------ | --------------------------------------------------- |
| `CREATE TABLE ...`                         | `CREATE TABLE ...` (with type adjustments)          |
| `DROP TABLE table_name`                    | `DROP TABLE table_name`                             |
| `ALTER TABLE ... ADD COLUMN col type`      | `ALTER TABLE ... ADD COLUMN col type`               |
| `ALTER TABLE ... RENAME COLUMN old TO new` | `ALTER TABLE ... RENAME COLUMN old TO new`          |
| `ALTER TABLE ... RENAME TO new_name`       | `ALTER TABLE ... RENAME TO new_name`                |
| `CREATE INDEX idx ON t(col)`               | `CREATE INDEX ASYNC idx ON t(col)` (MUST use ASYNC) |
| `DROP INDEX idx ON t`                      | `DROP INDEX idx` (MUST omit the ON clause)          |

### Operations Requiring Table Recreation Pattern

These MySQL operations MUST use the **Table Recreation Pattern** in DSQL:

| MySQL DDL                                                      | DSQL Approach                                                 |
| -------------------------------------------------------------- | ------------------------------------------------------------- |
| `ALTER TABLE ... MODIFY COLUMN col new_type`                   | Table recreation with type cast                               |
| `ALTER TABLE ... CHANGE COLUMN old new new_type`               | Table recreation (type change) or RENAME COLUMN (rename only) |
| `ALTER TABLE ... ALTER COLUMN col datatype`                    | Table recreation with type cast                               |
| `ALTER TABLE ... DROP COLUMN col`                              | Table recreation excluding the column                         |
| `ALTER TABLE ... ALTER COLUMN col SET DEFAULT val`             | Table recreation with DEFAULT in new definition               |
| `ALTER TABLE ... ALTER COLUMN col DROP DEFAULT`                | Table recreation without DEFAULT                              |
| `ALTER TABLE ... ADD CONSTRAINT ... UNIQUE`                    | Table recreation with constraint                              |
| `ALTER TABLE ... ADD CONSTRAINT ... CHECK`                     | Table recreation with constraint                              |
| `ALTER TABLE ... DROP CONSTRAINT ...`                          | Table recreation without constraint                           |
| `ALTER TABLE ... DROP PRIMARY KEY, ADD PRIMARY KEY (new_cols)` | Table recreation with new PK                                  |

### Operations Requiring Application-Layer Implementation

MUST implement these MySQL operations at the application layer:

| MySQL DDL                              | DSQL Approach                                             |
| -------------------------------------- | --------------------------------------------------------- |
| `ALTER TABLE ... ADD FOREIGN KEY`      | MUST implement referential integrity in application layer |
| `ALTER TABLE ... ADD FULLTEXT INDEX`   | MUST implement text search in application layer           |
| `ALTER TABLE ... ADD SPATIAL INDEX`    | MUST implement spatial queries in application layer       |
| `ALTER TABLE ... ENGINE=...`           | MUST omit                                                 |
| `ALTER TABLE ... AUTO_INCREMENT=...`   | Use SEQUENCE with setval() or IDENTITY column             |
| `CREATE TRIGGER`                       | MUST implement in application-layer logic                 |
| `CREATE PROCEDURE` / `CREATE FUNCTION` | MUST implement in application-layer logic                 |

---

## MySQL-to-DSQL Type Conversion Validation Matrix

| MySQL From Type               | DSQL To Type       | Validation                                              |
| ----------------------------- | ------------------ | ------------------------------------------------------- |
| VARCHAR -> INT/INTEGER        | VARCHAR -> INTEGER | MUST validate all values are numeric                    |
| VARCHAR -> TINYINT(1)/BOOLEAN | VARCHAR -> BOOLEAN | MUST validate values are 'true'/'false'/'t'/'f'/'1'/'0' |
| INT/INTEGER -> VARCHAR        | INTEGER -> VARCHAR | Safe conversion                                         |
| TEXT -> VARCHAR(n)            | TEXT -> VARCHAR(n) | MUST validate max length <= n                           |
| DATETIME -> DATE              | TIMESTAMP -> DATE  | Safe (truncates time)                                   |
| INT -> DECIMAL                | INTEGER -> DECIMAL | Safe conversion                                         |
| ENUM -> VARCHAR               | VARCHAR -> VARCHAR | Safe (already stored as VARCHAR in DSQL)                |
| MEDIUMINT -> BIGINT           | INTEGER -> BIGINT  | Safe conversion                                         |
| FLOAT -> DECIMAL              | REAL -> DECIMAL    | May lose precision; MUST validate acceptable            |
