# MySQL to DSQL: NULL and DEFAULT Constraints

For `SET NOT NULL`, use [Table Recreation](../ddl-migrations/overview.md#table-recreation).

## ALTER COLUMN SET NOT NULL

Validate that the source has no nulls before recreation:

```python
readonly_query(
    "SELECT COUNT(*) AS null_count FROM target_table WHERE target_column IS NULL"
)
```

## ALTER COLUMN DROP NOT NULL

Translate directly:

```python
transact(["ALTER TABLE target_table ALTER COLUMN target_column DROP NOT NULL"])
```

## ALTER COLUMN SET/DROP DEFAULT

Translate directly. Defaults apply to future inserts; they do not backfill existing rows:

```python
transact(["ALTER TABLE target_table ALTER COLUMN status SET DEFAULT 'pending'"])
transact(["ALTER TABLE target_table ALTER COLUMN status DROP DEFAULT"])
```
