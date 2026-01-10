# DSQL Language-Specific Implementation Examples and Guides
## Tenets
- ALWAYS prefer DSQL Connector when available
- Follow patterns outlined in [aurora-dsql-samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/)

## Framework and Connection Notes for Languages and Drivers
### Python
PREFER using the [DSQL Python Connector](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/SECTION_program-with-dsql-connector-for-python.html) for automatic IAM Auth:
- Compatible support in both: psycopg, psycopg2, and asyncpg - install only the needed library
  - **psycopg**
    - modern async/sync
    - `import aurora_dsql_psycopg as dsql`
    - [DSQL psycopg preferred example](https://github.com/aws-samples/aurora-dsql-samples/blob/main/python/psycopg/src/example_preferred.py)
    - See [aurora-dsql-samples/python/psycopg](https://github.com/aws-samples/aurora-dsql-samples/tree/main/python/psycopg)
  - **psycopg2**
    - synchronous
    - `import aurora_dsql_psycopg2 as dsql`
    - [DSQL psycopg2 preferred example](https://github.com/aws-samples/aurora-dsql-samples/blob/main/python/psycopg2/src/example_preferred.py)
    - See [aurora-dsql-samples/python/psycopg2](https://github.com/aws-samples/aurora-dsql-samples/tree/main/python/psycopg2)
  - **asyncpg**
    - full asynchronous style
    - `import aurora_dsql_asyncpg as dsql`
    - [DSQL asyncpg preferred example](https://github.com/aws-samples/aurora-dsql-samples/blob/main/python/asyncpg/src/example_preferred.py)
    - See [aurora-dsql-samples/python/asyncpg](https://github.com/aws-samples/aurora-dsql-samples/tree/main/python/asyncpg)

**SQLAlchemy**
- ALWAYS use psycopg2 with SQLAlchemy
- See [aurora-dsql-samples/python/sqlalchemy](https://github.com/aws-samples/aurora-dsql-samples/tree/main/python/sqlalchemy)

**JupyterLab**
- Still SHOULD PREFER using the python connector.
- Popular data science option for interactive computing environment that combines code, text, and visualizations
- Options for Local or using Anazon SageMaker
- REQUIRES downloading the Amazon root certificate from the official trust store
- See [aurora-dsql-samples/python/jupyter](https://github.com/aws-samples/aurora-dsql-samples/blob/main/python/jupyter/)

### Go

**pgx** (recommended)
- Use `aws-sdk-go-v2/feature/dsql/auth` for token generation
- Implement `BeforeConnect` hook: `config.BeforeConnect = func() { cfg.Password = token }`
- Use `pgxpool` for connection pooling with max lifetime < 1 hour
- Set `sslmode=verify-full` in connection string
- See [aurora-dsql-samples/go/pgx](https://github.com/aws-samples/aurora-dsql-samples/tree/main/go/pgx)

### JavaScript/TypeScript
PREFER using [node-postgres](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/SECTION_program-with-dsql-connector-for-node-postgres.html)
or [postgres-js](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/SECTION_program-with-dsql-connector-for-postgresjs.html) with the
DSQL Node.js Connector.

**node-postgres (pg)** (recommended)
- Use `@aws/aurora-dsql-node-postgres-connector` for automatic IAM auth
- [DSQL node-postgres preferred example](https://github.com/aws-samples/aurora-dsql-samples/blob/main/javascript/node-postgres/src/example_preferred.js)
- See [aurora-dsql-samples/javascript/node-postgres](https://github.com/aws-samples/aurora-dsql-samples/tree/main/javascript/node-postgres)

**postgres.js** (recommended)
- Lightweight alternative with `@aws/aurora-dsql-node-postgres-connector`
- Good for serverless environments
- [DSQL postgres-js preferred example](https://github.com/aws-samples/aurora-dsql-samples/blob/main/javascript/postgres-js/src/example_preferred.js)
- See [aurora-dsql-samples/javascript/postgres-js](https://github.com/aws-samples/aurora-dsql-samples/tree/main/javascript/postgres-js)

**Prisma**
- Custom `directUrl` with token refresh middleware
- See [aurora-dsql-samples/typescript/prisma](https://github.com/aws-samples/aurora-dsql-samples/tree/main/typescript/prisma)

**Sequelize**
- Configure `dialectOptions` for SSL
- Token refresh in `beforeConnect` hook
- See [aurora-dsql-samples/typescript/sequelize](https://github.com/aws-samples/aurora-dsql-samples/tree/main/typescript/sequelize)

**TypeORM**
- Custom DataSource with token refresh
- Create migrations table manually via psql
- See [aurora-dsql-samples/typescript/type-orm](https://github.com/aws-samples/aurora-dsql-samples/tree/main/typescript/type-orm)

### Java
PREFER using JDBC with the [DSQL JDBC Connector](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/SECTION_program-with-jdbc-connector.html)

**JDBC** (PostgreSQL JDBC Driver)
- Use DSQL JDBC Connector for automatic IAM auth
  - URL format: `jdbc:aws-dsql:postgresql://<endpoint>/postgres`
  - See [aurora-dsql-samples/java/pgjdbc](https://github.com/aws-samples/aurora-dsql-samples/tree/main/java/pgjdbc)
- Properties: `wrapperPlugins=iam`, `ssl=true`, `sslmode=verify-full`

**HikariCP** (Connection Pooling)
- Wrap JDBC connection, configure max lifetime < 1 hour
- See [aurora-dsql-samples/java/pgjdbc_hikaricp](https://github.com/aws-samples/aurora-dsql-samples/tree/main/java/pgjdbc_hikaricp)

### Rust

**SQLx** (async)
- Use `aws-sdk-dsql` for token generation
- Connection format: `postgres://admin:{token}@{endpoint}:5432/postgres?sslmode=verify-full`
- Use `after_connect` hook: `.after_connect(|conn, _| conn.execute("SET search_path = public"))`
- Implement periodic token refresh with `tokio::spawn`
- See [aurora-dsql-samples/rust/sqlx](https://github.com/aws-samples/aurora-dsql-samples/tree/main/rust/sqlx)

**Tokio-Postgres** (lower-level async)
- Direct control over connection lifecycle
- Use `Arc<Mutex<String>>` for shared token state
- Handle connection errors with retry logic

### Elixir

**Postgrex**
- MUST use Erlang/OTP 26+
- Driver: [Postgrex](https://hexdocs.pm/postgrex/) ~> 0.19
  - Use Postgrex.query! for all queries
  - See [aurora-dsql-samples/elixir/postgrex](https://github.com/aws-samples/aurora-dsql-samples/tree/main/elixir/postgrex)
- Connection: Implement `Repo.init/2` callback for dynamic token injection
  - MUST set `ssl: true` with `ssl_opts: [verify: :verify_peer, cacerts: :public_key.cacerts_get()]`
  - MAY prefer AWS CLI via `System.cmd` to call `generate-db-connect-auth-token`
