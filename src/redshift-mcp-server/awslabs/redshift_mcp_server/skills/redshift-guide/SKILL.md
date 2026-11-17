---
name: redshift-guide
description: "Amazon Redshift is NOT PostgreSQL; corrects LLM mistakes; covers SQL, metadata, connectivity/auth, storage, query performance, and operations. Applies ONLY to Redshift (provisioned or Serverless). Pushes back on: CREATE INDEX, string_agg, pg_catalog, text type, SERIAL, stl_query. Triggers on: Redshift SQL, Redshift CREATE TABLE, Redshift COPY/UNLOAD, slow or suddenly slow Redshift query, EXPLAIN plan, queue wait, stale statistics/ANALYZE, result cache, Redshift permission denied, Redshift disk full, storage growth, snapshot/backup cost, ghost rows/bloat, VACUUM, spill to disk, distribution skew, Redshift system views, QUALIFY, PIVOT, MERGE, materialized views, Redshift Data API (Python/boto3), Redshift workload management (WLM), concurrency scaling, Redshift resize, Spectrum, awsdatacatalog, connection failures (SSL/TLS, ODBC/JDBC, connection limit), IAM/SAML federation, IAM Identity Center, datashares. Does NOT apply to: S3 policies, Athena, Glue/Iceberg outside Redshift, Aurora, RDS, DynamoDB."
metadata:
  version: "2"
---

# Amazon Redshift Guide

## Redshift is NOT PostgreSQL (read first)

Redshift speaks PostgreSQL's wire protocol and shares much of its surface syntax, so
LLMs assume PostgreSQL behavior carries over — it frequently does not. Divergences span
system tables (`pg_catalog` is incomplete), DDL (no indexes, no sequences), functions
(`string_agg`, `SUBSTR` on tables, leader-node-only functions), types (a `text` column
becomes VARCHAR(256)), and comparison semantics (trailing blanks, unenforced constraints). **Assume
divergence and verify against the reference below — do not answer from PostgreSQL habit.**
Common PostgreSQL→Redshift divergences are in `references/redshift-sql-syntax.md`.

**This guide ships with this server.** Run the SQL it recommends, SHOW commands and system views
included, through `execute_query`, one statement per call. The `list_*` tools discover clusters,
databases, schemas, tables and columns, and `review_cluster` runs a cluster review. To load a
reference this guide cites, call `retrieve_skill_file` with the path exactly as cited. This
server runs no AWS CLI command: give the user the ones this guide shows, or run them with another
tool you have. The database user this server connects as sees only its own rows (the queries it
generated) in the system views, with no error, unless it is a superuser or has `sys:monitor` or
`SYSLOG ACCESS UNRESTRICTED`; some views refuse it with `permission denied` instead
→ `references/redshift-auth-authorization.md`.

## STEP 0: Serverless or Provisioned?

Establish this before answering — APIs, system tables, and capabilities differ. Take it
from the question when it says which one, else from the `type` of the target's `list_clusters`
entry; **ask** only when neither settles it. `SELECT version()` does not identify it.

- **Serverless** — identified by a *workgroup* (and namespace). Data API calls take
  `--workgroup-name`; the user says "workgroup"/"Serverless".
- **Provisioned** — identified by a *cluster*. Data API calls take
  `--cluster-identifier`; the user says "cluster".

| Target | System Views | Credentials API |
|---|---|---|
| **Provisioned** | SYS_, all SVV_ + STL_, STV_, SVL_, SVCS_ (single-AZ only — disabled on Multi-AZ) | `redshift:GetClusterCredentials` |
| **Serverless** | `SYS_` + a subset of `SVV_` ONLY (no STL/STV/SVL/SVCS) | `redshift-serverless:GetCredentials` |

## Critical Facts

