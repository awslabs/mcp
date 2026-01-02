# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Redshift MCP Server Pydantic models."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict, Optional


class RedshiftCluster(BaseModel):
    """Information about a Redshift cluster or serverless workgroup."""

    identifier: str = Field(..., description='Unique identifier for the cluster/workgroup')
    type: str = Field(..., description='Type of cluster (provisioned or serverless)')
    status: str = Field(..., description='Current status of the cluster')
    database_name: str = Field(..., description='Default database name')
    endpoint: Optional[str] = Field(None, description='Connection endpoint')
    port: Optional[int] = Field(None, description='Connection port')
    vpc_id: Optional[str] = Field(None, description='VPC ID where the cluster resides')
    node_type: Optional[str] = Field(None, description='Node type (provisioned only)')
    number_of_nodes: Optional[int] = Field(None, description='Number of nodes (provisioned only)')
    creation_time: Optional[datetime] = Field(None, description='When the cluster was created')
    master_username: Optional[str] = Field(None, description='Master username for the cluster')
    publicly_accessible: Optional[bool] = Field(None, description='Whether publicly accessible')
    encrypted: Optional[bool] = Field(None, description='Whether the cluster is encrypted')
    tags: Optional[Dict[str, str]] = Field(
        default_factory=dict, description='Tags associated with the cluster'
    )


class RedshiftDatabase(BaseModel):
    """Information about a database in a Redshift cluster.

    Based on the SVV_REDSHIFT_DATABASES system view.
    """

    database_name: str = Field(..., description='The name of the database')
    database_owner: Optional[int] = Field(None, description='The database owner user ID')
    database_type: Optional[str] = Field(
        None, description='The type of database (local or shared)'
    )
    database_acl: Optional[str] = Field(
        None, description='Access control information (for internal use)'
    )
    database_options: Optional[str] = Field(None, description='The properties of the database')
    database_isolation_level: Optional[str] = Field(
        None,
        description='The isolation level of the database (Snapshot Isolation or Serializable)',
    )


class RedshiftSchema(BaseModel):
    """Information about a schema in a Redshift database.

    Based on the SVV_ALL_SCHEMAS system view.
    """

    database_name: str = Field(..., description='The name of the database where the schema exists')
    schema_name: str = Field(..., description='The name of the schema')
    schema_owner: Optional[int] = Field(None, description='The user ID of the schema owner')
    schema_type: Optional[str] = Field(
        None, description='The type of the schema (external, local, or shared)'
    )
    schema_acl: Optional[str] = Field(
        None, description='The permissions for the specified user or user group for the schema'
    )
    source_database: Optional[str] = Field(
        None, description='The name of the source database for external schema'
    )
    schema_option: Optional[str] = Field(
        None, description='The options of the schema (external schema attribute)'
    )


class RedshiftTable(BaseModel):
    """Information about a table in a Redshift database.

    Based on the SVV_ALL_TABLES system view.
    """

    database_name: str = Field(..., description='The name of the database where the table exists')
    schema_name: str = Field(..., description='The schema name for the table')
    table_name: str = Field(..., description='The name of the table')
    table_acl: Optional[str] = Field(
        None, description='The permissions for the specified user or user group for the table'
    )
    table_type: Optional[str] = Field(
        None,
        description='The type of the table (views, base tables, external tables, shared tables)',
    )
    remarks: Optional[str] = Field(None, description='Remarks about the table')


class RedshiftColumn(BaseModel):
    """Information about a column in a Redshift table.

    Based on the SVV_ALL_COLUMNS system view.
    """

    database_name: str = Field(..., description='The name of the database')
    schema_name: str = Field(..., description='The name of the schema')
    table_name: str = Field(..., description='The name of the table')
    column_name: str = Field(..., description='The name of the column')
    ordinal_position: Optional[int] = Field(
        None, description='The position of the column in the table'
    )
    column_default: Optional[str] = Field(None, description='The default value of the column')
    is_nullable: Optional[str] = Field(
        None, description='Whether the column is nullable (yes or no)'
    )
    data_type: Optional[str] = Field(None, description='The data type of the column')
    character_maximum_length: Optional[int] = Field(
        None, description='The maximum number of characters in the column'
    )
    numeric_precision: Optional[int] = Field(None, description='The numeric precision')
    numeric_scale: Optional[int] = Field(None, description='The numeric scale')
    remarks: Optional[str] = Field(None, description='Remarks about the column')


