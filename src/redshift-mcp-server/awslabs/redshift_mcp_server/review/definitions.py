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

"""Definition of evaluation signals and recommendations."""

RECOMMENDATIONS: dict[str, str] = {
    'REC_001': """\
## For additional scalability, migrate to RG instances or serverless

RG instances provide the latest generation of compute and managed storage with independent scaling. Migrating from DC, DS, or RA3 node types to RG allows you to benefit from improved price-performance, and leverages automatic data tiering between local SSD and S3-backed managed storage.

See also:
- https://aws.amazon.com/redshift/features/rg/
- https://docs.aws.amazon.com/redshift/latest/mgmt/managing-cluster-considerations.html#rs-upgrading-to-ra3
- https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-whatis.html
- https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-migration.html
""",
    'REC_002': """\
## For busy clusters, schedule a VACUUM DELETE

Amazon Redshift automatically performs a DELETE ONLY vacuum in the background, so you rarely, if ever, need to run a DELETE ONLY vacuum. However, this operation only runs when the cluster is idle. If your cluster is busy, you should schedule this operation to minimize I/O operations. A VACUUM DELETE reclaims disk space occupied by rows that were marked for deletion by previous UPDATE and DELETE operations, and compacts the table to free up the consumed space. A DELETE ONLY vacuum operation doesn't sort table data.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/t_Reclaiming_storage_space202.html#automatic-table-delete
""",
    'REC_003': """\
## For busy clusters, schedule ANALYZE commands

Stale or missing table statistics reduce sort key effectiveness and may cause the optimizer not to use the optimal query path for the affected queries. A higher value of the stats_off column in SVV_TABLE_INFO means that statistics is more out of date hence it is recommended to check tables with >= 10. While Redshift automatically analyzes your data, this occurs when the cluster is not busy. If you have a busy cluster or if there are significant write operations/changes on the table (e.g. DML operations) and access to the data is immediately required, explicitly execute or schedule ANALYZE commands. Consider ANALYZE PREDICATE COLUMNS or sp_analyze_minimal if you have a wide table (100s of columns) for a faster execution.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/t_Analyzing_tables.html
""",
    'REC_004': """\
## If you are running out of storage or to reduce I/O overhead, review compression encodings

Compression is a column-level operation that reduces the size of data when it is stored. Compression conserves storage space and reduces the size of data that is read from storage, which reduces the amount of disk I/O and therefore improves query performance. As a best practice, leverage AZ64 for numeric and date data types and ZSTD for character data types where possible or use ENCODE AUTO to automatically manage the compression encoding for all columns in the table. For monitoring actions of automatic table optimization, SVV_ALTER_TABLE_RECOMMENDATIONS records the current Amazon Redshift Advisor recommendations for tables while SVL_AUTO_WORKER_ACTION shows an audit log of all the actions taken by Amazon Redshift, and the previous state of the table. To change the encoding of the table to AUTO: ALTER TABLE [table_name] ALTER ENCODE AUTO;

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/t_Compressing_data_on_disk.html
- https://docs.aws.amazon.com/redshift/latest/dg/t_Verifying_data_compression.html
""",
    'REC_005': """\
## If you are running out of storage or memory, add more compute nodes using resize

When using node types like DC2, you may run into situations where you are out of storage. In some cases, both DC2 and RA3, where you see heavy disk spill, resizing your cluster can make more memory available and speed up query execution.

See also:
- https://docs.aws.amazon.com/redshift/latest/mgmt/managing-cluster-operations.html#elastic-resize
- https://aws.amazon.com/blogs/big-data/accelerate-resize-and-encryption-of-amazon-redshift-clusters-with-faster-classic-resize/
""",
    'REC_006': """\
## Unload infrequently accessed data to S3 and query using Redshift Spectrum

Redshift Spectrum allows you to query exabytes of data in your Amazon S3 data lake, without loading or moving objects. Infrequently accessed data (also known as COLD data) can reside or be offloaded in Amazon S3 and be queried in Amazon Redshift using Redshift Spectrum. You can also define a spectrum usage limit either as a daily, weekly, or monthly usage limit and define actions that Amazon Redshift automatically takes if the limits are reached. The action taken could be logging the event to a system table, creating an alert for notification, or disabling the feature.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/c-getting-started-using-spectrum.html
- https://docs.aws.amazon.com/redshift/latest/dg/tutorial-query-nested-data.html
- https://aws.amazon.com/blogs/big-data/10-best-practices-for-amazon-redshift-spectrum/
- https://aws.amazon.com/blogs/big-data/manage-and-control-your-cost-with-amazon-redshift-concurrency-scaling-and-spectrum/
- https://aws.amazon.com/blogs/big-data/working-with-nested-data-types-using-amazon-redshift-spectrum/
""",
    'REC_007': """\
## To improve query performance, choose the best sort key

For large tables, adding a sort key can speed up queries with predicates. Review commonly filtered fields and add a sort key: ALTER TABLE [table_name] ALTER SORTKEY ([column1], [columnN]). For small tables (less than 5 million rows), sort keys are not effective and will add maintenance and storage overhead: ALTER TABLE [table_name] ALTER SORTKEY NONE; For unknown table sizes or access patterns, you can set the sort key to AUTO which allows Redshift to define the optimal sort key: ALTER TABLE [table_name] ALTER SORTKEY AUTO;

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-sort-key.html
""",
    'REC_008': """\
## To improve query performance, choose the best distribution style

Heavy skew (where the ratio of the number of rows on a slice is more than 4x of another slice) can cause queries to perform slower as they are waiting on the compute node with the most data to complete before returning the result set. If the first node is skewed, this may be due to using a distribution key containing nulls. To change the column used as a distribution key: ALTER TABLE [table_name] ALTER DISTSTYLE KEY DISTKEY [column_name]; For small tables (< 5 million rows) e.g. reference or dimension tables that are frequently used in JOINS consider an ALL distribution style. To manage the distribution style automatically, create your tables with DISTSTYLE AUTO. Amazon Redshift initially assigns ALL distribution to a small table, then changes to EVEN distribution when the table grows larger. A low skew value indicates that table data is properly distributed. If a table has a skew value of 4.00 or higher, consider modifying its data distribution style.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-best-dist-key.html
- https://docs.aws.amazon.com/redshift/latest/dg/t_Creating_tables.html#ato-enabling
- https://aws.amazon.com/blogs/big-data/amazon-redshift-engineerings-advanced-table-design-playbook-distribution-styles-and-distribution-keys/
- https://aws.amazon.com/blogs/big-data/automate-your-amazon-redshift-performance-tuning-with-automatic-table-optimization/
""",
    'REC_009': """\
## To improve query performance, remove nested loop joins (cross-joins)

Review queries that make use of cross-joins and remove them if possible by adding a join condition.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/query-performance-improvement-opportunities.html#nested-loop
""",
    'REC_010': """\
## To improve query performance, remove the encoding on the first column of a sort key

It is a best practice to not encode the first column of a sort key for optimal query performance. Using ENCODE AUTO to automatically manage the compression encoding for all columns in the table also ensures this. To change the encoding of the table to AUTO, the following command can be executed: ALTER TABLE [table_name] ALTER ENCODE AUTO;

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/t_Verifying_data_compression.html
""",
    'REC_011': """\
## To optimize memory consumption and avoid disk spill, reduce varchar fields to be inline with their max length

Use caution when setting a large length on character type fields such as VARCHAR. When allocating memory for queries using these fields, Amazon Redshift will allocate based on the maximum values and queries are more likely to spill to disk. To change the length of the column, the following command can be executed: ALTER TABLE [table_name] ALTER COLUMN [column_name] TYPE varchar([size])

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-smallest-column-size.html
""",
    'REC_012': """\
## To save cost, remove extra compute nodes using elastic or classic resize

You may have more compute than you need. If you can reduce the size of your cluster and maintain your SLAs, you may be able to save money. In addition, enable the concurrency scaling feature and leverage the 1 hour free credit per day on a given WLM queue. Apply the necessary concurrency scaling usage limits. Use of concurrency scaling allows the cluster to handle spiky compute needs and allow for queries in WLM queues in which it is enabled to get consistent performance.

See also:
- https://docs.aws.amazon.com/redshift/latest/mgmt/managing-cluster-operations.html#elastic-resize
- https://docs.aws.amazon.com/redshift/latest/dg/concurrency-scaling-queues.html
- https://docs.aws.amazon.com/redshift/latest/mgmt/managing-cluster-usage-limits.html
- https://aws.amazon.com/blogs/big-data/accelerate-resize-and-encryption-of-amazon-redshift-clusters-with-faster-classic-resize/
""",
    'REC_013': """\
## To improve query performance, ensure large tables with a sort key are vacuumed

Tables which contain a sort key but have not been vacuumed will not benefit from the sort key. While Auto Vacuum should optimize most tables, in busy clusters, customers should schedule the VACUUM SORT RECLUSTER operation either as part of the regular data ingestion / transformation workload (especially those that affect a large number of rows) or as part of a recurring maintenance activity (e.g. weekly / monthly) based on the vacuum_sort_benefit column in SVV_TABLE_INFO. Use the DEEP COPY approach if the table does not need to be accessible for writes. A deep copy is much faster than a vacuum. The trade off is that you should not make concurrent updates during a deep copy operation unless you can track it and move the delta updates into the new table after the process has completed.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/r_VACUUM_command.html
- https://docs.aws.amazon.com/redshift/latest/dg/performing-a-deep-copy.html
""",
    'REC_014': """\
## To improve query performance and reduce maintenance overhead, replace Interleaved Sort keys with Materialized Views

While interleaved sort keys may provide some benefit for tables with multiple access patterns, Materialized Views (MVs) are a newer strategy to optimize for performance in similar situations. MVs can be used to support not only different sorting strategies, but also calculated fields, different distribution strategies, and pre-aggregated results. Also, tables with an interleaved sort key are not eligible for concurrency scaling and data sharing. If your use case still requires interleaved sort keys, keep in mind a VACUUM REINDEX is required to take advantage of it, but it is an expensive operation and in many cases the performance benefit is not worth the additional maintenance effort.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/materialized-view-overview.html
- https://docs.aws.amazon.com/redshift/latest/dg/r_VACUUM_command.html#vacuum-reindex
""",
    'REC_015': """\
## To maximize system throughput and use resources most effectively, set up automatic WLM

With automatic workload management (autoWLM), Amazon Redshift manages query concurrency and memory allocation. Automatic WLM determines the amount of resources that queries need, and adjusts the concurrency based on the workload. When queries requiring large amounts of resources are in the system (for example, hash joins between large tables), the concurrency is lower. When lighter queries (such as inserts, deletes, scans, or simple aggregations) are submitted, concurrency is higher.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/automatic-wlm.html
- https://aws.amazon.com/blogs/big-data/benchmarking-the-performance-of-the-new-auto-wlm-with-adaptive-concurrency-in-amazon-redshift/
""",
    'REC_016': """\
## Re-allocate your memory distribution to add up to 100%

When using manual WLM total memory allocation should equal 100%. Allocating less than 100% may result in unpredictable query performance and/or inefficient use of cluster resources.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/cm-c-defining-query-queues.html
- https://docs.aws.amazon.com/redshift/latest/dg/cm-c-defining-query-queues.html#wlm-memory-percent
""",
    'REC_017': """\
## To improve query performance, configure no more than 20 WLM slots

When using manual WLM, high slot counts can result in too little memory being allocated to each query and results spilling to disk which may affect the query performance and having a lower query throughput. When you use lower concurrency, query throughput is increased and overall system performance is improved for most workloads.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/cm-c-defining-query-queues.html
- https://docs.aws.amazon.com/redshift/latest/dg/cm-c-defining-query-queues.html#cm-c-defining-query-queues-concurrency-level
""",
    'REC_018': """\
## To have better visibility on resource usage by workload and optimize resource allocation, create separate query queues for each workload

When you define multiple query queues, you can route queries to the appropriate queues at runtime. For example query queues can be defined for each type of workload: BI / Dashboard workload, ETL / Data Ingestion workload, Data Science workload, Adhoc workload, Application workload.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/cm-c-wlm-queue-assignment-rules.html
""",
    'REC_019': """\
## For additional scalability, enable the concurrency scaling

Use of concurrency scaling allows the cluster to handle spiky compute needs and allow for queries in WLM queues in which it is enabled to get consistent performance. Concurrency scaling is available 1 hour free per day. Additionally usage limits can be applied to manage costs.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/concurrency-scaling.html
- https://docs.aws.amazon.com/redshift/latest/dg/concurrency-scaling-queues.html
- https://docs.aws.amazon.com/redshift/latest/mgmt/managing-cluster-usage-limits.html
- https://aws.amazon.com/blogs/big-data/manage-and-control-your-cost-with-amazon-redshift-concurrency-scaling-and-spectrum/
- https://www.youtube.com/watch?v=-2yQsI9xJKQ
""",
    'REC_020': """\
## For additional scalability, enable short query acceleration

If you enable SQA, you can reduce or eliminate workload management (WLM) queues that are dedicated to running short queries. Amazon Redshift uses a machine learning algorithm to analyze each eligible query and predict the query's execution time. By default, WLM dynamically assigns a value for the SQA maximum runtime based on analysis of your cluster's workload. Alternatively, you can specify a fixed value of 1 to 20 seconds.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/wlm-short-query-acceleration.html
""",
    'REC_021': """\
## To ensure queries get resources based on importance, set priorities for each WLM queue

Not all queries are of equal importance, and often performance of one workload or set of users might be more important. When auto WLM is enabled, you can define the relative importance of queries in a workload by setting a priority value. The priority is specified for a queue and inherited by all queries associated with the queue. Amazon Redshift uses the priority when letting queries into the system, and to determine the amount of resources allocated to a query.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/query-priority.html
""",
    'REC_022': """\
## To set query performance boundaries on workloads, add QMR rules

Query monitoring rules (QMR) define metrics-based performance boundaries for WLM queues and specify what action to take when a query goes beyond those boundaries. For example, to track poorly designed queries, you might have a rule that logs queries that contain nested loops or execute for more than 2 hours. You can define up to 25 rules for each queue, with a limit of 25 rules for all queues. You can start with Query monitoring rules templates. WLM evaluates metrics every 10 seconds. If more than one rule is triggered during the same period, WLM initiates the most severe action: abort, then hop, then log. The most common metrics where QMR can protect your system include: query_execution_time (identifies sub-optimal table or query design), query_temp_blocks_to_disk (identifies queries using more than available memory which write intermediate results to disk), spectrum_scan_size_mb / spectrum_scan_row_count (a large scan may mean there is no partition pruning applied), and nested_loop_join_row_count (joins without a join condition that result in the Cartesian product of two tables).

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/cm-c-wlm-query-monitoring-rules.html
- https://docs.aws.amazon.com/redshift/latest/dg/cm-c-wlm-query-monitoring-rules.html#cm-c-wlm-query-monitoring-templates
- https://docs.aws.amazon.com/redshift/latest/dg/r_STL_WLM_RULE_ACTION.html

Review STL_WLM_RULE_ACTION to identify queries that triggered QMR rules and retrieve the offending queries for further analysis.
""",
    'REC_023': """\
## Increase load performance by optimizing COPY operations

Amazon Redshift can automatically load in parallel from multiple compressed data files. This divides the workload among the nodes in your cluster. However, if you use multiple concurrent COPY commands to load one table from multiple files, Amazon Redshift performs a serialized load which is slower than loading them using one operation. Optimal COPY performance can be achieved through a file count that is a multiple of the number of node slices. For optimum parallelism, the ideal file size is 1 to 125 MB after compression.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/t_Loading-data-from-S3.html
- https://docs.aws.amazon.com/redshift/latest/dg/c_loading-data-best-practices.html
- https://aws.amazon.com/blogs/big-data/part-1-introducing-new-features-for-amazon-redshift-copy/
""",
    'REC_024': """\
## To avoid disk spill, review queries and add predicates to filter tables that participate in joins, even if the predicates apply the same filters

Even though a filter may be redundant, the query planner can skip scanning large numbers of disk blocks when performing a join operation. For example, adding a predicate for sales.saletime to the WHERE clause returns the same result set without the filter because a product will always be sold after it is listed, but Amazon Redshift is able to filter the table before the join step.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/c_designing-queries-best-practices.html
""",
    'REC_026': """\
## For additional scalability, isolate your workloads using data sharing

Amazon Redshift data sharing provides workload isolation by allowing multiple consumers to share data seamlessly without the need to unload and load data. Implementing workload isolation allows for agility, allows sizing of clusters independently, and creates a simple cost charge-back model.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/data_sharing_intro.html
- https://aws.amazon.com/blogs/big-data/amazon-redshift-data-sharing-best-practices-and-considerations/
- https://aws.amazon.com/blogs/big-data/sharing-amazon-redshift-data-securely-across-amazon-redshift-clusters-for-workload-isolation/
- https://aws.amazon.com/blogs/big-data/implementing-multi-tenant-patterns-in-amazon-redshift-using-data-sharing/
- https://aws.amazon.com/blogs/aws/cross-account-data-sharing-for-amazon-redshift/
- https://aws.amazon.com/blogs/big-data/security-considerations-for-amazon-redshift-cross-account-data-sharing/
- https://aws.amazon.com/blogs/big-data/share-data-securely-across-regions-using-amazon-redshift-data-sharing/
""",
    'REC_027': """\
## Increase read performance from Spectrum tables, by optimizing your partitioning strategy

When you partition your data, you can restrict the amount of data that Redshift Spectrum scans by filtering on the partition key. Amazon Redshift Spectrum can take advantage of partition pruning and skip scanning unneeded partitions and files by defining the S3 prefix based on the columns (e.g. transaction_date) frequently used in SQL predicates. A common practice is to partition the data based on time. For example, you might choose to partition by year, month, date, and hour. If you have data coming from multiple sources, you might partition by a data source identifier and date.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/c-spectrum-external-performance.html
- https://docs.aws.amazon.com/redshift/latest/dg/c-spectrum-external-tables.html#c-spectrum-external-tables-partitioning
- https://aws.amazon.com/blogs/big-data/10-best-practices-for-amazon-redshift-spectrum/
""",
    'REC_028': """\
## To improve query performance, redesign the large table to a time series table

If your data has a fixed retention period, you can organize your data as a sequence of time-series tables. In such a sequence, each table is identical but contains data for different time ranges. You can easily remove old data simply by running a DROP TABLE command on the corresponding tables. This approach is much faster than running a large-scale DELETE process and saves you from having to run a subsequent VACUUM process to reclaim space. To hide the fact that the data is stored in different tables, you can create a UNION ALL view. When you delete old data, simply refine your UNION ALL view to remove the dropped tables. Similarly, as you load new time periods into new tables, add the new tables to the view. To signal the optimizer to skip the scan on tables that don't match the query filter, your view definition filters for the date range that corresponds to each table. If your data requires processing of different time ranges, you can follow a similar approach but instead of a time range make use of another criteria for data segregation based on data access pattern such as geography (e.g. region). A sample conversion process: create multiple tables based on how the data needs to be accessed (e.g. by week, month, quarter, geography, account), create a view that consolidates all the time series tables (may include external tables queried using Redshift Spectrum), replace the query on the table with the query on the view. If a query filters on the sort key, the query planner can efficiently skip all the tables that are not used.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-time-series-tables.html
""",
    'REC_029': """\
## Increase load performance by avoiding or minimizing multiple single row insert statements

A data ingestion / loading process that runs a single row insert or multi row insert statement uses only the leader node for each execution and is slow when used to load large amounts of data compared to other data ingestion / loading options like a COPY command which engages compute nodes in parallel. Data compression is also inefficient when you add data only one row or a few rows at a time. Redesign the data ingestion process to replace multiple single row insert statements to either use: COPY command, COPY command with column mapping, ALTER TABLE APPEND, Bulk Insert, or Multi Row Insert.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/c_loading-data-best-practices.html
- https://docs.aws.amazon.com/redshift/latest/dg/t_Updating_tables_with_DML_commands.html
- https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-use-copy.html
- https://docs.aws.amazon.com/redshift/latest/dg/copy-parameters-column-mapping.html#copy-column-list
- https://docs.aws.amazon.com/redshift/latest/dg/r_ALTER_TABLE_APPEND.html
- https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-bulk-inserts.html
- https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-multi-row-inserts.html
""",
    'REC_030': """\
## To improve query performance, create a materialized view to use incremental refresh

A materialized view contains a precomputed result set, based on an SQL query over one or more base tables. Materialized views are especially useful for speeding up queries that are predictable and repeated. Instead of performing resource-intensive queries against large tables (such as aggregates or multiple joins), applications can query a materialized view and retrieve a precomputed result set. From the user standpoint, the query results are returned much faster compared to when retrieving the same data from the base tables. To complete refresh of the materialized views with minimal impact to active workloads in your cluster, create a materialized view that can perform an incremental refresh in order to quickly identify the changes to the data in the base tables since the last refresh and update the data in the materialized view.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/materialized-view-refresh.html
- https://aws.amazon.com/blogs/big-data/speed-up-your-elt-and-bi-queries-with-amazon-redshift-materialized-views/
- https://aws.amazon.com/blogs/big-data/optimize-your-analytical-workloads-using-the-automatic-query-rewrite-feature-of-amazon-redshift-materialized-views/
""",
    'REC_031': """\
## To keep the data accurate and up to date, recreate the materialized view

Due to underlying DDL changes on the base tables used in the materialized view, the materialized view can no longer be refreshed.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/r_SVV_MV_INFO.html
""",
    'REC_033': """\
## To save cost, apply the necessary concurrency scaling usage limit

You can define limits to monitor and control your usage and associated cost of some Amazon Redshift features. You can create daily, weekly, and monthly usage limits, and define actions that Amazon Redshift automatically takes if those limits are reached. Actions include logging an event to a system table, raising alerts with Amazon SNS and Amazon CloudWatch to notify an administrator, and disabling further usage to control costs. A concurrency scaling limit specifies the threshold of the total amount of time used by concurrency scaling in 1-minute increments.

See also:
- https://docs.aws.amazon.com/redshift/latest/mgmt/managing-cluster-usage-limits.html
- https://aws.amazon.com/blogs/big-data/manage-and-control-your-cost-with-amazon-redshift-concurrency-scaling-and-spectrum/
""",
    'REC_034': """\
## To improve query performance, create a materialized view to use incremental refresh in the producer cluster and share the materialized view to the consumer cluster(s)

Materialized views (MVs) provide a powerful route to precompute complex aggregations for use cases where high throughput is needed, and you can directly share a materialized view object via data sharing as well. For materialized views built on tables where there are frequent write operations, it is ideal to create the materialized view object on the producer itself and share the view. This method gives us the opportunity to centralize the management of the view on the producer cluster itself. For slowly changing data tables, you can share the table objects directly and build the materialized view on the shared objects directly on the consumer. This method gives us the flexibility of creating a customized view of data on each consumer according to your use case. This can help optimize the block metadata download and caching times in the data sharing query lifecycle. This also helps in materialized view refreshes because Redshift does not support incremental refresh for MVs built on shared objects.

See also:
- https://aws.amazon.com/blogs/big-data/speed-up-your-elt-and-bi-queries-with-amazon-redshift-materialized-views/
- https://aws.amazon.com/blogs/big-data/amazon-redshift-data-sharing-best-practices-and-considerations/
""",
    'REC_035': """\
## For better price performance, leverage Redshift serverless

Redshift serverless provides the same or better price performance when compared to on demand especially with intermittent workloads. This is possible because of its ability to auto pause and resume so you only pay for the times the cluster is running.

See also:
- https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-serverless.html
- https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-billing.html
- https://www.youtube.com/watch?v=XcRJjXudIf8
- https://www.youtube.com/watch?v=JBPpmMq9OS8
""",
    'REC_036': """\
## To avoid 'connection limit' errors and release unused resources, set idle session timeout and clean up idle sessions when needed

Idle connections consume cluster connection slots and hold resources unnecessarily. Configuring idle session timeouts and periodically cleaning up stale sessions prevents connection limit errors and frees resources for active workloads.

See also:
- https://docs.aws.amazon.com/redshift/latest/mgmt/connecting-drop-issues.html
""",
    'REC_037': """\
## For increased stability, use the 'trailing' track for production workloads

The trailing maintenance track applies cluster patches after they have been validated on the current track for several weeks. Using the trailing track for production clusters reduces the risk of encountering issues from newly released patches.

See also:
- https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-clusters.html#rs-maintenance-tracks
""",
    'REC_038': """\
## To reduce processing skew, perform a classic resize to rebalance your data

Data distribution skew across slices can develop over time, especially after multiple elastic resizes. A classic resize redistributes all data evenly across the new slice configuration, eliminating processing skew and restoring balanced query execution.

See also:
- https://docs.aws.amazon.com/redshift/latest/mgmt/managing-cluster-operations.html#rs-resize-tutorial
""",
    'REC_039': """\
## Ensure materialized views are not stale for data accuracy and query rewrite

A materialized view contains a pre-computed result set, based on an SQL query over one or more base tables. Materialized views are especially useful for speeding up queries that are predictable and repeated. In addition, materialized views can be useful for accessing data using an alternate distribution or sort key. From the user standpoint, they don't have to re-write their queries; the re-writer will determine and use the appropriate MV and the query results are returned much faster compared to when retrieving the same data from the base tables. A stale MV does not have up-to-date data and will not be used by autorewrite.

See also:
- https://docs.aws.amazon.com/redshift/latest/dg/materialized-view-refresh.html
- https://aws.amazon.com/blogs/big-data/speed-up-your-elt-and-bi-queries-with-amazon-redshift-materialized-views/
- https://aws.amazon.com/blogs/big-data/optimize-your-analytical-workloads-using-the-automatic-query-rewrite-feature-of-amazon-redshift-materialized-views/
""",
}


