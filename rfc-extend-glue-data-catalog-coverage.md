RFC: Extend aws-dataprocessing-mcp-server with Iceberg detection, Data Quality, table-version, and partition-index tools

### Is this related to an existing feature request or issue?

Yes. This started as a proposal for a brand-new `aws-glue-catalog-mcp-server`, narrowed from #614 ("RFC: Data Processing MCP Server"). Investigation before filing that RFC found that `aws-dataprocessing-mcp-server` — which appears to be what #614 became — already implements 18 Glue tools covering databases, tables (CRUD + search), connections (CRUD + test + entity/metadata preview), partitions (CRUD + list), catalogs, crawlers, classifiers, crawler schedules/metrics, usage profiles, security configurations, catalog encryption, resource policies, and ETL jobs/job-runs/bookmarks. A new server would have duplicated nearly all of that. This RFC instead proposes closing four specific, verified gaps directly in `aws-dataprocessing-mcp-server`.

### Summary

Add four capabilities to `aws-dataprocessing-mcp-server`'s existing Glue Data Catalog tools, following its established "mega-tool with an `operation` parameter" pattern rather than introducing new standalone tools where an existing tool already owns the resource type:

1. **Table format detection** — new `detect-table-format` / `get-iceberg-table-info` operations on `manage_aws_glue_tables`, to classify a table as Hive, Iceberg, Delta, or Hudi and surface Iceberg-specific properties (metadata location, format version) when applicable.
2. **Glue Data Quality** — a new `manage_aws_glue_data_quality` tool (rulesets CRUD, evaluation runs, results), wiring up the `DataQualityResult` Pydantic model that already exists in `models/data_catalog_models.py` but is currently unused by any handler.
3. **Table version history** — new `get-table-versions` / `batch-delete-table-version` operations on `manage_aws_glue_tables`.
4. **Partition indexes** — new `create-partition-index` / `get-partition-indexes` / `delete-partition-index` operations on `manage_aws_glue_partitions`.

### Use case

- A migration engineer auditing a catalog asks "which tables here are Iceberg vs. still Hive?" Today the assistant can only call `get-table` and try to eyeball `Parameters['table_type']`/SerDe class names itself, inconsistently, for each table. A dedicated detection operation gives a direct, reliable answer.
- A data governance team asks "can you check the data quality results for the `orders` table?" Today this is simply impossible — there is no Glue Data Quality tool at all, despite the server's own README already advertising "automated schema discovery and data quality validation" as a feature.
- A schema-governance reviewer asks "show me the schema version history for this table — when did the `event_date` column get added?" There is currently no operation that calls `GetTableVersions`.
- A performance-tuning conversation asks "does this table have a partition index, and would adding one help this query pattern?" There is currently no operation that calls `GetPartitionIndexes`/`CreatePartitionIndex`.

### Proposal

All four additions follow the handler/model conventions already used throughout `awslabs/aws_dataprocessing_mcp_server/handlers/glue/` (a `Handler` class registering `self.mcp.tool(name=...)` in `__init__`, an `operation` string dispatch, Pydantic response models in `models/data_catalog_models.py`, and gating via `self.allow_write` / `self.allow_sensitive_data_access` inherited from the shared handler base).

| Tool | New/existing | New operations |
|---|---|---|
| `manage_aws_glue_tables` | existing (`data_catalog_handler.py`) | `detect-table-format` (read), `get-iceberg-table-info` (read), `get-table-versions` (read), `batch-delete-table-version` (write) |
| `manage_aws_glue_partitions` | existing (`data_catalog_handler.py`) | `create-partition-index` (write), `get-partition-indexes` (read), `delete-partition-index` (write) |
| `manage_aws_glue_data_quality` | **new** (`data_catalog_handler.py` or a new `data_quality_handler.py`, consistent with how crawler/commons logic got their own handler files) | `list-rulesets`, `get-ruleset`, `create-ruleset` (write), `update-ruleset` (write), `delete-ruleset` (write), `start-ruleset-evaluation-run` (write), `get-ruleset-evaluation-run`, `list-ruleset-evaluation-runs`, `get-data-quality-result`, `list-data-quality-results`, `batch-get-data-quality-result` |

**Table format detection logic:** classify using, in order, `Parameters['table_type']` (`ICEBERG` is explicit and authoritative when present), then SerDe class name / input format for Hive-style tables, then `Parameters` keys characteristic of Delta (`delta.*`) or Hudi (`hoodie.*`) table properties written by those engines. Falls back to `UNKNOWN` rather than guessing. `get-iceberg-table-info` only returns data when detection resolves to `ICEBERG`, and surfaces `metadata_location`, format version, and current snapshot info already present in the table's parameters — it does not read the Iceberg metadata JSON itself over S3 (no new S3 permissions needed).