class QueryResult(BaseModel):
    """Result of a SQL query execution."""

    columns: list[str] = Field(..., description='List of column names in the result set')
    rows: list[list] = Field(..., description='List of rows, where each row is a list of values')
    row_count: int = Field(..., description='Number of rows returned')
    execution_time_ms: Optional[int] = Field(
        None, description='Query execution time in milliseconds'
    )
    query_id: str = Field(..., description='Unique identifier for the query execution')


class TableColumnDesign(BaseModel):
    """Column design information from pg_table_def system table."""

    column_name: str = Field(..., description='Column name')
    data_type: str = Field(..., description='Column data type')
    encoding: Optional[str] = Field(None, description='Compression encoding')
    distkey: bool = Field(..., description='Whether this column is the distribution key')
    sortkey: int = Field(
        ..., description='Sort key position (0 if not a sort key, 1+ for position)'
    )
    notnull: bool = Field(..., description='Whether the column has NOT NULL constraint')


class TableDesign(BaseModel):
    """Table design information from pg_table_def system table.

    This information helps distinguish between:
    - Runtime sort operations in EXPLAIN (Sort Key: column_name)
    - Actual table SORTKEY configuration (sortkey > 0 in pg_table_def)

    ## Usage for Optimization Analysis

    **Identifying Missing SORTKEY:**
    - EXPLAIN shows "Sort Key: price" + TableDesign shows sortkey=0 for price column
      → Table lacks SORTKEY, runtime sort required
      → Recommendation: ALTER TABLE ADD SORTKEY(price)

    **Verifying DISTKEY Alignment:**
    - EXPLAIN shows "DS_DIST_INNER" on join + TableDesign shows different distkey columns
      → Tables not co-located, redistribution required
      → Recommendation: Align DISTKEY on join columns

    **Distribution Style Analysis:**
    - diststyle='EVEN' + frequent joins shown in EXPLAIN
      → Consider KEY distribution on join column
    - diststyle='KEY' but no column has distkey=true
      → Investigate distribution key configuration issue
    """

    schema_name: str = Field(..., description='Schema name')
    table_name: str = Field(..., description='Table name')
    diststyle: str = Field(..., description='Distribution style (KEY, EVEN, ALL, AUTO)')
    columns: list[TableColumnDesign] = Field(
        ..., description='Column design information ordered by sortkey DESC'
    )


