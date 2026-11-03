# End-to-end test: The guide, unprompted

2026-11-03 21:48 UTC

- **Scenario**: `guide`
- **Code under test**: `feat/redshift-guide-skill` at `f67f46ea`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 2.2 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each
- **Target**: `mcp-e2e-harbor`, Serverless, 8 RPU, unseeded

## Summary

Graded by the harness from the server log.

| Check | Result |
|---|---|
| Guide retrieved with no argument before the first query | PASS |
| Target's type taken from list_clusters, not asked for or guessed wrong | PASS |
| Reference files loaded unprompted, each in full | PASS |

## Prompt

Written by the harness, not by hand, and never says what to expect.

Which tables in database `dev` on my Redshift warehouse `mcp-e2e-harbor` take up the most space, and how much of that space could be reclaimed?

## Transcript

I'll start by loading the Redshift guide this server requires, and discover the cluster at the same time.`mcp-e2e-harbor` is a Serverless workgroup. This is a storage-attribution question, so the guide requires me to load its storage reference first.Now I'll run the anchor attribution query and load the reclaim-estimate guidance at the same time.Only one row came back, a small internal table. Let me check whether `dev` actually holds user tables and whether I'm seeing everything.Superuser access confirmed, so nothing is hidden from me. `dev` has only the default schemas, so let me check `public` for tables.**`dev` on `mcp-e2e-harbor` has no user tables, so there is nothing taking up space and nothing to reclaim.**

What I checked:

- `SVV_TABLE_INFO` (the per-table attribution view, queried as superuser `IAMR:Admin`, so nothing was hidden by permissions) returned a single row: `pg_internal.redshift_auto_health_check_`, 0.03 GB, 4,000 rows, 0 ghost rows. That is a Redshift-managed internal health-check table, not your data.

- `dev` contains only `information_schema`, `pg_catalog` and `public`, and `public` is empty. So the absence of rows in `SVV_TABLE_INFO` is a genuinely empty database, not the view omitting zero-block tables.

Reclaimable space is zero. The estimate for a `VACUUM DELETE ONLY` is `size_gb × (ghost_rows / tbl_rows)` per table, and the only table present reports 0 ghost rows, so a vacuum would return nothing and is not worth the I/O.

Two things worth knowing before you conclude the warehouse is empty:

- The workgroup also has three auto-mounted catalogs (`awsdatacatalog`, `[catalog]@s3tablescatalog`, `[catalog]@s3tablescatalog`). Data there sits in S3/Iceberg, is billed as S3 storage rather than Redshift managed storage, and Redshift cannot be connected to those catalogs for size inspection, so it does not appear in any per-table view here.

- Your account has six other warehouses with a `dev` database, including `mcp-e2e-serverless` and `mcp-e2e-provisioned` (same e2e-harness tag) plus `redshift-cluster-analytics`, `-appsec`, `-marketing` and `redshift-workgroup-etl`. If you expected tables, you may be thinking of one of those. Name one and I'll run the same attribution against it.

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] Running: @awslabs.redshift-mcp-server/list_databases

[tool] status: Completed

[tool] status: Completed