- **SHOW commands are the primary metadata interface** — SHOW DATABASES, SHOW SCHEMAS, SHOW TABLES, SHOW COLUMNS, SHOW TABLE, SHOW VIEW. Do NOT default to pg_catalog or information_schema. → **Load `references/redshift-sql-metadata.md` for metadata/discovery questions and any "relation does not exist" report** — it has the diagnostic flow.
- **`SYS_` views are the preferred system views** — they work everywhere. `STL_`, `STV_`, `SVL_`, and `SVCS_` are provisioned single-AZ only, and some `SVV_` views are unsupported on Serverless. → **Load `references/redshift-sql-metadata.md` for any system-view or monitoring question.**
- **`sys_load_error_detail`** for COPY debugging (not `stl_load_errors`, which is provisioned single-AZ only).
- **DATEADD/DATEDIFF** — unit-first argument order: `DATEADD(day, -30, GETDATE())`, `DATEDIFF(day, start, end)`.
- **APPROXIMATE COUNT(DISTINCT col)** — Redshift-specific, ~2% error, much faster than exact COUNT(DISTINCT) on large datasets.
- **MERGE ... REMOVE DUPLICATES** — simplified dedup when source and target have identical schemas.
- **COPY should use IAM_ROLE** (the namespace role, not the caller role) + supports MANIFEST for explicit file lists + MAXERROR for error tolerance.
- **`SUBSTR()` is leader-node-only** — works on literals but errors on table columns (`SUBSTR() function is not supported (Hint: use SUBSTRING instead)`). Use `SUBSTRING()` on columns.
- **UNIQUE / PRIMARY KEY / FOREIGN KEY are informational only** — NOT enforced (duplicate rows are accepted with no error). Optimizer hints; enforce integrity in the application or via MERGE. `NOT NULL` IS enforced.
- **`SHOW VIEW <schema.name>`** returns the definition of a regular view, materialized view, or late-binding view. MV freshness: `SVV_MV_INFO` (`is_stale`).
- **No `FILTER (WHERE ...)` on aggregates** — PostgreSQL-only, Redshift rejects it. Write `COUNT(CASE WHEN cond THEN 1 END)` / `SUM(CASE WHEN cond THEN x END)` instead. This applies to every query you emit, including ones you derive from a reference example.
- **`TOP N` and `LIMIT N` both work** (`TOP N PERCENT` does not). A `text` column becomes `VARCHAR(256)` — use `VARCHAR(max)` or explicit length.
- **Iceberg tables use `CREATE TABLE ... USING ICEBERG`** (not `STORED AS ICEBERG`, not `TABLE_FORMAT=ICEBERG`).
- **Datashares support read and write operations** — consumers can write once the producer grants write privileges. Treat "permission denied" on a datashare write as a **missing grant**, not an unsupported operation. → **Load `references/redshift-sql-metadata.md` for requirements and limits.**
- **Storage: attribute before you remediate, and never reflex-VACUUM.** Disk-full is usually NOT data growth — rule out transient query **spill** (temp blocks) and per-node/slice **skew** first, because the cluster average hides a single full node. On RA3/Serverless a high local reading is **cache**, not out-of-space, and free managed storage does not prevent a node-local Disk Full. `SVV_TABLE_INFO.unsorted` alone is misleading — gate sorting on `vacuum_sort_benefit`. **"Storage is growing / what is driving it" is a different question from "storage is high"**: it needs a trend over months (CloudWatch, not a point-in-time view), per-table attribution is always partial, and the per-table sum is never the cluster total. → **Load `references/redshift-storage-utilization.md` to attribute space, then `references/redshift-storage-remediation.md` to act.**

## Safety Guardrails

**BLOCK:** DROP DATABASE, DELETE without WHERE, publicly-accessible=true, GRANT ALL ON ALL
**WARN then confirm:** RESIZE, RESTORE, VACUUM on large tables, ALTER PASSWORD, WLM config change, TRUNCATE / DROP TABLE — **`TRUNCATE` forces an implicit COMMIT and cannot be rolled back** (it also commits other pending work in the same transaction), so name the target table and say the rows are unrecoverable before proceeding; treat it as routine only on temp/staging tables the user has already called disposable
**Confirm:** CREATE, GRANT specific, COPY, UNLOAD

## Security Considerations

Apply these defaults when generating anything that connects, loads, or exports. Details
are in the reference files noted.