class QueryPlanNode(BaseModel):
    """Individual node in the query execution plan tree.

    Represents a single operation in the query execution plan with its relationships,
    costs, and metadata. Redshift does not use indexes - instead, performance depends
    on proper DISTKEY (distribution key) and SORTKEY (sort key) configuration.

    Key optimization areas to check:
    - Sequential scans on large tables may benefit from SORTKEY
    - Join operations may benefit from matching DISTKEY on join columns
    - Distribution type (DS_DIST_*) indicates data movement patterns
    - High costs often indicate need for DISTKEY/SORTKEY optimization

    ## Table Maintenance Recommendations

    **VACUUM Operations:**
    - High scan costs with unsorted data → Check SVV_TABLE_INFO.vacuum_sort_benefit
    - If vacuum_sort_benefit > 20%, recommend VACUUM SORT ONLY or VACUUM RECLUSTER
    - Ghost rows from DELETEs → Recommend VACUUM DELETE to reclaim space
    - Large unsorted regions → Consider VACUUM FULL (sorts + deletes)
    - Maintenance windows → Use VACUUM BOOST for priority processing
    - Note: Redshift auto-vacuums in background, manual vacuum for critical cases

    **ANALYZE Statistics:**
    - Stale statistics → Check PG_STATISTIC_INDICATOR for rows changed
    - Recommend ANALYZE after large data loads or schema changes
    - Use ANALYZE PREDICATE COLUMNS for efficiency (only frequently queried columns)
    - Auto-analyze runs in background but can be toggled via auto_analyze parameter

    ## Distribution Optimization

    **Distribution Patterns (distribution_type field):**
    - DS_BCAST_INNER → Large table broadcast, expensive operation
      * Recommend: Change to KEY distribution on join columns to co-locate data
    - DS_DIST_INNER → Redistributing inner table based on join keys
      * Check if DISTKEY matches join columns, if not recommend changing DISTKEY
    - DS_DIST_NONE → Optimal! No redistribution needed (data already co-located)
    - DS_DIST_ALL_INNER → Broadcasting entire inner table to all nodes

    **Data Skew Detection:**
    - Query SVV_TABLE_INFO.skew_rows for uneven distribution
    - Skew > 10% → Recommend different DISTKEY with higher cardinality
    - Check SVL_QUERY_REPORT for slice-level processing imbalance

    ## Join Optimization

    **Hash Join → Merge Join Conversion:**
    - Hash Join present with high cost → Check if Merge Join possible:
      * Verify join columns are DISTKEY (co-located data across nodes)
      * Verify join columns are SORTKEY (pre-sorted within nodes)
      * If both true, data is optimally positioned for merge join
    - Nested Loop present → Likely indicates cross-join (missing join condition)
      * Recommend adding explicit join conditions to avoid Cartesian product

    ## Memory and Resource Issues

    **Disk-Based Operations:**
    - Check SVL_QUERY_SUMMARY.is_diskbased for disk spills
    - If true → Query exceeded allocated memory, recommend:
      * Temporarily increase wlm_query_slot_count for more memory
      * Review WLM queue configuration for adequate memory allocation

    **Query Pattern Issues:**
    - High bytes relative to rows → Too many columns selected, recommend:
      * Select only necessary columns
      * Review if all columns in SELECT are needed
    - High SCAN rows vs low RETURN rows → Predicate insufficiently restrictive
      * Recommend adding WHERE clauses or making existing predicates more selective

    ## Alert-Based Detection

    **System Catalog Views for Automated Detection:**
    - STL_ALERT_EVENT_LOG → Check for ghost rows, nested loops, broadcast alerts
    - SVV_TABLE_INFO → Check vacuum_sort_benefit, unsorted%, stats_off columns
    - SVL_QUERY_SUMMARY → Check for disk-based operations, high maxtime steps
    - PG_STATISTIC_INDICATOR → Track rows inserted/deleted since last ANALYZE

    ## Additional Performance Factors

    **Data Compression:**
    - Redshift uses columnar storage with adaptive compression encodings
    - Compression reduces storage, disk I/O, and improves query performance
    - Compressed data is read into memory then uncompressed during query execution
    - Recommendation: Use COPY with COMPUPDATE ON or CREATE TABLE with ENCODE AUTO
    - AUTO encoding analyzes data and applies optimal compression per column
    - Benefit: More data in memory = more memory for query processing

    **Short Query Acceleration (SQA):**
    - Prioritizes short-running queries over long-running queries
    - Runs in dedicated space, not stuck behind long queries in WLM queues
    - Only applies to queries in user-defined queues
    - When enabled: Short queries start faster, long queries don't contend for slots
    - Benefit: Can reduce or eliminate WLM queues dedicated to short queries
    - Allows configuring WLM with fewer query slots, improving throughput

    **Code Compilation and Caching:**
    - Redshift generates and compiles code for each query execution plan
    - First-time queries have compilation overhead - rerun to see typical performance
    - Compiled code segments cached locally on cluster and in unlimited remote cache
    - Cache persists after cluster reboots
    - Subsequent runs skip compilation phase and run much faster
    - Serverless compilation service scales beyond cluster compute resources
    - Code recompiled after version upgrades (cache not compatible across versions)
    - Recommendation: Always run queries twice to get accurate performance baseline

    **Materialized Views:**
    - Pre-computed query results stored as table-like structures
    - Query optimizer automatically rewrites queries to use materialized views
    - Significant performance improvement for complex aggregations and joins
    - Auto-refresh keeps data current or manual refresh for control
    - Consider for: Repeated complex queries, dashboard queries, aggregation queries
    - Trade-off: Storage space vs query performance improvement

    **Cluster Sizing and Node Architecture:**
    - Node types: RA3 (managed storage), DC2 (compute optimized), DS2 (legacy)
    - Each compute node divided into slices for parallel processing
    - More nodes = more slices = faster parallel query execution
    - More nodes also = higher cost
    - Balance: Find optimal cost vs performance for your workload
    - Slices run portions of query concurrently across the cluster
    - Data distributed across slices according to table's distribution style

    Note: Redshift does NOT support traditional database indexes. Do not suggest
    index creation. Focus on DISTKEY, SORTKEY, VACUUM, ANALYZE, and distribution styles.
    """

    node_id: int = Field(..., description='Unique identifier for this node in the plan')
    parent_node_id: Optional[int] = Field(None, description='ID of parent node, null for root')
    level: int = Field(..., description='Depth in the execution tree (0 = root)')
    operation: str = Field(..., description='Operation type (e.g., Hash Join, Seq Scan)')
    relation_name: Optional[str] = Field(
        None, description='Table, view, or materialized view name'
    )
    prefix: Optional[str] = Field(None, description='Query execution prefix (e.g., XN)')
    distribution_type: Optional[str] = Field(
        None,
        description='Data distribution method (DS_BCAST_INNER, DS_DIST_NONE, DS_DIST_INNER, etc.)',
    )
    cost_startup: Optional[float] = Field(None, description='Relative cost to return first row')
    cost_total: Optional[float] = Field(
        None, description='Relative cost to complete the operation'
    )
    rows: Optional[int] = Field(None, description='Estimated number of rows')
    width: Optional[int] = Field(None, description='Estimated average row width in bytes')
    join_condition: Optional[str] = Field(None, description='Join condition if applicable')
    filter_condition: Optional[str] = Field(
        None, description='Filter/WHERE condition if applicable'
    )
    sort_key: Optional[str] = Field(None, description='Sort key information if applicable')
    details: str = Field(..., description='Original EXPLAIN output line')


