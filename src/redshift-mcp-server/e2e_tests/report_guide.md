# End-to-end test: The guide, unprompted

2026-11-05 02:25 UTC

- **Scenario**: `guide`
- **Code under test**: `feat/redshift-guide-skill` at `6d01b634`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 2.0 min
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

I'll start by loading the Redshift guide, as this server requires.`mcp-e2e-harbor` is a serverless workgroup, so I'll attribute space with `SVV_TABLE_INFO` (the STV/STL storage views don't exist there).Only an internal table came back. Let me confirm that's the real picture and not a visibility limit.**Database `dev` on `mcp-e2e-harbor` holds no user tables, so there is nothing consuming space and nothing to reclaim.**

What `SVV_TABLE_INFO` returns is a single row, and it isn't yours:

| schema | table | size | rows | ghost rows |

|---|---|---|---|---|

| pg_internal | redshift_auto_health_check_ | 32 MB | 4,000 | 0 |

That table belongs to Redshift's own automatic health check. It carries zero ghost rows, and you can't vacuum or drop it in any case.

A cross-check backs this up: I'm connected as `IAMR:Admin`, a superuser, so `SVV_TABLE_INFO` rows aren't being filtered by privilege; `dev` contains only `public`, `pg_catalog` and `information_schema`, and `public` is empty.

Two things worth knowing before you go looking elsewhere:

- The workgroup also auto-mounts three external catalogs (`awsdatacatalog`, `[catalog]@s3tablescatalog`, `[catalog]@s3tablescatalog`). Data in those lives in S3 or S3 Tables and is billed there, not as Redshift managed storage. Redshift refuses connections to an auto-mounted catalog, so neither I nor `SVV_TABLE_INFO` can size them from here.

- If you see a storage figure in the console or in CloudWatch that this doesn't explain, on Serverless that reading is managed storage plus cache plus query spill, not permanent table data. Snapshots and recovery points also bill against managed storage and never show up in `SVV_TABLE_INFO`. Pruning old recovery points would be the lever there, not `VACUUM`.

If you expected tables here, tell me which workgroup or cluster you think they're on and I'll run the same attribution against it.

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_databases

[tool] status: Completed
