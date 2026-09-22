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
| `ro_policy_differential.py` | Compares the read-only SQL policy guard against PostgreSQL's own `SET TRANSACTION READ ONLY` verdict for ~160 statements, and fails on any divergence that isn't justified in the script. Needs **only a plain PostgreSQL 13+ server** — no AWS, no Aurora. |

### Known RDS Data API limitation: array slices with named parameters

An array slice cannot be combined with `query_parameters` on the `RDS_API`
connection method. This is a Data API limitation, not an MCP server one.

Three layers independently decide which `:name` sequences are placeholders: the
SQL guard's parse-only rewrite, the psycopg executor's `%(name)s` rewrite, and —
on the `RDS_API` path only — the Data API's own server-side scanner. The first two
share a single pattern (`named_params.NAMED_PARAM_PATTERN`) and correctly leave a
slice colon alone, because the colon in `[1:2]` follows a word character. The Data
API's scanner does not, and rejects the call before PostgreSQL sees it:

```
SELECT (ARRAY['a','b','c'])[1:2] AS slice, :n::int AS n
  → ValidationException: Cannot find parameter: 2
```

It reads `:2` as a placeholder named `2`. Observed on Aurora PostgreSQL 17.5.

The scanner *is* literal-aware and cast-aware — `'a:b'`, `:n::int`, and
`IN (:a, :b)` all work — so the gap is specific to the slice. `PARAMETERIZED_SLICE_READS`
therefore runs on the PG-Wire paths, where it also guards against a defect this
server previously had (the executor once rewrote `tags[1:limit_idx]` into the
unparseable `tags[1%(limit_idx)s]`), and is recorded **N/A** on `RDS_API` rather
than asserted as a permanent AWS behavior. If AWS fixes the scanner, promote it
back into `PARAMETERIZED_READ_QUERIES`.

Workaround for callers on the Data API path: compute the bounds without a literal
slice (`array_agg` over `unnest … WITH ORDINALITY`, or `(string_to_array(...))[…]`
built from parameters), or use a PG-Wire connection method.

### Cluster teardown is fire-and-forget by default

Deleting an Aurora cluster is slow and strictly ordered: every member instance has
to be gone before `delete_db_cluster` is accepted, so the delete polls for
instance removal and then for cluster removal — up to roughly 20 minutes each in
the worst case. All of that happens *after* the last assertion is recorded, so by
default the harness hands teardown to a **detached background process** and exits
immediately.

It cannot simply be un-awaited. An asyncio task abandoned at interpreter exit is
cancelled, and firing only the instance deletions would strand the cluster. So the
work moves to a child process started with `start_new_session=True`, which keeps it
out of the harness's process group — a Ctrl-C during teardown no longer abandons a
half-deleted cluster. The child runs under `sys.executable` so it can import the
package, and its output goes to a per-cluster log:

```
Teardown of mcp-e2e-express-... running detached as pid 12345,
  log: e2e-cleanup-mcp-e2e-express-...-20260910-135114.log
```

The run prints a `tail -f` line per cluster plus an `aws rds describe-db-clusters`
command to confirm the resources actually went away.

Two consequences worth knowing:

- **A killed teardown leaks the cluster.** If the child dies — machine sleep,
  container teardown, a `SIGKILL` to the whole session — the cluster survives and
  must be deleted by hand. Pass `--wait-for-cleanup` to block until deletion
  finishes instead; that is the right choice in CI that tears the host down as
  soon as the process exits.
- **Security-group cleanup normally defers.** The SG cannot be deleted while the
  cluster's ENIs still hold it, and with detached teardown the cluster is still
  alive when the harness exits. That is logged at INFO rather than as a warning,
  and `gc_e2e_test_security_groups` reaps it on the next run.

If the detached spawn itself fails (no fork available, unwritable log directory),
the harness falls back to a blocking delete rather than leaking silently.

### Policy corpus size (`--full-policy-corpus`)

`e2e_integration_test.py` drives a curated policy corpus by default so a routine
run stays quick. Pass `--full-policy-corpus` to drive the **entire** unit-level
matrix from `tests/test_policy_matrix.py` — 200 reads, 208 writes, 98 dangerous
and 9 fail-closed statements, each in both modes — through the real `run_query`
tool, which makes this suite a literal superset of the unit policy tests.

Two things to know about what it asserts:

- Each cell checks the **policy decision**, and tolerates a database error. It
  does not check that a statement executes. The unit corpus was written for a
  parser, so 51 of its 200 reads cannot execute anywhere: 23 carry `:name`
  placeholders needing bound parameters, 4 are the locking clauses the read-only
  transaction refuses on purpose, and 24 deliberately reference objects that do
  not exist (`t`, `s`, `myschema`, large object 1) or extensions that are not
  installed. `ALLOWED_READ_QUERIES` keeps the stronger "must return rows"
  assertion on a curated set that really runs.
- It adds roughly a thousand round trips per connection method, which is why it
  is opt-in rather than the default.

The same eight cells are checked in the ordinary unit suite against a mocked
connection (`tests/test_run_query_policy_wiring.py`), so a disagreement shows up
in seconds locally rather than only after a cluster spins up. Use the flag when
changing the guard or its corpora.

---