- **In transit:** the Data API is HTTPS-only. For JDBC/ODBC set the `require_ssl`
  parameter and connect with `sslmode=verify-full` so the server certificate is checked.
- **At rest:** keep cluster/namespace encryption enabled, and add
  `ENCRYPTED KMS_KEY_ID '<arn>'` to `UNLOAD` — it writes query results to S3, outside
  Redshift's own encryption. → `references/redshift-sql-ddl-copy.md`
- **Credentials:** prefer `SecretArn` (Secrets Manager) or IAM Identity Center; `DbUser`
  is acceptable because it issues temporary credentials. Never place database passwords in
  code, environment variables, or SQL text. → `references/redshift-sql-recipes-load-api.md`
- **Least privilege:** scope the namespace `IAM_ROLE` to the specific bucket and prefix
  (`s3:GetObject` on `arn:aws:s3:::<bucket>/<prefix>/*`), not `s3:*` or a managed
  full-access policy, and condition its trust policy on both `aws:SourceArn` (the
  cluster/namespace ARN) and `aws:SourceAccount` — `SourceArn` alone still allows another
  resource in the account to assume it. Grant per-object privileges rather than
  `GRANT ALL ON ALL`.
- **Audit:** CloudTrail records `redshift-data:*` API calls but not the SQL executed;
  enable Redshift audit logging (`useractivitylog`, `connectionlog`, `userlog`) for that.
  Both capture query text and user activity, so encrypt every destination in use:
  the CloudWatch Logs group (`aws logs associate-kms-key`), the CloudTrail trail
  (SSE-KMS), and the audit-log S3 bucket (SSE-S3 — audit logging to S3 supports only
  S3-managed keys, not KMS). Serverless only supports sending audit logs to CloudWatch.
- **Network:** keep `PubliclyAccessible=false` and connect over a VPC
  endpoint. Do not open port 5439 to `0.0.0.0/0` or `::/0` — scope inbound rules to
  specific CIDRs or to a referencing security group.
- **Sensitive data:** Data API results persist for 24h and `sys_load_error_detail` can
  echo fragments of rejected rows, so treat statement IDs and load-error output as
  sensitive.
