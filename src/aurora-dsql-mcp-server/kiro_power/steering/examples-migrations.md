# DSQL Examples: Migration Execution

Part of [Aurora DSQL Implementation Examples](../dsql-examples.md).

---

## Migration Execution

**Pattern:** MUST execute each DDL statement separately (DDL statements execute outside transactions)

Source: Adapted from [aurora-dsql-samples/java/liquibase](https://github.com/aws-samples/aurora-dsql-samples/tree/main/java/liquibase)

```javascript
const migrations = [
  {
    id: '001_initial_schema',
    description: 'Create owner and pet tables',
    statements: [
      `CREATE TABLE IF NOT EXISTS owner (
         id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
         name VARCHAR(30) NOT NULL,
         city VARCHAR(80) NOT NULL,
         telephone VARCHAR(20)
       )`,
      `CREATE TABLE IF NOT EXISTS pet (
         id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
         name VARCHAR(30) NOT NULL,
         birth_date DATE NOT NULL,
         owner_id UUID
       )`,
    ]
  },
  {
    id: '002_create_indexes',
    description: 'Create async indexes',
    statements: [
      'CREATE INDEX ASYNC idx_owner_city ON owner(city)',
      'CREATE INDEX ASYNC idx_pet_owner ON pet(owner_id)',
    ]
  },
  {
    id: '003_add_columns',
    description: 'Add status column',
    statements: [
      'ALTER TABLE pet ADD COLUMN IF NOT EXISTS status VARCHAR(20)',
      "UPDATE pet SET status = 'active' WHERE status IS NULL",
    ]
  }
];

async function runMigrations(pool, migrations) {
  for (const migration of migrations) {
    for (const statement of migration.statements) {
      if (statement.trim()) {
        await pool.query(statement);
      }
    }
  }
}
```
