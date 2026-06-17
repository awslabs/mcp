# Postgres MCP Server — End-to-End Tests

These tests run against **real Aurora PostgreSQL clusters** that the test
creates, exercises, and tears down. They are not part of the unit test suite
(`pytest tests/`) and are not run in CI by default, because they provision real
AWS resources, take several minutes, and require live AWS credentials.

There are two scripts in this directory:

| Script | What it does |
|--------|--------------|
| `e2e_integration_test.py` | Full lifecycle: creates clusters, runs the MCP tools (`connect_to_database`, `run_query`, `get_table_schema`, …), validates security/enforcement behavior, then deletes everything it created. |
| `e2e_test_sql_injection.py` | Focused check that `get_table_schema` is parameterized and resists a SQL-injection-shaped table name. Connects to an **already-existing** cluster you specify. |

---

## Prerequisites

1. **AWS credentials** with permissions to:
   - Create/describe/delete RDS (Aurora) clusters and instances
   - Read AWS Secrets Manager secrets (`secretsmanager:GetSecretValue`)
   - Manage the `AuroraIAMAuth-postgres` IAM policy (for IAM-auth connection methods)
   - For `--test-non-express-cluster`: `ec2:*SecurityGroup*` and `ec2:DescribeVpcs`
   The test uses the `AWS_PROFILE` / standard boto3 credential chain.
2. **Python 3.10+** and `uv` (see the top-level project README for setup).
3. Run commands from the project root: `src/postgres-mcp-server/`.

