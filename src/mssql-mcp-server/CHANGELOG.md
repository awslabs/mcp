# Changelog

## Unreleased

### Fixed
- `run_query` no longer drops columns that share a name. Rows are dicts keyed
  by column name, so in `SELECT *` over a join of two tables that both have
  `id` or `name`, the last of those columns overwrote the others, and
  `SELECT 1, 2`, whose columns have no names, returned only `2`. A result that
  repeats a column name now returns an error that names the columns and asks
  for aliases, the same as the db2 server.

## 0.1.0 (initial release)

### Features
- Initial release of the AWS Labs MCP server for Microsoft SQL Server on AWS RDS
- Support for direct SQL Server connections with password authentication (Secrets Manager)
- SQL injection detection and mutating keyword blocking
- Read-only mode enforcement