**Data Quality:** thin wrapper over `glue:ListDataQualityRulesets`, `glue:GetDataQualityRuleset`, `glue:CreateDataQualityRuleset`, `glue:UpdateDataQualityRuleset`, `glue:DeleteDataQualityRuleset`, `glue:StartDataQualityRulesetEvaluationRun`, `glue:GetDataQualityRulesetEvaluationRun`, `glue:ListDataQualityRulesetEvaluationRuns`, `glue:GetDataQualityResult`, `glue:ListDataQualityResults`, `glue:BatchGetDataQualityResult` — the same shape as every other Glue handler in this server, just for an API surface nothing currently touches.

**Table versions / partition indexes:** thin wrappers over `glue:GetTableVersions`, `glue:BatchDeleteTableVersion`, `glue:GetPartitionIndexes`, `glue:CreatePartitionIndex`, `glue:DeletePartitionIndex` — no new design pattern, just filling in adjacent API calls the existing table/partition handlers don't yet make.

### Out of scope

- A brand-new, separate MCP server. That was the original shape of this proposal; it's explicitly dropped here because it would duplicate the 18 Glue tools `aws-dataprocessing-mcp-server` already ships.
- Delta Lake or Apache Hudi *write* support (create/update tables in those formats) — detection only; this server does not gain the ability to write Delta/Hudi tables.
- Reading Iceberg metadata/manifest files directly from S3 — `get-iceberg-table-info` surfaces what's already in Glue's `Table` response; deeper Iceberg introspection belongs to `s3-tables-mcp-server`/PyIceberg-based tooling, not this server.
- Any changes to EMR or Athena tools in this server — out of scope for this RFC.
- Fixing the `get-job-run` vs. `get-job-runs` sensitive-data-gating inconsistency noticed during investigation (the singular operation is gated behind `--allow-sensitive-data-access`, the plural is not, despite both returning `ErrorMessage`/`Arguments` fields) — worth its own follow-up issue, not bundled into this one.

### Potential challenges

1. **Format-detection false negatives/positives.** Delta and Hudi detection relies on property-key conventions (`delta.*`, `hoodie.*`) rather than a canonical field, so some tables may resolve to `UNKNOWN` rather than a wrong answer — that's the intended fail-safe, but it means detection coverage will be incomplete for edge-case table configurations, and should be documented as best-effort.
2. **Backward compatibility of adding operations to already-shipped tools.** `manage_aws_glue_tables` and `manage_aws_glue_partitions` are live, versioned tools; adding new `operation` string values must not change behavior for any existing operation value, and needs test coverage proving existing operations are untouched.
3. **IAM permission surface growth.** Data Quality and table-version/partition-index operations need new `glue:*` permissions added to this server's README IAM policy tables (both read-only and write policies) — easy to do, easy to forget.
4. **Data Quality write operations under `--allow-write`.** `create-ruleset`/`update-ruleset`/`delete-ruleset`/`start-ruleset-evaluation-run` need the same write-gating discipline as every other mutating operation in this server; ruleset evaluation runs can also incur cost/runtime on the caller's account, worth calling out in tool docstrings.
5. **New handler file vs. extending `data_catalog_handler.py`.** `data_catalog_handler.py` is already large (7 tools); whether Data Quality gets its own `data_quality_handler.py` (consistent with how crawlers and commons got split out) or is added inline is an implementation decision for the PR, not this RFC.

### Dependencies and Integrations

- **boto3** Glue API methods listed above — all already-available Glue API calls, no new AWS service dependency.
- Existing `aws_dataprocessing_mcp_server` internal conventions: `BaseHandler`, `utils/aws_helper.py`, `utils/consts.py`, `models/data_catalog_models.py` (where `DataQualityResult` already lives, unused).
- No dependency on the abandoned `aws-glue-catalog-mcp-server` idea — this RFC supersedes it entirely.

### Alternative solutions

- **Ship the original standalone `aws-glue-catalog-mcp-server`.** Rejected after investigation: 14 of its ~22 proposed tools would have duplicated existing `aws-dataprocessing-mcp-server` tools under different names, which would confuse users choosing between two servers for the same job and would likely be closed by maintainers as duplicative.
- **Do nothing / leave the gaps as-is.** Rejected: the Data Quality gap in particular is not just a missing feature but an accuracy problem — `aws-dataprocessing-mcp-server`'s own README already advertises "data quality validation" as a supported capability, which is not currently true.
- **File four separate small issues instead of one RFC.** Considered, but the four gaps share a root cause (Glue Data Catalog API coverage stopped short of these four areas) and a common design question (mega-tool-with-operations vs. new standalone tool for Data Quality), so reviewing them together seemed more useful than four disconnected threads.

---

**Author:** Dipayan Das ([@dipayanthedata](https://github.com/dipayanthedata)) — AWS Community Builder

---

**Disclaimer**: We value your time and bandwidth. As such, any pull requests created on non-triaged issues might not be successful.

Metadata information for admin purposes, please leave them empty.

* RFC PR:
* Approved by: ''
* Reviewed by: ''