SIGNAL_EVALUATION_SQL: list[tuple[str, str, str]] = [
    (
        'ATOWorkerActions',
        'all',
        """\
-- ATOWorkerActions
WITH data AS (
SELECT "schema" namespace, "table" table_name, alter_table_type, status, alter_from, event_time
FROM (SELECT
    "schema",  "table",  alter_table_type,
    status, trim(alter_from) alter_from, event_time,
    ROW_NUMBER() OVER (PARTITION BY o.table_id, o.alter_table_type ORDER BY event_time DESC) rownum
  FROM SYS_AUTO_TABLE_OPTIMIZATION o
  JOIN SVV_TABLE_INFO t on o.table_id = t.table_id
) ato where rownum = 1
)
-- Signal: column encoding on table is not set to auto
SELECT count(*), 'REC_004'
FROM data
WHERE trim(status) != 'Abort:This table is already the recommended style.' and trim(status) != 'Complete: 100%' AND (alter_table_type='encode')
UNION ALL
-- Signal: distribution style on table is not set to auto
SELECT count(*), 'REC_008'
FROM data
WHERE trim(status) != 'Abort:This table is already the recommended style.' and trim(status) != 'Complete: 100%' AND (alter_table_type='distkey')
UNION ALL
-- Signal: sort key on table is not set to auto
SELECT count(*), 'REC_007'
FROM data
WHERE trim(status) != 'Abort:This table is already the recommended style.' and trim(status) != 'Complete: 100%' AND (alter_table_type='sortkey')
""",
    ),
    (
        'AlterTableRecommendations',
        'all',
        """\
-- AlterTableRecommendations
WITH data AS (
SELECT "database" db,
       "schema" namespace,
       "table" table_name,
       type,
       ddl,
       auto_eligible
FROM SVV_ALTER_TABLE_RECOMMENDATIONS
JOIN SVV_TABLE_INFO using(table_id, database)
)
-- Signal: column encoding recommendation on table is not automatically applied
SELECT count(*), 'REC_004'
FROM data
WHERE type='encode' and auto_eligible='f'
UNION ALL
-- Signal: sort key recommendation on table is not automatically applied
SELECT count(*), 'REC_007'
FROM data
WHERE type='sortkey' and auto_eligible='f'
UNION ALL
-- Signal: dist key recommendation on table is not automatically applied
SELECT count(*), 'REC_008'
FROM data
WHERE type='diststyle' and auto_eligible='f'
""",
    ),
    (
        'CopyPerformance',
        'provisioned',
        """\
-- CopyPerformance
WITH data AS (
SELECT
  end_time::DATE AS copy_date,
  database_name db,
  table_name,
  split_part(data_source, '/', 3) s3_bucket,
  file_format,
  sum(case when splits > source_file_count then 1 else 0 end) split_copies,
  sum(loaded_rows) rows_inserted,
  sum(source_file_count) files_scanned,
  sum((file_bytes_scanned/1000000)::int) mb_scanned,
  avg(loaded_rows/(duration/1000000::decimal(18,2))) insert_rate_rows_per_second,
  avg(source_file_count) avg_files_per_copy,
  avg(file_bytes_scanned/source_file_count)::decimal(18,2) avg_file_size_mb,
  avg(file_bytes_scanned/(duration/1000000::decimal(18,2))) avg_scan_kbps,
  count(distinct query_id) no_of_copy,
  max(query_id) sample_query,
  sum(duration/1000000)::decimal(18,2) total_copy_time_secs,
  avg(duration/1000000)::decimal(18,2) avg_copy_time_secs,
  sum(error_count) error_count
FROM SYS_LOAD_HISTORY join (
  select user_id, query_id,
    sum(splits_scanned) splits
  from SYS_LOAD_DETAIL
  group by 1,2) using (USER_ID, QUERY_ID)
where loaded_rows > 0
group by 1,2,3,4,5
)
-- Signal: files per copy are less than slice count
SELECT count(*), 'REC_023'
FROM data
WHERE no_of_copy > 24 AND (avg_files_per_copy < (SELECT COUNT(1) FROM stv_slices))
UNION ALL
-- Signal: files with a small size
SELECT count(*), 'REC_023'
FROM data
WHERE no_of_copy > 24 AND (avg_file_size_mb < 10)
""",
    ),
    (
        'DataShareConsumerUsage',
        'all',
        """\
-- DataShareConsumerUsage
WITH usage as (SELECT
    database_name,
    user_name,
    transaction_id,
    request_id,
    query_id,
    min(record_time) over (partition by user_id, session_id, transaction_id) request_start_date,
    max(record_time) over (partition by user_id, session_id, transaction_id) request_end_date,
    request_start_date::date request_date,
    round(execution_time/1000000.0,2) query_execution_secs,
    round(datediff('milliseconds', min(record_time) over (partition by user_id, session_id, transaction_id), max(record_time) over(partition by user_id, session_id, transaction_id))/1000.0,2) as request_duration_secs,
    case when trim(nvl(error_message,'')) = '' then 0 else 1 end error_cnt,
    round(datediff('milliseconds',request_end_date,start_time)/1000.0, 2)  as request_interval_secs,
    round(datediff('milliseconds',request_start_date,end_time)/1000.0, 2)  as execution_secs
FROM SYS_DATASHARE_USAGE_CONSUMER
JOIN SYS_QUERY_HISTORY using (user_id, session_id, transaction_id)
JOIN SVV_USER_INFO using (user_id)),
perc as (SELECT
    request_date,
    database_name,
    user_name,
    percentile_cont(0.8) within GROUP ( ORDER BY request_duration_secs) AS p80_request_sec,
    percentile_cont(0.9) within GROUP ( ORDER BY request_duration_secs) AS p90_request_sec,
    percentile_cont(0.99) within GROUP ( ORDER BY request_duration_secs) AS p99_request_sec
FROM usage
group by 1,2,3),
data as (
select
    request_date,
    database_name db,
    user_name,
    count(distinct query_id) query_count,
    avg(query_execution_secs) as avg_query_execution_secs,
    sum(query_execution_secs) as total_query_execution_secs,
    avg(execution_secs)::decimal(18,2) as avg_execution_secs,
    sum(execution_secs)::decimal(18,2) as total_execution_secs,
    avg(request_duration_secs) as avg_request_duration_secs,
    min(p80_request_sec) p80_request_sec,
    min(p90_request_sec) p90_request_sec,
    min(p99_request_sec) p99_request_sec,
    sum(request_duration_secs) as total_request_duration_secs,
    avg(request_interval_secs) as avg_request_interval_secs,
    sum(request_interval_secs) as total_request_interval_secs,
    count(distinct transaction_id) total_unique_transaction,
    count(distinct request_id) total_usage_consumer_count,
    sum(error_cnt) total_request_error_count
FROM usage join perc using(request_date, database_name, user_name)
GROUP BY 1,2,3
)
-- Signal: long running metadata sync
SELECT count(*), 'REC_028'
FROM data
WHERE avg_request_duration_secs > 60
UNION ALL
SELECT count(*), 'REC_034'
FROM data
WHERE avg_request_duration_secs > 60
""",
    ),
    (
        'DataShareProducerObject',
        'all',
        """\
-- DataShareProducerObject
WITH data AS (
SELECT d.share_type,
    d.share_name,
    d.include_new,
    d.producer_account,
    d.object_type,
    split_part(d.object_name, '.', 1) namespace,
    split_part(d.object_name, '.', 2) table_name,
    ti.estimated_visible_rows,
    vi.record_time last_vacuum_date,
    vi.vacuum_type,
    mi.is_stale mv_is_stale,
    CASE WHEN mi.state = 1 THEN 'Y' WHEN mi.state <> 1 THEN 'N' ELSE NULL END AS is_mv_incremental_refresh,
    CASE WHEN mi.autorefresh = 1 THEN 'Y' WHEN mi.autorefresh <> 1 THEN 'N' ELSE NULL END AS is_mv_auto_refresh
FROM SVV_DATASHARE_OBJECTS d
LEFT OUTER JOIN SVV_TABLE_INFO ti ON (split_part(d.object_name, '.', 1) = ti."schema" and split_part(d.object_name, '.', 2) = ti."table" and current_database() = ti."database")
LEFT OUTER JOIN SVV_MV_INFO mi ON (ti."database" = mi.database_name and ti."schema" = mi."schema_name" and ti."table" = mi."name")
LEFT OUTER JOIN (SELECT record_time, table_id, table_name, status, vacuum_type,
    row_number() over (PARTITION BY table_id order by record_time desc) rownum
    FROM SYS_VACUUM_HISTORY
    WHERE status != 'Skipped') vi on ti.table_id = vi.table_id and vi.rownum = 1
WHERE share_type = 'OUTBOUND' and object_type = 'table'
ORDER BY 2,3,5,4
)
-- Signal: materialized view shared by a producer is doing a full refresh
SELECT count(*), 'REC_034'
FROM data
WHERE is_mv_incremental_refresh = 'N'
""",
    ),
    (
        'ExtQueryPerformance',
        'all',
        """\
-- ExtQueryPerformance
WITH data AS (
SELECT source_type, split_part(table_name,'.',1) db,
    case when split_part(table_name,'.',2) like 'pg_temp%' then 'pg_temp' else split_part(table_name,'.',2) end AS namespace,
    case when namespace = 'pg_temp' then
        substring(split_part(table_name,'.',3),1,len(split_part(table_name,'.',3))-14)
        else split_part(table_name,'.',3) end AS external_table_name,
    file_format,
    split_part(file_location, '/', 3) s3_bucket,
    CASE WHEN nvl(total_partitions,1) > 1 THEN 'Y' ELSE 'N' END AS is_table_partitioned,
    nvl(max(total_partitions),1) AS external_table_partition_count,
    COUNT(1) total_query_count,
    SUM(CASE WHEN nvl(qualified_partitions,1) < nvl(total_partitions,1) THEN 1 ELSE 0 END) total_query_using_Partition_Pruning_count,
    (total_query_using_Partition_Pruning_count::numeric / total_query_count::numeric)*100 AS pct_of_query_using_Partition_Pruning,
    nvl(AVG(qualified_partitions),1) AS avg_Qualified_Partitions,
    nvl(avg(scanned_files),0) AS avg_Files,
    AVG(case when nvl(scanned_files,0) > 0 then (returned_bytes/scanned_files/1000000.0)::decimal(18,2) else 0 end) AS avg_file_size_mb,
    AVG(duration / 1000000.0)::decimal(18,2) avg_Elapsed_sec,
    SUM(duration / 1000000.0)::decimal(18,2) Total_Elapsed_sec,
    SUM(nvl(error_cnt,0)) AS total_scan_error_count,
    AVG(nvl(error_cnt,0)) AS avg_scan_error_count
FROM SYS_EXTERNAL_QUERY_DETAIL
LEFT JOIN (select user_id, query_id, count(1) error_cnt FROM SYS_EXTERNAL_QUERY_ERROR GROUP BY 1,2) e USING (user_id, query_id)
WHERE table_name != '..' and table_name != '' and duration > 0
group by 1,2,3,4,5,6,7
)
-- Signal: high count of long queries not using partition pruning
SELECT count(*), 'REC_027'
FROM data
WHERE avg_qualified_partitions > 100 and avg_elapsed_sec > 60 AND (pct_of_query_using_partition_pruning < 95)
""",
    ),
    (
        'MaterializedView',
        'all',
        """\
-- MaterializedView
WITH data AS (
SELECT
  database_name db, schema_name namespace, user_name, name, is_stale, state, autorewrite, autorefresh,
  CASE state
    WHEN 0 THEN 'The MV is fully recomputed when refreshed'
    WHEN 1 THEN 'The MV is incremental'
    WHEN 101 THEN 'The MV cant be refreshed due to a dropped column. This constraint applies even if the column is not used in the MV'
    WHEN 102 THEN 'The MV cant be refreshed due to a changed column type. This constraint applies even if the column is not used in the MV'
    WHEN 103 THEN 'The MV cant be refreshed due to a renamed table'
    WHEN 104 THEN 'The MV cant be refreshed due to a renamed column. This constraint applies even if the column is not used in the MV'
    WHEN 105 THEN 'The MV cant be refreshed due to a renamed schema'
    ELSE NULL
  END AS state_desc,
  mv_state, event_desc, event_starttime,
  refresh_db_username, refresh_status, refresh_type, refresh_starttime, refresh_endtime, refresh_duration_secs
FROM SVV_MV_INFO
LEFT JOIN (SELECT database_name, mv_schema schema_name, mv_name name,
  state AS mv_state, event_desc, start_time event_starttime
  FROM SYS_MV_STATE s
  QUALIFY ROW_NUMBER() OVER (PARTITION BY database_name, schema_name, mv_name ORDER BY start_time DESC) = 1)
  USING (database_name, schema_name, name)
LEFT JOIN (SELECT database_name, schema_name, mv_name name, user_name refresh_db_username,
    status refresh_status, refresh_type, start_time refresh_starttime, end_time refresh_endtime, duration/1000000 refresh_duration_secs
  FROM SYS_MV_REFRESH_HISTORY h
  JOIN SVV_USER_INFO u using (user_id)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY database_name, schema_name, mv_name ORDER BY start_time DESC) = 1
) USING (database_name, schema_name, name) WHERE SVV_MV_INFO.schema_name <> 'pg_automv'
)
-- Signal: materialized view is doing a full refresh
SELECT count(*), 'REC_030'
FROM data
WHERE state=0
UNION ALL
-- Signal: materialized view cannot be auto refreshed
SELECT count(*), 'REC_031'
FROM data
WHERE state > 1 and is_stale = 't' and autorefresh = 't'
UNION ALL
-- Signal: materialized view is stale
SELECT count(*), 'REC_039'
FROM data
WHERE is_stale = 't'
""",
    ),
    (
        'NodeDetails',
        'provisioned',
        """\
-- NodeDetails
WITH data AS (
SELECT CASE
       WHEN capacity = 190633 THEN 'dc2.large'
       WHEN capacity = 760956 THEN 'dc2.8xlarge'
       WHEN capacity = 726296 THEN 'dc2.8xlarge'
       WHEN capacity = 952455 THEN 'ds2.xlarge'
       WHEN capacity = 945026 THEN 'ds2.8xlarge'
       WHEN capacity < 2002943 THEN 'ra3.large'
       WHEN capacity = 2002943 AND part_count = 1 THEN 'ra3.xlplus'
       WHEN capacity > 2002943 AND part_count = 1 THEN 'ra3.4xlarge'
       WHEN capacity > 2002943 AND part_count = 4 THEN 'ra3.16xlarge'
       ELSE 'unknown'
       END AS node_type,
       s.node,
       slice_count,
       storage_utilization_pct,
       storage_capacity_gb,
       storage_used_gb
FROM (SELECT distinct p.host node, p.capacity, count(1) part_count FROM stv_partitions p WHERE host = owner GROUP BY 1,2) AS s
INNER JOIN (SELECT node,COUNT(1) AS slice_count FROM stv_slices WHERE type='D' GROUP BY node) n ON (s.node = n.node)
INNER JOIN (SELECT node,
       ROUND((used::decimal(18,2)/capacity)*100,2) AS storage_utilization_pct,
       (capacity::decimal(18,2)/1000) AS storage_capacity_gb,
       (used::decimal(18,2)/1000) AS storage_used_gb
  FROM stv_node_storage_capacity) ns ON (s.node = ns.node)
ORDER by 2
)
-- Signal: should consider migrating to RG instances
SELECT count(*), 'REC_001'
FROM data
WHERE node_type NOT LIKE 'rg%'
UNION ALL
SELECT count(*), 'REC_002'
FROM data
WHERE node_type NOT LIKE 'rg%'
UNION ALL
SELECT count(*), 'REC_004'
FROM data
WHERE node_type NOT LIKE 'rg%'
UNION ALL
SELECT count(*), 'REC_005'
FROM data
WHERE node_type NOT LIKE 'rg%'
UNION ALL
SELECT count(*), 'REC_006'
FROM data
WHERE node_type NOT LIKE 'rg%'
UNION ALL
-- Signal: has under-utilized storage
SELECT count(*), 'REC_012'
FROM data
WHERE storage_utilization_pct < 40 and node_type NOT LIKE 'rg%'
UNION ALL
-- Signal: has 10% data skew
SELECT count(*), 'REC_008'
FROM data
WHERE 100*abs(storage_used_gb - (select min(storage_used_gb) from data))/storage_used_gb >= 10
""",
    ),
    (
        'TableInfo',
        'all',
        """\
-- TableInfo
WITH data AS (
SELECT
  "database" db,
  "schema" namespace,
  "table" table_name,
  max_varchar,
  sortkey1,
  tbl_rows,
  skew_rows,
  diststyle,
  vacuum_sort_benefit,
  stats_off,
  sortkey1_enc,
  sortkey_num,
  CASE WHEN t.tbl_rows - t.estimated_visible_rows < 0 THEN 0 ELSE (t.tbl_rows - t.estimated_visible_rows) END  num_rows_marked_for_deletion,
  case when nvl(tbl_rows,0) = 0 then 0 else (nvl(num_rows_marked_for_deletion,0) / nvl(tbl_rows,0))*100::decimal(18,2) end pct_rows_marked_for_deletion,
  encoded_column_pct,
  column_count,
  encoded_column_count
From SVV_TABLE_INFO T
JOIN (SELECT attrelid,
  COUNT(1) column_count,
  Sum(CASE WHEN attisdistkey = false THEN 0 ELSE 1 END) distkey_column_count,
  Sum(CASE WHEN attencodingtype IN ( 0, 128 ) THEN 0 ELSE 1 END) encoded_column_count,
  Sum(CASE WHEN attencodingtype NOT IN ( 0, 128 ) AND attsortkeyord > 0 THEN 0 ELSE 1 END) encoded_sortkey_count,
  ((encoded_column_count::decimal / column_count)*100)::int encoded_column_pct
FROM   pg_attribute
WHERE  attnum > 0
GROUP  BY attrelid) c ON c.attrelid = t.table_id
where "schema" not in ('information_schema', 'pg_catalog', 'pg_automv', 'pg_internal') and "database" not in ('sample_data_dev')
)
-- Signal: tables with wide columns
SELECT count(*), 'REC_011'
FROM data
WHERE max_varchar > 1000
UNION ALL
-- Signal: large tables without a sort key
SELECT count(*), 'REC_007'
FROM data
WHERE tbl_rows > 5000000 and sortkey1 NOT LIKE 'AUTO(SORTKEY%' AND (sortkey1 = '')
UNION ALL
-- Signal: large tables with skew
SELECT count(*), 'REC_008'
FROM data
WHERE tbl_rows > 5000000 AND (skew_rows >= 4 and diststyle not like 'AUTO%')
UNION ALL
-- Signal: large tables with unsorted data
SELECT count(*), 'REC_013'
FROM data
WHERE tbl_rows > 5000000 AND (vacuum_sort_benefit >= 10)
UNION ALL
-- Signal: tables with interleaved sort keys
SELECT count(*), 'REC_014'
FROM data
WHERE tbl_rows > 5000000 AND (sortkey1 like '%INTERLEAVED%')
UNION ALL
-- Signal: small tables without an ALL distribution
SELECT count(*), 'REC_008'
FROM data
WHERE tbl_rows <= 5000000 and diststyle not like 'AUTO%' AND (diststyle not like '%ALL%')
UNION ALL
-- Signal: small tables with a sort key
SELECT count(*), 'REC_007'
FROM data
WHERE tbl_rows <= 5000000 and sortkey1 not like 'AUTO(SORTKEY%' AND (sortkey1 != '')
UNION ALL
-- Signal: large tables needing a vacuum delete
SELECT count(*), 'REC_002'
FROM data
WHERE tbl_rows > 5000000 AND (pct_rows_marked_for_deletion > 10)
UNION ALL
-- Signal: tables with out of date statistics
SELECT count(*), 'REC_003'
FROM data
WHERE stats_off > 10 or stats_off is null
UNION ALL
-- Signal: large tables with encoded sort keys
SELECT count(*), 'REC_010'
FROM data
WHERE tbl_rows > 5000000 and not sortkey1 like 'AUTO(SORTKEY%' AND (sortkey1_enc != 'none' and sortkey1_enc != '')
UNION ALL
-- Signal: tables with low column compression
SELECT count(*), 'REC_004'
FROM data
WHERE ((column_count - encoded_column_count) - (case when sortkey1_enc = 'none' or sortkey1_enc = '' then 1 else 0 end)) AND tbl_rows > 5000000 AND (encoded_column_pct < 80)
UNION ALL
-- Signal: large tables distributed by date or datetime
SELECT count(*), 'REC_008'
FROM data
WHERE tbl_rows > 5000000 AND (diststyle like '%KEY%date%' or diststyle like '%KEY%dt%' or diststyle like '%KEY%timestamp%' or diststyle like '%KEY%datetime%')
""",
    ),
    (
        'Top50QueriesByRunTime',
        'all',
        """\
-- Top50QueriesByRunTime
WITH a as (
SELECT
  database_name db,
  user_name,
  generic_query_hash,
  query_id,
  (execution_time/1000000) execution_time_sec,
  count(1) over(partition by generic_query_hash) query_cnt,
  avg(compile_time/1000000) over(partition by generic_query_hash) compile_time_sec,
  avg(planning_time/1000000) over(partition by generic_query_hash) planning_time_sec,
  avg(lock_wait_time/1000000) over(partition by generic_query_hash) lock_wait_time_sec,
  avg(elapsed_time/1000000) over(partition by generic_query_hash) elapsed_time_sec,
  avg(queue_time/1000000) over(partition by generic_query_hash) queue_time_sec,
  avg(ROUND((queue_time*1.0/elapsed_time)*100,2)) over(partition by generic_query_hash) pct_wlm_queue_time,
  service_class_id,
  service_class_name,
  query_type,
  error_message,
  query_priority,
  compute_type
FROM SYS_QUERY_HISTORY
JOIN SVV_USER_INFO using (user_id)
WHERE user_id > 1 and service_class_id >= 5 and query_type != 'DDL' and execution_time > 1000000
QUALIFY ROW_NUMBER() OVER (PARTITION BY generic_query_hash ORDER BY execution_time DESC) = 1
order by execution_time_sec desc
limit 50),
b as (select query_id,
  max(case when is_rrscan = 't' then 1 else 0 end) rrscan,
  max(case when spilled_block_local_disk > 0 or spilled_block_remote_disk > 0 then 1 else 0 end) disk_spill,
  max(case when spilled_block_local_disk > 0 then 1 else 0 end) local_disk_spill,
  max(case when spilled_block_remote_disk > 0 then 1 else 0 end) remote_disk_spill,
  max(case when spilled_block_local_disk > 0 then spilled_block_local_disk else 0 end) local_disk_spill_mb,
  max(case when spilled_block_remote_disk > 0 then spilled_block_remote_disk else 0 end) remote_disk_spill_mb,
  listagg(distinct case
    when step_name = 'nestloop' and output_rows > 5000000 then 'Large nljoin'
    when step_name = 'scan' and input_rows >5000000 and is_rrscan = 'f' and output_rows< (.25*input_rows) then 'Scanning unsorted data'
    when step_name = 'broadcast' and output_rows >5000000 then 'Large broadcast'
    when step_name = 'distribute' and output_rows >5000000 then 'Large distribution'
    when alert like '%statistics%' then 'Missing statistics'
    else alert end, ', ') alerts,
  listagg(distinct case when table_name not like '%..%' and table_name != '' then table_name end, ', ') table_list,
  local_disk_spill_mb + remote_disk_spill_mb total_disk_spill_mb
from SYS_QUERY_DETAIL join a using (query_id)
group by 1),
data as (
select
  a.*,
  b.alerts, b.rrscan, b.disk_spill, b.local_disk_spill, b.remote_disk_spill, b.local_disk_spill_mb, b.remote_disk_spill_mb, b.table_list, b.total_disk_spill_mb
FROM a LEFT JOIN b on a.query_id = b.query_id
order by execution_time_sec desc
)
-- Signal: long running queries with missing Table Statistics
SELECT count(*), 'REC_003'
FROM data
WHERE lower(alerts) like '%stat%'
UNION ALL
-- Signal: long running queries using Nested Loop Joins
SELECT count(*), 'REC_009'
FROM data
WHERE lower(alerts) like '%nl%'
UNION ALL
SELECT count(*), 'REC_022'
FROM data
WHERE lower(alerts) like '%nl%'
UNION ALL
-- Signal: long running queries with Dist or Broadcast alerts
SELECT count(*), 'REC_008'
FROM data
WHERE lower(alerts) like '%dist%' or lower(alerts) like '%broadcast%'
UNION ALL
-- Signal: long running queries with Sort alerts
SELECT count(*), 'REC_007'
FROM data
WHERE lower(alerts) like '%sort%'
UNION ALL
-- Signal: high count of queries with large disk spill
SELECT count(*), 'REC_005'
FROM data
WHERE total_disk_spill_mb > 1000000
UNION ALL
SELECT count(*), 'REC_011'
FROM data
WHERE total_disk_spill_mb > 1000000
UNION ALL
SELECT count(*), 'REC_022'
FROM data
WHERE total_disk_spill_mb > 1000000
UNION ALL
SELECT count(*), 'REC_024'
FROM data
WHERE total_disk_spill_mb > 1000000
""",
    ),
    (
        'UsagePattern',
        'all',
        """\
-- UsagePattern
WITH data AS (
SELECT
  date_trunc('hour',start_time) as workload_exec_hour,
  service_class_id,
  service_class_name,
  count(1) query_count,
  sum(case when query_type = 'COPY' then 1 else 0 end) copy_count,
  sum(case when query_type = 'INSERT' then 1 else 0 end) insert_count,
  sum(case when query_type = 'UPDATE' then 1 else 0 end) update_count,
  sum(case when query_type = 'DDL' then 1 else 0 end) ddl_count,
  sum(case when query_type = 'CTAS' then 1 else 0 end) ctas_count,
  sum(case when result_cache_hit then 1 else 0 end) result_cache_hits,
  sum(case when queue_time > 0 then 1 else 0 end) queued_queries,
  sum(case when nvl(error_message,'') = '' then 0 else 1 end) error_queries,
  sum(case when compute_type != 'primary' then 1 else 0 end) burst_queries,
  sum(case when compute_type != 'primary' then execution_time/1000000.0 else 0 end)::decimal(18,2) burst_secs,
  sum(case when compile_time > 0 then 1 else 0 end) compiled_queries,
  sum(queue_time/1000000)::decimal(18,2) total_queue_time,
  sum(compile_time/1000000)::decimal(18,2) total_compile_time,
  sum(planning_time/1000000)::decimal(18,2) total_planning_time,
  sum(lock_wait_time/1000000)::decimal(18,2) total_lock_wait_time,
  sum(elapsed_time/1000000)::decimal(18,2) total_query_elapsed_time,
  case when total_query_elapsed_time > 0 then ROUND((total_queue_time*1.0/total_query_elapsed_time)*100,2) else 0 end pct_wlm_queue_time,
  sum(case when query_priority in ('low', 'lowest') then 1 else 0 end) low_priority_query_cnt,
  sum(case when query_priority in ('high', 'highest') then 1 else 0 end) high_priority_query_cnt,
  sum(case when short_query_accelerated = 'true' then 1 else 0 end) sqa_queries,
  sum(rrscan_queries) rrscan_queries,
  sum(disk_spill) total_disk_spill_count,
  sum(local_disk_spill) local_disk_spill_count,
  sum(remote_disk_spill) remote_disk_spill_count,
  sum(local_disk_spill_mb) total_local_disk_spill_mb,
  sum(remote_disk_spill_mb) total_remote_disk_spill_mb,
  sum(case when approx_rows_inserted between 1 and 100 then 1 else 0 end) small_insert_count
FROM SYS_QUERY_HISTORY
LEFT JOIN (select query_id,
  max(case when is_rrscan = 't' then 1 else 0 end) rrscan_queries,
  max(case when spilled_block_local_disk > 0 or spilled_block_remote_disk > 0 then 1 else 0 end) disk_spill,
  max(case when spilled_block_local_disk > 0 then 1 else 0 end) local_disk_spill,
  max(case when spilled_block_remote_disk > 0 then 1 else 0 end) remote_disk_spill,
  max(case when spilled_block_local_disk > 0 then spilled_block_local_disk else 0 end) local_disk_spill_mb,
  max(case when spilled_block_remote_disk > 0 then spilled_block_remote_disk else 0 end) remote_disk_spill_mb,
   sum(case when step_name = 'insert' then output_rows else 0 end) approx_rows_inserted
from SYS_QUERY_DETAIL
group by 1) SYS_QUERY_DETAIL using (QUERY_ID)
where user_id > 1 and service_class_id >= 5
group by 1,2,3
)
-- Signal: high count of COPY command
SELECT count(*), 'REC_023'
FROM data
WHERE copy_count > 100
UNION ALL
-- Signal: high count of small_insert statements
SELECT count(*), 'REC_029'
FROM data
WHERE small_insert_count > 100
UNION ALL
-- Signal: high count of WLM queuing
SELECT count(*), 'REC_019'
FROM data
WHERE pct_wlm_queue_time > 5
UNION ALL
SELECT count(*), 'REC_020'
FROM data
WHERE pct_wlm_queue_time > 5
UNION ALL
SELECT count(*), 'REC_026'
FROM data
WHERE pct_wlm_queue_time > 5
UNION ALL
-- Signal: high count of spilled to disk
SELECT count(*), 'REC_005'
FROM data
WHERE total_disk_spill_count > 100
UNION ALL
SELECT count(*), 'REC_011'
FROM data
WHERE total_disk_spill_count > 100
UNION ALL
SELECT count(*), 'REC_022'
FROM data
WHERE total_disk_spill_count > 100
UNION ALL
SELECT count(*), 'REC_024'
FROM data
WHERE total_disk_spill_count > 100
UNION ALL
-- Signal: high concurrency scaling usage
SELECT count(*), 'REC_033'
FROM data
WHERE burst_secs > 600
""",
    ),
    (
        'WLMConfig',
        'provisioned',
        """\
-- WLMConfig
WITH data AS (
SELECT
       min(case when scc.service_class >= 100 then 'auto' else 'manual' end) over (partition by null) wlm_mode,
       scc.service_class::text AS service_class_id,
       CASE
         WHEN scc.service_class BETWEEN 1 AND 4 THEN 'System'
         WHEN scc.service_class = 5 THEN 'Superuser'
         WHEN scc.service_class BETWEEN 6 AND 13 THEN 'Manual WLM'
         WHEN scc.service_class = 14 THEN 'SQA'
         WHEN scc.service_class = 15 THEN 'Redshift Maintenance'
         WHEN scc.service_class BETWEEN 100 AND 107 THEN 'Auto WLM'
       END AS service_class_category,
       trim(scc.name) AS queue_name,
       CASE
         WHEN scc.num_query_tasks = -1 THEN 'auto'
         ELSE scc.num_query_tasks::text
       END AS slots,
       CASE
         WHEN scc.query_working_mem = -1 THEN 'auto'
         ELSE scc.query_working_mem::text
       END AS query_working_memory_mb_per_slot,
       SUM(case when scc.service_class BETWEEN 6 AND 13 then num_query_tasks*query_working_mem else NULL end) over (partition by null) AS total_memory_mb,
       NVL(ROUND(((scc.num_query_tasks*scc.query_working_mem)::decimal(18,2)/ total_memory_mb::decimal(18,2))*100,0)::decimal(18,2)::varchar(12),'auto') cluster_memory_pct,
       scc.max_execution_time AS query_timeout,
       trim(scc.concurrency_scaling) AS concurrency_scaling,
       trim(scc.query_priority) AS queue_priority,
       nvl(qc.qmr_rule_count,0) AS qmr_rule_count,
       coalesce(qc.is_queue_evictable,'N') is_queue_evicatable,
       cnd.condition,
       qc.qmr_rule
FROM stv_wlm_service_class_config scc
INNER JOIN (
       select action_service_class, LISTAGG(TRIM(condition),', ') condition
       from stv_wlm_classification_config
       group by 1) cnd ON scc.service_class = cnd.action_service_class
LEFT OUTER JOIN (
       SELECT service_class,
         COUNT(1) AS qmr_rule_count,
         max(case when rule_name IS NOT NULL then 'Y' else 'N' end) is_queue_evictable,
         LISTAGG(rule_name || ':' || '[' || action || '] ' || metric_name || metric_operator || metric_value::VARCHAR(256) || ',') within group(order by rule_name) as qmr_rule
       FROM stv_wlm_qmr_config
       GROUP BY 1) qc ON (scc.service_class = qc.service_class)
WHERE scc.service_class > 4
ORDER BY 2 ASC
)
-- Signal: queues do not have total memory = 100
SELECT count(*), 'REC_016'
FROM data
WHERE wlm_mode='manual' and service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select sum(case when cluster_memory_pct = 'auto' then 0 else cluster_memory_pct::decimal end) from data) < 100)
UNION ALL
-- Signal: queues have total concurrency > 20
SELECT count(*), 'REC_017'
FROM data
WHERE wlm_mode='manual' and service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select sum(case when slots = 'auto' then 0 else slots::int end) from data where service_class_id not in (5,14,15)) > 20)
UNION ALL
-- Signal: uses single WLM queue
SELECT count(*), 'REC_018'
FROM data
WHERE service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select count(1) from data where service_class_category = 'Manual WLM') = 1 OR (select count(1) from data where service_class_category = 'Auto WLM') = 1)
UNION ALL
-- Signal: uses manual WLM
SELECT count(*), 'REC_015'
FROM data
WHERE wlm_mode='manual' and service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select count(1) from data where wlm_mode='manual') > 0)
UNION ALL
-- Signal: Concurrency scaling is not enabled
SELECT count(*), 'REC_019'
FROM data
WHERE service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select count(1) from data where concurrency_scaling = 'auto') = 0)
UNION ALL
-- Signal: short query acceleration (SQA) is not enabled
SELECT count(*), 'REC_020'
FROM data
WHERE service_class_id <> 5 and service_class_id <> 15 AND ((select count(1) from data where service_class_category != 'SQA') = (select count(1) from data))
UNION ALL
-- Signal: all query queues having the same query priority
SELECT count(*), 'REC_021'
FROM data
WHERE service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select count(distinct queue_priority) from data) = 1)
UNION ALL
-- Signal: no query monitoring rules (QMR) defined
SELECT count(*), 'REC_022'
FROM data
WHERE service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select sum(qmr_rule_count) from data) = 0)
UNION ALL
-- Signal: no QMR defined for query_execution_time metric
SELECT count(*), 'REC_022'
FROM data
WHERE service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select count(1) from data where coalesce(qmr_rule,'') not like '%query_execution_time%') = (select count(1) from data))
UNION ALL
-- Signal: no QMR defined for query_temp_blocks_to_disk metric
SELECT count(*), 'REC_022'
FROM data
WHERE service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select count(1) from data where coalesce(qmr_rule,'') not like '%query_temp_blocks_to_disk%') = (select count(1) from data))
UNION ALL
-- Signal: no QMR defined for spectrum_scan_size_mb or spectrum_scan_row_count metric
SELECT count(*), 'REC_022'
FROM data
WHERE service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select count(1) from data where coalesce(qmr_rule,'') not like '%spectrum_scan%') = (select count(1) from data))
""",
    ),
    (
        'WorkloadEvaluation',
        'all',
        """\
-- WorkloadEvaluation
WITH recursive min_list(start_min, end_min) as (
  SELECT
    dateadd(m,1,dateadd(d,-7,date_trunc('m',getdate()))) start_min,
    dateadd(m,2,dateadd(d,-7,date_trunc('m',getdate()))) end_min
  UNION ALL
  SELECT dateadd(m, 1, start_min), dateadd(m, 1, end_min) from min_list where start_min < date_trunc('m',getdate())),
scan_list as (
  SELECT query_id, max(mb_scanned) max_scan_mb,
    CASE WHEN max_scan_mb < 100 THEN 'small'
      WHEN max_scan_mb > 500000 THEN 'large'
      ELSE 'medium' END workloadtype
    FROM (
      SELECT query_id, segment_id, sum(blocks_read) mb_scanned
      FROM SYS_QUERY_DETAIL
      WHERE user_id > 1
      GROUP BY 1,2) scan_sum
  GROUP BY 1),
daily_summary as (
  SELECT
    workloadtype,
    datediff(m,start_min, date_trunc('m',getdate()))/1440 day_num,
    count(distinct start_min) mins_of_day
  FROM SYS_QUERY_HISTORY
  JOIN scan_list using (query_id)
  JOIN min_list ON start_time < end_min AND end_time > start_min
  WHERE user_id > 1
  GROUP BY 1,2),
summary as (
  SELECT workloadtype,
    avg(mins_of_day) total_query_minutes_in_day,
    ((total_query_minutes_in_day/1440.0)*100)::int perc_duration_in_day
  FROM daily_summary
  GROUP BY 1),
workload_breakdown as (
  SELECT
    workloadtype,
    sum(elapsed_time/1000000.0)::decimal(18,2) total_workload,
    min(elapsed_time/1000000.0)::decimal(18,2) workload_exec_sec_min,
    max(elapsed_time/1000000.0)::decimal(18,2) workload_exec_sec_max,
    avg(elapsed_time/1000000.0)::decimal(18,2) workload_exec_sec_avg,
    count(distinct query_id) query_cnt,
    avg(max_scan_mb) scan_mb_avg
  FROM SYS_QUERY_HISTORY
  JOIN scan_list using (query_id)
  WHERE start_time between dateadd(d,-7,date_trunc('m',getdate())) and date_trunc('m',getdate())
    and user_id > 1
  GROUP BY 1),
data as (
SELECT workloadtype,
  ((total_workload*1.0 / sum(total_workload) over (partition by null))*100)::int perc_of_total_workload,
  perc_duration_in_day, total_query_minutes_in_day,
  (sum(total_query_minutes_in_day) over () / 1440.0 * 100)::int total_pct_busy,
  workload_exec_sec_avg, workload_exec_sec_min,
  workload_exec_sec_max, query_cnt, scan_mb_avg
FROM summary s
JOIN workload_breakdown b using(workloadtype)
)
-- Signal: Evaluate Workload for Serverless. Cluster is busy less than 75% of the time in a day.
SELECT count(*), 'REC_035'
FROM data
WHERE total_pct_busy < 75
""",
    ),
]