> **Cost note:** the test creates real Aurora clusters. They are deleted on a
> clean exit, but if the process is killed (SIGKILL, machine sleep) a cluster
> can leak. See [Cleanup & leaked resources](#cleanup--leaked-resources).

---

## `e2e_integration_test.py`

### What it creates

By **default the run creates only an Express cluster** — express provisions in
well under a minute. The Serverless v2 cluster is opt-in because its instance
provisioning adds roughly 7–8 minutes to the run.

| Cluster | Created when | Tested with |
|---------|-------------|-------------|
| Express | always | `PG_WIRE_IAM_PROTOCOL` (publicly reachable, no network setup) |
| Serverless v2 | `--test-serverless-cluster` (or `--test-non-express-cluster`) | `RDS_API` (public HTTPS) |
| Serverless v2 — PG Wire | `--test-non-express-cluster` | `PG_WIRE_IAM_PROTOCOL`, `PG_WIRE_PROTOCOL` (needs VPC reachability) |

### Test phases

1. **Phase 1 — cluster creation.** Each `create_cluster` call is itself recorded
   as a test case, so a creation failure shows up in the summary and fails the run.
2. **Phase 2 — functional SQL suite.** For each compatible (cluster, connection
   method) cell: `connect_to_database`, `is_database_connected`,
   `get_database_connection_info`, `run_query(SELECT …)`, `get_table_schema`,
   a `DROP TABLE` that is expected to be rejected, and a manual cleanup.
3. **Phase 3 — security / invariant suites** (per cluster):
   - `endpoint_validation` — caller-supplied `db_endpoint` must match a real
     cluster endpoint.
   - `secret_arn_validation` — Secrets Manager ARN resolution / override priority.
   - `query_enforcement` — drives `run_query` under **both** `--allow_write_query`
     settings (toggled in-process) and asserts: read queries allowed in both
     modes; mutating keywords blocked in read-only mode and allowed past the
     guard in write mode; dangerous functions and security-sensitive GUCs blocked
     in **both** modes.
   - `startup_secret_arn_validation` — server startup probe rejects an unreadable
     `--secret_arn`.

Every planned case appears in the final summary as PASS / FAIL / SKIP. A
suite-level exception is recorded as a failure for that suite only and does not
cascade.

### Usage

```bash
# Default: express-only, fast (~1-2 min)
uv run python tests/e2e/e2e_integration_test.py \
    --region us-west-2 \
    --engine-version 16.4 \
    --database mcp_test_db \
    --port 5432

# Also create + test the serverless cluster via RDS_API (adds ~7-8 min)
uv run python tests/e2e/e2e_integration_test.py \
    --region us-west-2 --engine-version 16.4 \
    --test-serverless-cluster

# Full run including serverless PG Wire (requires VPC reachability to the cluster)
uv run python tests/e2e/e2e_integration_test.py \
    --region us-west-2 --engine-version 16.4 \
    --test-non-express-cluster

# Capture the log to a file while still watching it live
uv run python tests/e2e/e2e_integration_test.py \
    --region us-west-2 --engine-version 16.4 \
    2>&1 | tee e2e.log
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--region` | required | AWS region (e.g. `us-west-2`). |
| `--engine-version` | required | Aurora PostgreSQL engine version (e.g. `16.4`). |
| `--database` | `mcp_test_db` | Database name created on the serverless cluster. (Express auto-creates only `postgres`, which the tests use for express.) |
| `--port` | `5432` | Database port. |
| `--log-level` | `INFO` | loguru level. Use `DEBUG` to see cluster property dumps and other verbose internals. |
| `--test-serverless-cluster` | off | Also create + test the serverless cluster (RDS_API). |
| `--test-non-express-cluster` | off | Also test serverless via PG Wire. **Implies `--test-serverless-cluster`.** Requires VPC reachability — see below. |

### `--test-non-express-cluster` networking

The serverless cluster lives in a VPC and is reachable on TCP 5432 only from
inside that VPC. When this flag is set, the test:

1. Creates the serverless writer instance with `PubliclyAccessible=true`.
2. Creates a dedicated security group (`mcp-e2e-pgwire-<timestamp>`, tagged
   `mcp-e2e=true`) in the default VPC, authorizing inbound 5432 from a fixed set
   of managed prefix lists.
3. Tears the security group down on exit.

For this to work, the host running the test must reach the cluster through one
of those prefix lists' networks. If your egress is not covered by them, the PG
Wire connection will time out — see the prefix-list constant
`E2E_TEST_PREFIX_LIST_IDS` near the top of `e2e_integration_test.py`.

---

## `e2e_test_sql_injection.py`

A standalone check against an **existing** cluster (it does not create one). It
connects, fetches a known table's schema, then attempts a malicious table name
to confirm parameterization holds.

```bash
uv run python tests/e2e/e2e_test_sql_injection.py \
    --directory . \
    --region us-west-2 \
    --database-type APG \
    --connection-method RDS_API \
    --cluster-identifier my-cluster \
    --db-endpoint my-cluster-instance-1.xxxx.us-west-2.rds.amazonaws.com \
    --database postgres
```

---

## Cleanup & leaked resources

On a clean exit the test deletes every cluster and security group it created.
If the process is killed mid-run, resources can leak. The next run self-heals:

- **IAM policy:** at startup the run clears stale `dbuser` entries from the
  `AuroraIAMAuth-postgres` policy so it can't grow past IAM's size cap.
- **Security groups:** at startup the run deletes leftover `mcp-e2e-pgwire-*`
  groups (tagged `mcp-e2e=true`) older than one hour.
- **Clusters:** leaked clusters are **not** auto-deleted. If a run is killed,
  check for `mcp-e2e-express-*` / `mcp-e2e-serverless-*` clusters and delete
  them manually:

  ```bash
  aws rds describe-db-clusters --region us-west-2 \
    --query "DBClusters[?starts_with(DBClusterIdentifier, 'mcp-e2e-')].DBClusterIdentifier"
  ```

---

## Troubleshooting

- **`uv run` picks the wrong Python / `libpython3.10.so` error:** invoke the
  virtualenv interpreter directly, e.g. `.venv/bin/python tests/e2e/e2e_integration_test.py …`.
- **Serverless PG Wire times out with `PoolTimeout`:** the test host can't reach
  the cluster on 5432. Confirm your egress is covered by the configured prefix
  lists, or run without `--test-non-express-cluster`.
- **`default VPC … none found`:** `--test-non-express-cluster` needs a default
  VPC in the region. Use a region that has one, or omit the flag.
- **Noisy logs:** the default level is `INFO`. Drop to `WARNING` for less, or
  raise to `DEBUG` when diagnosing.