## Prerequisites

1. **AWS credentials** with permissions to:
   - Create/describe/delete RDS (Aurora) clusters and instances
   - Read AWS Secrets Manager secrets (`secretsmanager:GetSecretValue`)
   - Create/tag/delete AWS Secrets Manager secrets (`secretsmanager:CreateSecret`,
     `TagResource`, `DeleteSecret`) — the run provisions a least-privilege role
     and stores its credentials in a temporary secret (see the
     `privilege_enforcement` suite).
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
   - `tls_enforcement` — validates TLS on the psycopg (PG Wire) path by toggling
     `server.configured_sslmode` / `server.configured_ca_bundle` in-process and
     reconnecting. Asserts: `verify-full` (default, bundled combined AWS CA)
     connects and the session is actually encrypted (`pg_stat_ssl.ssl` is true);
     `require` connects and is encrypted; and `verify-full` against an
     **unrelated CA** is rejected (proving certificate verification, not just
     encryption). Skipped on the `RDS_API` cell (verified HTTPS, no sslmode). The
     wrong-CA case needs `openssl` on the host to mint a throwaway CA (skipped
     with a note if absent), and the `verify-full` positive case needs the
     bundled AWS CA present — run `python hatch_build.py` first if running from a
     source tree.
   - `privilege_enforcement` — drives the least-privilege guardrail
     (`--privilege_check`) by toggling `server.privilege_check_policy` and the
     resolved secret in-process. It asserts the **master user** (an
     `rds_superuser` member, selected by clearing the secret pin) is **rejected
     under `enforce`** and **allowed under `warn`/`off`**, and that the
     provisioned **least-privilege role** (selected by pinning its secret) is
     **allowed under `enforce`**.

   **Least-privilege connection model (express).** Rather than connect every
   suite as the cluster master user, the run provisions a dedicated
   non-superuser role for the **express** cluster on the fly (a role with
   `USAGE`+`CREATE` on `public` and `rds_iam`, plus an `rds-db:connect` entry),
   stores its credentials in a temporary secret, and pins that secret so the
   functional and security suites authenticate as that role under `enforce` —
   mirroring the recommended production setup. The role/secret are torn down at
   the end of the run. `secret_arn_validation` still runs as master under `off`
   (it exercises the master-secret fallback), and the serverless cluster
   (opt-in) still connects as master under `off` — extending the least-privilege
   model to serverless is a follow-up.
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

## `ro_policy_differential.py`

Answers "is the read-only guard blocking anything it shouldn't?" without relying
on anyone's opinion about what counts as a read. Each of ~160 statements is run
twice — once through `assert_executable(sql, allow_write_query=False)` and once
inside `BEGIN; SET TRANSACTION READ ONLY` on a live server — and the two verdicts
are compared. PostgreSQL is the oracle.

Divergences come in two kinds:

- **false-positive candidate** — PostgreSQL executed it, the guard rejected it.
  Either over-blocking, or intentional strictness that has to be written down.
- **backstop-reliant** — the guard allowed it and PostgreSQL's read-only
  transaction refused it. Not an exposure, since the server always wraps
  read-only queries in that transaction, but it marks where the guard defers to
  the engine rather than deciding itself (currently only the `SELECT … FOR`
  locking clauses).

Every divergence must be justified in the script's `EXPECTED_DIVERGENCES` map.
An unlabeled one fails the run, so this is a regression detector rather than a
report: a denylist edit that starts blocking legitimate reads shows up here.

Unlike the other two scripts this needs no AWS and nothing Aurora-specific — any
PostgreSQL 13+ you can create a schema in will do, including a local build. It
creates the schema `mcp_ro_diff`, uses it, and drops it again.

```bash
# local PostgreSQL over a unix socket
uv run python tests/e2e/ro_policy_differential.py \
    --dsn "host=/tmp port=5432 dbname=postgres"

# an RDS/Aurora endpoint
uv run python tests/e2e/ro_policy_differential.py \
    --dsn "host=my-cluster.xxxx.us-west-2.rds.amazonaws.com port=5432 dbname=postgres \
           user=me password=... sslmode=verify-full"

# leave the probe schema behind for inspection
uv run python tests/e2e/ro_policy_differential.py --dsn "..." --keep-schema
```

Exit status is 0 when every divergence is accounted for, 1 otherwise. Sample tail
of a passing run against PostgreSQL 16.4:

```
guard read-only verdict vs PostgreSQL 16.4 read-only transaction
  SELECT grammar            95/ 99 agree
  real-world tooling        33/ 33 agree
  statement types            3/ 29 agree
OK: every divergence is accounted for (34 labeled).
```

The low agreement count for statement types is expected and is the point of the
labels: PostgreSQL permits cursors, `PREPARE`, `LISTEN`, `SET`, `LOCK`,
`CHECKPOINT`, `ANALYZE`, and the statistics/WAL mutating functions inside a
read-only transaction, and the guard rejects all of them on purpose.

The unit-test counterpart, which needs no database, is
`tests/test_sql_guard_read_only_corpus.py`. It carries the same corpora plus an
exhaustive classification of all 117 statement node types in the grammar, so a
PostgreSQL upgrade that adds one fails the suite until it is classified.

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
