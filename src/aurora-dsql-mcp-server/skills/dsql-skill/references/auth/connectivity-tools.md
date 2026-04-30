# DSQL Connectivity & Data Loading Tools

Part of [DSQL Development Guide](../development-guide.md).

---

## Database Connectivity Tools

DSQL has many tools for connecting including 10 database drivers, 4, ORM libraries, and 3 specialized adapters
across various languages as listed in the [programming guide](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/aws-sdks.html). PREFER using connectors, drivers, ORM libraries, and adapters.

### Database Drivers

Low-level libraries that directly connect to the database:

| Programming Language | Driver                           | Sample Repository                                                                                            |
| -------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **C++**              | libpq                            | [C++ libpq samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/cpp/libpq)                  |
| **C# (.NET)**        | Npgsql                           | [.NET Npgsql samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/dotnet/npgsql)            |
| **Go**               | pgx                              | [Go pgx samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/go/pgx)                        |
| **Java**             | pgJDBC                           | [Java pgJDBC samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/java/pgjdbc)              |
| **Java**             | DSQL Connector for JDBC          | JDBC samples                                                                                                 |
| **JavaScript**       | DSQL Connector for node-postgres | [Node.js samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/javascript/node-postgres)     |
| **JavaScript**       | DSQL Connector for Postgres.js   | [Postgres.js samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/javascript/postgres-js)   |
| **Python**           | Psycopg                          | [Python Psycopg samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/python/psycopg)        |
| **Python**           | DSQL Connector for Psycopg2      | [Python Psycopg2 samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/python/psycopg2)      |
| **Python**           | DSQL Connector for Asyncpg       | [Python Asyncpg samples](https://github.com/awslabs/aurora-dsql-python-connector/tree/main/examples/asyncpg) |
| **Ruby**             | pg                               | [Ruby pg samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/ruby/ruby-pg)                 |
| **Rust**             | SQLx                             | [Rust SQLx samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/rust/sqlx)                  |

### Object-Relational Mapping (ORM) Libraries

Standalone libraries that provide object-relational mapping functionality:

| Programming Language | ORM Library | Sample Repository                                                                                                 |
| -------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------- |
| **Java**             | Hibernate   | [Hibernate Pet Clinic App](https://github.com/awslabs/aurora-dsql-hibernate/tree/main/examples/pet-clinic-app)    |
| **Python**           | SQLAlchemy  | [SQLAlchemy Pet Clinic App](https://github.com/awslabs/aurora-dsql-sqlalchemy/tree/main/examples/pet-clinic-app)  |
| **TypeScript**       | Sequelize   | [TypeScript Sequelize samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/typescript/sequelize) |
| **TypeScript**       | TypeORM     | [TypeScript TypeORM samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/typescript/type-orm)    |

### Aurora DSQL Adapters and Dialects

Specific extensions that make existing ORMs work with Aurora DSQL:

| Programming Language | ORM/Framework | Repository                                                                           |
| -------------------- | ------------- | ------------------------------------------------------------------------------------ |
| **Java**             | Hibernate     | [Aurora DSQL Hibernate Adapter](https://github.com/awslabs/aurora-dsql-hibernate/)   |
| **Python**           | Django        | [Aurora DSQL Django Adapter](https://github.com/awslabs/aurora-dsql-django/)         |
| **Python**           | SQLAlchemy    | [Aurora DSQL SQLAlchemy Adapter](https://github.com/awslabs/aurora-dsql-sqlalchemy/) |

---

## Data Loading Tools

The [DSQL Loader](https://github.com/aws-samples/aurora-dsql-loader) is a fast parallel data loader for DSQL that supports
loading from CSV, TSV, and Parquet files into DSQL with automatic schema detection and progress tracking.

Developers SHOULD PREFER the DSQL Loader for:

- quick, managed loading without user supervision
- populating test tables
- migrating data into DSQL from local files or S3 URIs of type csv, tsv, or parquet
- automated schema detection and progress tracking

ALWAYS use the loader's schema inference, PREFERRED to separate schema
creation for data migration.

**Install and use the DSQL Loader with [loader.sh](../../scripts/loader.sh)**

### Common Examples

**Load from S3:**

```bash
aurora-dsql-loader load \
  --endpoint your-cluster.dsql.us-east-1.on.aws \
  --source-uri s3://my-bucket/data.parquet \
  --table analytics_data
```

**Create table automatically from a local filepath:**

```bash
aurora-dsql-loader load \
  --endpoint your-cluster.dsql.us-east-1.on.aws \
  --source-uri data.csv \
  --table new_table \
  --if-not-exists
```

**Validate a local file without loading:**

```bash
aurora-dsql-loader load \
  --endpoint your-cluster.dsql.us-east-1.on.aws \
  --source-uri data.csv \
  --table my_table \
  --dry-run
```