- **Further reading:**
  [Security in Amazon Redshift](https://docs.aws.amazon.com/redshift/latest/dg/c_security-overview.html)
  for the full guidance behind these defaults.

## Routing Table

**MANDATORY:** When a question matches a row below, you MUST load and read the referenced file BEFORE answering.

**Establish whether the target is provisioned or Serverless before giving troubleshooting steps —
from the question when it says which one, without re-confirming, else from the `type` of its
`list_clusters` entry; ask only when neither settles it.**

| User Intent | Route To |
|---|---|
| "CREATE TABLE", "DISTKEY/SORTKEY", "ENCODE", "IDENTITY", "COPY", "UNLOAD", "IAM_ROLE", "Iceberg table" | `references/redshift-sql-ddl-copy.md` |
| "LISTAGG", "DATEADD/DATEDIFF", "NVL/DECODE", "type mapping", "text type", "VARBYTE", "recursive CTE" | `references/redshift-sql-functions-types.md` |
| "QUALIFY", "PIVOT/UNPIVOT", "MERGE", "TOP N", "SUBSTR error", "UNIQUE/PK not enforced", "trailing blanks", "leader-node function", "JSON", "SUPER", "PartiQL", "nested/semi-structured data" | `references/redshift-sql-extensions-semantics.md` |
| "system view", "SVV_/SYS_", "SHOW commands", "STL vs SYS", "list tables", "distkey/sortkey lookup", "datashare discovery", "2-part vs 3-part", "permission denied", "GRANT", "privileges", **"relation/table does not exist"** | `references/redshift-sql-metadata.md` |
| "how do I write SQL", "PostgreSQL vs Redshift", "which SQL reference", general dialect question | `references/redshift-sql-syntax.md` (index of the 6 SQL references + PostgreSQL-vs-Redshift failure table) |
| "COPY failed", "load error", "Data API poll", "async query", "Data API throttle" | `references/redshift-sql-recipes-load-api.md` |
| "materialized view", "MV refresh", "AUTO REFRESH", "stale view" | `references/redshift-sql-materialized-views.md` |
| "disk full" / error 1016 / 34507, "PercentageDiskSpaceUsed", "storage grew", "what's consuming space", "ghost rows", "tombstone", "spill to disk", "managed storage vs local SSD", "datashare cache", "one node full / storage skew", "Serverless storage inflation", "what is driving the storage increase" / "storage keeps climbing" / "grew N% per month" / "which tables are growing" / "is vacuum missing" — a growth-over-time question, answered by the *"Is it growing, and what is driving it?"* section: split it into four (is it really that full, is it vacuum debt, how much would VACUUM return, what is driving the trend), trend from CloudWatch over months, per-table attribution from `SYS_VACUUM_HISTORY`, and state plainly what cannot be attributed from customer-side views, any snapshot / backup / recovery-point billing or cost question — including "AWS Backup", "cross-region snapshot copy", "backup billed at full size", "why is snapshot storage this expensive", "incremental so it should be cheaper" (answer from the per-type × per-platform matrix in S16, never from AWS Backup's own incremental-copy documentation, which describes AWS Backup's behavior and not Redshift's manual-snapshot metering), "cluster unavailable / stuck after hitting 100% storage" (confirm the fill first — `PercentageDiskSpaceUsed` in CloudWatch, since the SQL views are unreachable while the cluster is down, and rule out the non-storage causes before assuming disk) — attribute the space first | `references/redshift-storage-utilization.md` |
| "VACUUM won't finish / times out", "which VACUUM mode — DELETE ONLY / SORT ONLY / FULL / RECLUSTER", "vacuum_sort_benefit", "unsorted", "reclaim space", "deep copy", "auto-vacuum CPU", "distribution key skew", "recovering a cluster stuck or unavailable at ~100% storage — headroom plus escalation", "resize failed and stuck in canceling-resize" — take action | `references/redshift-storage-remediation.md` |
| "slow Redshift query", "query was fast now slow", "why is my query slow", "query performance", "time decomposition", "queue vs execution time", "planning/compile time", "result cache hit / false fast", "EXPLAIN plan", "DS_BCAST_INNER / broadcast / nested loop / merge join", "stale statistics / ANALYZE / bad row estimate", "function on join key / plan flip", "distribution skew / skew_rows / one slice", "did the query change / query hash", "row multiplication / join fan-out / DISTINCT slow", "sys_query_history / sys_query_detail" | `references/redshift-sql-query-performance.md` |
| "ready-to-run performance query", "which SQL to run", "diagnostic queries", "execution step / skew / spill", "plan diff between runs", "svv_table_info table health", "auto-analyze / auto-vacuum history", "lock wait / transaction history" | `references/redshift-sql-query-performance-queries.md` |
| "connection timed out/refused", "SSO/federated login fails", "Response signature invalid", "assumeRoleWithSAML", "RedshiftDbUser principal tag", "sts:TagSession AccessDenied", "IAM Identity Center region", "connection limit exceeded", "ODBC/JDBC driver", "ODBC 1.x EOL/CVE", "SSL error/certificate verify failed", "permission denied to query database created from datashare", "SYSLOG ACCESS/system-table row visibility", "GetClusterCredentials AccessDenied" | `references/redshift-auth-authorization.md` |
| General Redshift question not matching above | Answer directly from general knowledge |
| Aurora, RDS, DynamoDB, Athena (non-Redshift) | **REFUSE.** State this skill is for Amazon Redshift only. Do not provide guidance for other database services. |

## Data API Quick Reference

→ **Load `references/redshift-sql-recipes-load-api.md` before answering ANY Data API, COPY-error, or async-query question.** It carries the bounded poll loop, the `HasResultSet` and `ResourceNotFoundException` handling, the per-target parameters, and the auth options.

Data API calls are **async by default** — use long polling (`--wait-time-seconds`, 1–30)
rather than blind sleeps, and keep a bounded loop for work that can exceed 30s.
Serverless takes `--workgroup-name`, provisioned takes `--cluster-identifier`.