class ExecutionPlan(BaseModel):
    """Result of an EXPLAIN query execution with structured plan nodes.

    This structured format enables AI assistants to:
    1. Identify performance bottlenecks by analyzing costs
    2. Detect suboptimal distribution patterns
    3. Recommend DISTKEY and SORTKEY optimizations
    4. Understand query execution flow through parent-child relationships

    ## DISPLAYING EXECUTION PLANS TO USERS

    **CRITICAL: Always display the full execution plan with proper indentation to users.**

    When presenting execution plans, use the structured hierarchy to create readable output:

    **Required Display Format:**
    1. Use the `level` field to determine indentation (0 = root, 1 = first indent, etc.)
    2. Indent with 2-3 spaces per level OR use bullet/number hierarchy
    3. Show operation name, costs, and key metadata from each node
    4. Include ALL nodes from the query_plan list - don't truncate
    5. Preserve parent-child relationships using indentation

    **Example Display Pattern:**
    ```
    ### Execution Plan Steps:

    1. XN Limit (cost=1000000016724.67..1000000016724.68 rows=3 width=28)
       - Operation: Limits result to 3 rows
       - Cost: Very low incremental cost since it stops after 3 records

    2. XN Merge (cost=1000000016724.67..1000000017155.81 rows=172456 width=28)
       - Merge Key: saletime
       - Operation: Combines sorted data from multiple nodes
       - Cost: High cost due to sorting 172,456 rows

       3. XN Network (cost=... rows=... width=...)
          - Operation: Send to leader
          - Data Movement: Gathering data from compute nodes

          4. XN Sort (cost=... rows=... width=...)
             - Sort Key: saletime
             - Operation: Sorts all rows by saletime (descending)
    ```

    **Extracting Display Information from QueryPlanNode:**
    - `level`: Determines indentation depth
    - `operation`: Primary operation type (e.g., "Hash Join", "Seq Scan")
    - `prefix`: Query execution prefix (XN, LF) - include in display
    - `relation_name`: Table/view name - important for context
    - `cost_startup` and `cost_total`: Show relative costs
    - `rows`: Number of rows processed - important for understanding scale
    - `distribution_type`: If present (DS_*), indicates data movement
    - `join_condition`, `filter_condition`, `sort_key`: Include when present
    - `details`: Original EXPLAIN line for reference

    **Performance Analysis Section:**
    After displaying the plan, provide analysis covering:
    - High-cost operations and why they're expensive
    - Data movement patterns (distribution types)
    - Optimization opportunities (SORTKEY, DISTKEY recommendations)
    - Table maintenance recommendations if applicable

    ## PERFORMANCE OPTIMIZATION WORKFLOW

    **Step 1: Check Table Health**
    Query SVV_TABLE_INFO for each table in the plan:
    - vacuum_sort_benefit > 20% → Recommend VACUUM SORT ONLY or VACUUM RECLUSTER
    - unsorted > 10% → Recommend VACUUM SORT ONLY
    - stats_off = true → Recommend ANALYZE or ANALYZE PREDICATE COLUMNS
    - skew_rows > 10% → Recommend reviewing DISTKEY choice

    Example query:
    ```sql
    SELECT "table", unsorted, vacuum_sort_benefit, stats_off, skew_rows
    FROM svv_table_info
    WHERE "table" IN ('table1', 'table2')
    ORDER BY vacuum_sort_benefit DESC;
    ```

    **Step 2: Identify Distribution Issues**
    Review distribution_type in QueryPlanNode objects:
    - DS_BCAST_INNER with large row counts → Expensive broadcast operation
      * Check if tables can use KEY distribution on join columns
      * Consider changing smaller dimension tables to ALL distribution
    - DS_DIST_INNER → Data being redistributed during query
      * Verify DISTKEY matches join columns
      * Consider co-locating frequently joined tables on same DISTKEY
    - DS_DIST_NONE → Optimal! Data already co-located, no redistribution needed

    Check for data skew with SVL_QUERY_REPORT:
    ```sql
    SELECT query, segment, step, rows, bytes,
           MAX(rows) OVER (PARTITION BY query, segment, step) as max_rows,
           MIN(rows) OVER (PARTITION BY query, segment, step) as min_rows
    FROM svl_query_report
    WHERE query = <query_id>
    ORDER BY segment, step;
    ```

    **Step 3: Optimize Join Strategy**
    - Hash Join detected → Evaluate if Merge Join is possible:
      * Check if join columns are both DISTKEY (data co-located)
      * Check if join columns are both SORTKEY (data pre-sorted)
      * Query pg_table_def to verify current DISTKEY/SORTKEY settings
    - Nested Loop detected → Look for cross-joins:
      * Review query for missing join conditions
      * Recommend explicit ON/WHERE clauses to avoid Cartesian products

    Example to check table design:
    ```sql
    SELECT tablename, "column", type, distkey, sortkey
    FROM pg_table_def
    WHERE tablename IN ('table1', 'table2')
    ORDER BY tablename, sortkey;
    ```

    **Step 4: Memory and Resource Optimization**
    Query SVL_QUERY_SUMMARY for the execution:
    - is_diskbased = true → Disk spills occurred, query exceeded memory
      * Recommend temporarily increasing wlm_query_slot_count
      * Review WLM configuration for adequate memory per slot
    - High bytes/rows ratio → Too many columns selected
      * Recommend selecting only necessary columns
    - High maxtime in SCAN step → Table scan taking too long
      * Check if WHERE clause uses sort key columns
      * Verify predicates are restrictive enough

    **Step 5: Maintenance Recommendations**
    Based on query patterns and table operations:
    - Recent large DELETEs/UPDATEs → Check STL_ALERT_EVENT_LOG for ghost rows
      * If ghost rows > 5%, recommend VACUUM DELETE
    - After large data loads → Recommend VACUUM FULL if unsorted region is large
    - Schema changes or significant data modifications → Always recommend ANALYZE
    - Production workloads → Consider ANALYZE PREDICATE COLUMNS for efficiency

    Check for alerts:
    ```sql
    SELECT event_time, solution, event, details
    FROM stl_alert_event_log
    WHERE query = <query_id>
    ORDER BY event_time DESC;
    ```

    **Step 6: Monitoring Queries for Tuning**
    Identify queries that need optimization:
    ```sql
    -- Find long-running queries
    SELECT query, trim(querytxt) as query_text,
           datediff(seconds, starttime, endtime) as duration_sec
    FROM svl_qlog
    WHERE userid > 1
    ORDER BY duration_sec DESC
    LIMIT 10;

    -- Check for queries with nested loops
    SELECT query, substring(text, 1, 100) as query_text
    FROM svl_statementtext
    WHERE sequence = 0
      AND query IN (
        SELECT DISTINCT query FROM stl_alert_event_log
        WHERE event = 'Nested Loop Join'
      );
    ```

    ## Distribution Style Selection Guide

    **KEY Distribution:**
    - Use for large fact tables
    - Choose DISTKEY that matches the most common join column
    - Ideal for tables frequently joined on the same column
    - DISTKEY should have high cardinality to avoid skew

    **ALL Distribution:**
    - Use for small dimension tables (< few million rows)
    - Table is fully replicated to all nodes
    - Eliminates redistribution during joins
    - Trade-off: Increases storage and load times

    **EVEN Distribution:**
    - Use when table is not frequently joined
    - Distributes rows evenly in round-robin fashion
    - Good for tables with no obvious DISTKEY candidate

    **AUTO Distribution:**
    - Let Redshift choose based on table size and usage patterns
    - Recommended for new tables when distribution pattern is uncertain
    - Redshift can change distribution automatically as usage evolves

    ## Sort Key Selection Guide

    **Compound Sort Keys:**
    - Most common type, sorts by columns in order specified
    - Best for queries filtering on sort key prefix columns
    - Example: SORTKEY(date, category) optimizes WHERE date = X AND category = Y

    **Interleaved Sort Keys:**
    - Equal weight to all sort key columns
    - Best when queries filter on different combinations of sort key columns
    - Requires VACUUM REINDEX to maintain performance
    - Consider compound sort keys first due to lower maintenance

    Important: Redshift does NOT use indexes. Performance tuning focuses on:
    - DISTKEY: Determines how data is distributed across nodes (KEY, ALL, EVEN, AUTO)
    - SORTKEY: Determines physical sort order within each node (compound, interleaved)
    - VACUUM: Reclaim space and re-sort rows (FULL, SORT ONLY, DELETE ONLY, RECLUSTER, BOOST)
    - ANALYZE: Update query planner statistics (use PREDICATE COLUMNS for efficiency)

    Never suggest creating indexes - this is not supported in Redshift.
    """

    query_id: str = Field(..., description='Unique identifier for the explain execution')
    explained_query: str = Field(..., description='Original SQL query that was explained')
    execution_time_ms: Optional[int] = Field(
        None, description='Time taken to generate the plan in milliseconds'
    )
    raw_plan_text: list[str] = Field(
        ..., description='Raw EXPLAIN output from Data API (stripped of indentation/metadata)'
    )
    formatted_plan_text: list[str] = Field(
        ..., description='Reconstructed EXPLAIN output with proper indentation and metadata'
    )
    query_plan: list[QueryPlanNode] = Field(
        ..., description='Structured execution plan as a list of nodes with hierarchy'
    )
    plan_format: str = Field(
        'structured', description='Format of the plan (structured with parsed nodes)'
    )
    table_designs: Dict[str, TableDesign] = Field(
        default_factory=dict,
        description='Table design information from pg_table_def for tables in the execution plan. '
        'Key is "schema.table" format. Use this to verify if runtime Sort operations in EXPLAIN '
        'indicate missing table SORTKEY, or if data redistribution indicates DISTKEY misalignment.',
    )
