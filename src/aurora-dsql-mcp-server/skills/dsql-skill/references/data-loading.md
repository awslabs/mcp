# Data Loading with the DSQL Loader

Part of [DSQL Development Guide](development-guide.md).

The [DSQL Loader](https://github.com/aws-samples/aurora-dsql-loader) (`aurora-dsql-loader`)
is the recommended tool for bulk-loading CSV, TSV, or Parquet data into Aurora DSQL.

For installation and basic invocation, see [connectivity-tools.md](auth/connectivity-tools.md#data-loading-tools).

## Table of Contents

- [Fresh-vs-Warm Partition Behavior](#fresh-vs-warm-partition-behavior)
- [Resume and Retry Mechanics](#resume-and-retry-mechanics)
- [Conflict Handling](#conflict-handling---on-conflict-do-nothing)
- [CSV/TSV Header Handling](#csvtsv-header-handling)
- [Schema Inference Caveats](#schema-inference-caveats)
- [Index Count Affects Throughput](#index-count-affects-throughput)
- [Diagnostic Decision Tree](#diagnostic-decision-tree)

---

## Fresh-vs-Warm Partition Behavior

DSQL tables start on a single partition and auto-split under sustained write heat. Fresh tables absorb a few thousand rec/s regardless of client concurrency — this is normal, not a problem to fix. Throughput accelerates as partitions split. See [Primary keys in Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-primary-keys.html) for partition distribution guidelines.

**Agent guidance:** when a user reports low throughput on a fresh table, do NOT recommend adding workers. Advise them to keep the load running or run a pre-pass to drive splits.

---

## Resume and Retry Mechanics

The loader writes a manifest tracking committed chunks. On resume, it restarts from the last committed chunk.

### `--manifest-dir <persistent-path>`

You **MUST** set `--manifest-dir` to a persistent path. Default `/tmp` is tmpfs on AL2023 — manifests are lost on process death.

```bash
aurora-dsql-loader load \
  --endpoint your-cluster.dsql.us-east-1.on.aws \
  --source-uri data.csv \
  --table my_table \
  --manifest-dir /var/lib/dsql-loader/manifests
```

### `--resume-job-id <id>`

Re-runs continue from the last committed chunk. The job id is printed in the loader's log on the line beginning `Starting load job:`.

```bash
aurora-dsql-loader load \
  --endpoint your-cluster.dsql.us-east-1.on.aws \
  --source-uri data.csv \
  --table my_table \
  --manifest-dir /var/lib/dsql-loader/manifests \
  --resume-job-id <job-id-from-log> \
  --keep-manifest
```

### `--keep-manifest`

Retains the manifest after a successful load. Useful for auditing or idempotent re-runs.

---

## Conflict Handling: `--on-conflict do-nothing`

`--on-conflict do-nothing` silently skips rows that violate **any** unique constraint (primary key or any UNIQUE index) on the target table.

The agent **MUST** verify these preconditions before recommending `--on-conflict do-nothing`:

1. The target table **MUST** have at least one unique constraint on the conflict column(s).
2. The load **MUST** be idempotent — the same source row produces the same target row, so skipping duplicates yields the correct final state.
3. The source data **MUST NOT** have changed since the original run if using `do-nothing` for crash recovery. Changed source rows are silently kept at their old values.

---

## CSV/TSV Header Handling

You **MUST** pass `--header` if the CSV/TSV file has a header row. The loader treats every row as data by default.

```bash
aurora-dsql-loader load \
  --endpoint your-cluster.dsql.us-east-1.on.aws \
  --source-uri sales_with_header.csv \
  --table sales \
  --header
```

**Symptoms of a missing `--header`:**

- `invalid input syntax for type <T>: "<column_name>"` — header values inserted as data.
- First batch fails entirely while subsequent batches succeed.

**Legacy behavior (v2.x):** older versions defaulted to assuming a header row. If upgrading from v2.x, add `--header` to invocations loading header-bearing files.

---

## Schema Inference Caveats

> **These produce successful loads with no error or warning.** You **MUST** validate with `--dry-run` against any new table.

Schema inference silently produces wrong types for:

- **Mixed nullability across files** — column infers as `TEXT` instead of numeric/date.
- **Numeric-looking identifiers** (ZIP codes, phone numbers with leading zeros) — infers as integer, losing leading characters.
- **Non-ISO date formats** — falls back to `TEXT` silently.

```bash
aurora-dsql-loader load \
  --endpoint your-cluster.dsql.us-east-1.on.aws \
  --source-uri data.csv \
  --table my_table \
  --dry-run
```

If the inferred schema is wrong, create the table explicitly and re-run without `--if-not-exists`.

---

## Index Count Affects Throughput

- For large loads, **SHOULD** create secondary indexes **after** the bulk load using `CREATE INDEX ASYNC`.
- For tables queried during ingestion, keep indexes in place — throughput cost is preferable to incorrect query results.

---

## Diagnostic Decision Tree

### Symptom: throughput stuck at a few thousand rec/s; host CPU is low

**Cause:** partition-constrained (fresh/few partitions).
**Action:** keep the load running. Throughput accelerates as DSQL splits. For recurring fresh-table loads, run a pre-pass to drive splits.

### Symptom: throughput below expected; host CPU > 90%

**Cause:** host-bound.
**Action:** reduce concurrency (`--workers`, `--batch-concurrency`) or use a larger host.

### Symptom: throughput below expected; host CPU ~50%; persists past 15 minutes

**Cause:** hot-key — many rows hashing to the same partition.
**Action:** inspect source for PK skew. Verify UUIDs are genuinely random (v1 UUIDs share high-order prefix).

### Symptom: "Records loaded" exceeds `SELECT count(*)` on target

**Cause:** duplicate keys in source + `--on-conflict do-nothing`.
**Action:** check source for duplicate-PK rows. De-duplicate or document the gap.

### Symptom: loader crashed; manifest is gone

**Cause:** manifest was in `/tmp` (tmpfs) and cleared on exit.
**Action:** re-run from beginning. If table has a unique constraint and load is idempotent, use `--on-conflict do-nothing` to skip already-committed rows. For future loads, **MUST** set `--manifest-dir` to persistent path.
