---
inclusion: always
---
<!------------------------------------------------------------------------------------
   Add rules to this file or a short description that will apply across all your workspaces.

   Learn about inclusion modes: https://kiro.dev/docs/steering/#inclusion-modes
------------------------------------------------------------------------------------->
# Aurora Postgres MCP — Steering

## Purpose
Use the awslabs.postgres-mcp-server MCP server to create database and answer data questions against our Aurora PostgreSQL environments. Prefer natural-language → SQL via the MCP tools, with safe defaults and explicit guardrails.
AWS Labs

## When to use
- Create Aurora Postgres cluster, database, schema, and table
- Questions that require live database answers (counts, aggregates, lookups).
- Schema exploration (list tables/columns) needed to craft queries.
- Explain plans or performance diagnostics when asked explicitly.
Do not use for: speculative answers you can derive from code/docs only, or destructive changes.

## Environments & scope
- Primary environment: aurora-postgres
- PII/Secrets: Never echo secrets or full PII in chat; mask IDs to last 4 chars.

## Tool API usage guidance (important)
### Cluster Management
- Regular Cluster (Production): Call create_cluster to create a regular cluster asynchronously. This returns immediately with a job ID.
- Monitoring Async Operations: Call get_job_status with the job ID to check the status of asynchronous cluster creation. Poll every 30-60 seconds until status is COMPLETED or FAILED.

### Database Connections Management
- Call connect_to_database to establish a connection to a specific database within a cluster
- You can maintain connections to multiple databases simultaneously
- Call get_database_connection_info to get all currently connections

## Tool usage policy (important)
- Default to read-only. If a tool exposes writes, refuse gently unless user authorizes with “RUN IT”.
- Dry-run first: when feasible, request an EXPLAIN plan before running heavy queries (>5s or large scans).
- Bound queries: always include LIMIT 50 on browsing, and narrow with WHERE predicates.
- Return format: prefer compact tables; summarize in bullets; include exact SQL in a collapsible block.
- Citations: mention “(via Aurora Postgres MCP)” in answers that used the tool.
- Error handling: if a query fails, surface the error message, then propose a fixed query.
- Privacy: redact emails/phones; aggregate where possible.

## SQL style guide
- Use ANSI SQL compatible with Aurora PostgreSQL; avoid vendor-specific syntax not supported by PG.
- Qualify tables as schema.table.
- Use CTEs for clarity; prefer window functions over correlated subqueries when appropriate.
- Time zones: treat timestamps as UTC unless a column or prompt says otherwise; show conversion if user asks.
- Performance hygiene: avoid SELECT *; target only needed columns; push down filters; avoid functions on indexed columns in WHERE.

## Safety & confirmation
Destructive statements (INSERT/UPDATE/DELETE/TRUNCATE/DDL) require:

1) show the SQL; 2) explain impact; 3) ask for “RUN IT” confirmation.

- For large reads (scans > 1M rows), warn about cost/time; recommend narrower filters.
