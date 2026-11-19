# End-to-end test: The guide, unprompted

2026-11-13 23:30 UTC

- **Scenario**: `guide`
- **Code under test**: `fix/redshift-read-only-transaction-rollback` at `8998a9d0`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 1.5 min
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

**Nothing to report and nothing to reclaim: `dev` on `mcp-e2e-harbor` holds no user tables.**

`SVV_TABLE_INFO` (superuser, so the view is unfiltered) returns exactly one row for the whole database:

| schema | table | size | ghost rows | unsorted | vacuum_sort_benefit |

|---|---|---|---|---|---|

| pg_internal | redshift_auto_health_check_ | 32 MB (32 blocks) | 0 of 4,000 | null | null |

That is Redshift's own internal health-check relation, not yours. `tbl_rows - estimated_visible_rows` is 0, so there are no ghost rows to clear, and `vacuum_sort_benefit` is null, so there is no sort debt either. Reclaimable space: 0. Do not run VACUUM here.

The only user-visible schema, `public`, contains no tables; the rest are `pg_catalog` and `information_schema`.

Two things worth knowing before you conclude the workgroup is empty:

- The workgroup also has three auto-mounted catalogs (`awsdatacatalog`, `[catalog]@s3tablescatalog`, `[catalog]@s3tablescatalog`). Their data sits in S3/Glue, not in Redshift managed storage, and Redshift refuses connections to them, so neither this server nor `SVV_TABLE_INFO` can size them. Check those through S3 or the Glue/S3 Tables console.

- `SVV_TABLE_INFO` covers permanent user tables only. If a billing or capacity figure for this workgroup looks larger than 32 MB, the rest is temp/spill, catalog, snapshot and recovery-point storage, none of which VACUUM touches. `SVV_TABLES_SPACE_USAGE` splits perm vs temp vs datashared per node if you want that breakdown, and `sys_serverless_usage` covers billed storage.

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_databases

[tool] status: Completed
