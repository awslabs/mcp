# ORM Migration Quick Reference

Adapter names and key gotchas per framework. This file provides DSQL-specific adapter
names and configuration not available in general documentation.

Before relying on generated foreign keys, **MUST** verify the selected adapter version's release
notes or inspect its generated DDL. When the adapter omits foreign key constraints, generate and lint
the DDL manually to preserve the relationship.

Across adapters, inline foreign keys in `CREATE TABLE` use DSQL foreign-key syntax.
Post-creation foreign keys **MUST** use `ADD CONSTRAINT ... NOT VALID`, followed by
`ALTER TABLE ASYNC ... VALIDATE CONSTRAINT` and terminal job verification.

For existing tables, emit that sequence through the framework's raw-SQL migration hook:
`RunSQL` (Django), `migrationBuilder.Sql` (EF Core), Flyway/Liquibase (Hibernate), `execute`
(Rails), or `op.execute` (Alembic/SQLAlchemy). For tenant-scoped composite FKs, use raw DDL in
Django and Rails; EF Core, Hibernate, and SQLAlchemy provide composite relationship mappings.

## Adapters

| Framework  | Adapter                                 | Install                                                      |
| ---------- | --------------------------------------- | ------------------------------------------------------------ |
| Django     | `aurora_dsql_django`                    | `pip install aurora-dsql-django boto3`                       |
| EF Core    | `Amazon.AuroraDsql.EntityFrameworkCore` | `dotnet add package Amazon.AuroraDsql.EntityFrameworkCore`   |
| Hibernate  | `aurora-dsql-hibernate-dialect`         | `software.amazon.dsql:aurora-dsql-hibernate-dialect` (Maven) |
| Rails      | Standard `pg` gem + `aws-sdk-dsql`      | `gem 'pg'` + `gem 'aws-sdk-dsql'`                            |
| SQLAlchemy | `aurora_dsql_sqlalchemy`                | `pip install aurora-dsql-sqlalchemy boto3`                   |

## Key Gotchas Per Framework

### Django

| Issue             | Fix                                                                             |
| ----------------- | ------------------------------------------------------------------------------- |
| ENGINE            | `'aurora_dsql_django'` (not `django.db.backends.postgresql`)                    |
| CONN_MAX_AGE      | ≤ 1800 (DSQL timeout is 1 hour)                                                 |
| Migrations        | Each DDL in its own migration; `RunSQL("CREATE INDEX ASYNC ...")`               |
| SELECT FOR UPDATE | Use when a write depends on rows read; retain whole-transaction OCC retry       |
| AutoField         | Replace with `UUIDField(primary_key=True, default=uuid.uuid4)`                  |
| ForeignKey        | Keep `ForeignKey`; the DSQL backend creates database constraints for new tables |

### EF Core (.NET)

Requires .NET 8.0+, EF Core 9.0.7+, and `Amazon.AuroraDsql.Npgsql` 1.1.0+.

| Issue          | Fix                                                                                                                                                                                                                                                |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Setup          | `AddDsqlDataSource(host)` then `UseDsql(sp)` in `AddDbContext` (IAM auth via `Amazon.AuroraDsql.Npgsql`)                                                                                                                                           |
| PKs            | `Guid` keys with a store-generated `gen_random_uuid()` default — leave `Id` unset on insert                                                                                                                                                        |
| Auto-increment | `long` keys via `dsql.EnableIdentityColumns()` — `cacheSize: 1` for near-strict ordering, larger (default ≥ 65536) for throughput                                                                                                                  |
| OCC retry      | `DsqlExecutionStrategy` auto-retries `SaveChangesAsync` in implicit transactions. Inside an explicit transaction it does NOT retry — use `ExecuteInTransactionAsync` and call `ChangeTracker.Clear()` first so retries don't replay stale entities |
| FK constraints | Keep relationships and generated foreign keys. Cascades count toward DSQL transaction limits                                                                                                                                                       |
| Isolation      | Requested isolation levels are ignored; `SET TRANSACTION ISOLATION LEVEL`, `SAVEPOINT`, and `LOCK TABLE` are filtered at the ADO.NET layer                                                                                                         |
| Migrations     | dsql-lint rewrites EF Core DDL for DSQL (e.g. `CREATE INDEX` → `CREATE INDEX ASYNC`) and makes it idempotent so failed migrations re-run safely                                                                                                    |

### Hibernate

| Issue          | Fix                                                                                                                                                                                                                                                                                         |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dialect        | Provided by `aurora-dsql-hibernate-dialect` (auto-registered)                                                                                                                                                                                                                               |
| ID generation  | `@GeneratedValue(strategy = GenerationType.UUID)`                                                                                                                                                                                                                                           |
| OCC retry      | Prefer the [aurora-dsql-jdbc-connector](https://github.com/awslabs/aurora-dsql-connectors/tree/main/java/jdbc) — built-in retry for SQLSTATE 40001. For manual `@Retryable`, match on `SQLException` and check `getSQLState() == "40001"` (Hibernate's class-40 mapping varies by version). |
| FK constraints | Keep normal relationship mappings; the DSQL dialect exports foreign key constraints                                                                                                                                                                                                         |
| DDL generation | `hibernate.hbm2ddl.auto = none` — manage DDL manually                                                                                                                                                                                                                                       |

### Rails

| Issue      | Fix                                                                                                                 |
| ---------- | ------------------------------------------------------------------------------------------------------------------- |
| adapter    | `postgresql` (standard pg gem)                                                                                      |
| Auth       | Custom connection handler generating IAM tokens via `aws-sdk-dsql`                                                  |
| Migrations | `disable_ddl_transaction!` in each migration                                                                        |
| PKs        | `id: :uuid` in `create_table`                                                                                       |
| FKs        | Use `add_foreign_key ..., validate: false`, then run `ALTER TABLE ASYNC ... VALIDATE CONSTRAINT` and verify the job |
| Locking    | Use `lock!` / `with_lock` when a decision depends on rows read; retain OCC retry in `ApplicationRecord`             |

### SQLAlchemy

| Issue      | Fix                                                                                |
| ---------- | ---------------------------------------------------------------------------------- |
| ForeignKey | Keep `ForeignKey` and `ForeignKeyConstraint`; the dialect emits inline constraints |

## Additional Resources

- [Migrating from PostgreSQL to Aurora DSQL — framework and ORM compatibility](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-migration-guide.html#dsql-framework-compatibility)
