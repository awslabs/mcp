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

"""Consolidated review queries and recommendations.

This module replaces the three JSON config files (queries.json, signals.json,
recommendations.json) with Python constants that are ready to use at runtime.
"""

# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------
# Each value is a single markdown string combining the title, description,
# and documentation links for the recommendation.
# ---------------------------------------------------------------------------

RECOMMENDATIONS: dict[str, str] = {
    'REC_001': (
        '## For additional scalability, migrate to the RA3 node type or serverless\n\n'
        'RA3 nodes with managed storage provide independent scaling of compute and storage. '
        'Migrating from DC or DS node types to RA3 allows you to scale storage without adding compute, '
        'and leverages automatic data tiering between local SSD and S3-backed managed storage.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-clusters.html#rs-upgrading-to-ra3\n'
        '- https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-whatis.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-migration.html\n'
        '- https://aws.amazon.com/premiumsupport/knowledge-center/redshift-ra3-node-type/\n'
        '- https://aws.amazon.com/blogs/big-data/use-amazon-redshift-ra3-with-managed-storage-in-your-modern-data-architecture/\n'
    ),
    'REC_002': (
        '## For busy clusters, schedule a VACUUM DELETE\n\n'
        'Amazon Redshift automatically performs a DELETE ONLY vacuum in the background, so you rarely, '
        'if ever, need to run a DELETE ONLY vacuum. However, this operation only runs when the cluster '
        'is idle. If your cluster is busy, you should schedule this operation to minimize I/O operations. '
        'A VACUUM DELETE reclaims disk space occupied by rows that were marked for deletion by previous '
        'UPDATE and DELETE operations, and compacts the table to free up the consumed space. A DELETE ONLY '
        "vacuum operation doesn't sort table data.\n\n"
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/t_Reclaiming_storage_space202.html#automatic-table-delete\n'
    ),
    'REC_003': (
        '## For busy clusters, schedule ANALYZE commands\n\n'
        'Stale or missing table statistics reduce sort key effectiveness and may cause the optimizer '
        'not to use the optimal query path for the affected queries. A higher value of the stats_off '
        'column in SVV_TABLE_INFO means that statistics is more out of date hence it is recommended to '
        'check tables with >= 10. While Redshift automatically analyzes your data, this occurs when the '
        'cluster is not busy. If you have a busy cluster or if there are significant write '
        'operations/changes on the table (e.g. DDL change) and access to the data is immediately '
        'required, explicitly execute or schedule ANALYZE commands. Consider ANALYZE PREDICATE COLUMNS '
        'or sp_analyze_minimal if you have a wide table (100s of columns) for a faster execution.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/t_Analyzing_tables.html\n'
    ),
    'REC_004': (
        '## If you are running out of storage or to reduce I/O overhead, review compression encodings\n\n'
        'Compression is a column-level operation that reduces the size of data when it is stored. '
        'Compression conserves storage space and reduces the size of data that is read from storage, '
        'which reduces the amount of disk I/O and therefore improves query performance. As a best '
        'practice, leverage AZ64 for numeric and date data types and ZSTD for character data types '
        'where possible or use ENCODE AUTO to automatically manage the compression encoding for all '
        'columns in the table. For monitoring actions of automatic table optimization, '
        'SVV_ALTER_TABLE_RECOMMENDATIONS records the current Amazon Redshift Advisor recommendations '
        'for tables while SVL_AUTO_WORKER_ACTION shows an audit log of all the actions taken by Amazon '
        'Redshift, and the previous state of the table. To change the encoding of the table to AUTO: '
        'ALTER TABLE [table_name] ALTER ENCODE AUTO;\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/t_Compressing_data_on_disk.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/t_Verifying_data_compression.html\n'
    ),
    'REC_005': (
        '## If you are running out of storage or memory, add more compute nodes using resize\n\n'
        'When using node types like DC2, you may run into situations where you are out of storage. '
        'In some cases, both DC2 and RA3, where you see heavy disk spill, resizing your cluster can '
        'make more memory available and speed up query execution.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/mgmt/managing-cluster-operations.html#elastic-resize\n'
        '- https://aws.amazon.com/blogs/big-data/accelerate-resize-and-encryption-of-amazon-redshift-clusters-with-faster-classic-resize/\n'
    ),
    'REC_006': (
        '## Unload infrequently accessed data to S3 and query using Redshift Spectrum\n\n'
        'Redshift Spectrum allows you to query exabytes of data in your Amazon S3 data lake, without '
        'loading or moving objects. Infrequently accessed data (also known as COLD data) can reside or '
        'be offloaded in Amazon S3 and be queried in Amazon Redshift using Redshift Spectrum. You can '
        'also define a spectrum usage limit either as a daily, weekly, or monthly usage limit and define '
        'actions that Amazon Redshift automatically takes if the limits are reached. The action taken '
        'could be logging the event to a system table, creating an alert for notification, or disabling '
        'the feature.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/c-getting-started-using-spectrum.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/tutorial-query-nested-data.html\n'
        '- https://aws.amazon.com/blogs/big-data/10-best-practices-for-amazon-redshift-spectrum/\n'
        '- https://aws.amazon.com/blogs/big-data/manage-and-control-your-cost-with-amazon-redshift-concurrency-scaling-and-spectrum/\n'
        '- https://aws.amazon.com/blogs/big-data/working-with-nested-data-types-using-amazon-redshift-spectrum/\n'
    ),
    'REC_007': (
        '## To improve query performance, choose the best sort key\n\n'
        'For large tables, adding a sort key can speed up queries with predicates. Review commonly '
        'filtered fields and add a sort key: ALTER TABLE [table_name] ALTER SORTKEY ([column1], '
        '[columnN]). For small tables (less than 5 million rows), sort keys are not effective and will '
        'add maintenance and storage overhead: ALTER TABLE [table_name] ALTER SORTKEY NONE; For unknown '
        'table sizes or access patterns, you can set the sort key to AUTO which allows Redshift to '
        'define the optimal sort key: ALTER TABLE [table_name] ALTER SORTKEY AUTO;\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-sort-key.html\n'
    ),
    'REC_008': (
        '## To improve query performance, choose the best distribution style\n\n'
        'Heavy skew (where the ratio of the number of rows on a slice is more than 4x of another slice) '
        'can cause queries to perform slower as they are waiting on the compute node with the most data '
        'to complete before returning the result set. If the first node is skewed, this may be due to '
        'using a distribution key containing nulls. To change the column used as a distribution key: '
        'ALTER TABLE [table_name] ALTER DISTSTYLE KEY DISTKEY [column_name]; For small tables (< 5 '
        'million rows) e.g. reference or dimension tables that are frequently used in JOINS consider an '
        'ALL distribution style. To manage the distribution style automatically, create your tables with '
        'DISTSTYLE AUTO. Amazon Redshift initially assigns ALL distribution to a small table, then '
        'changes to EVEN distribution when the table grows larger. A low skew value indicates that table '
        'data is properly distributed. If a table has a skew value of 4.00 or higher, consider modifying '
        'its data distribution style.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-best-dist-key.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/t_Creating_tables.html#ato-enabling\n'
        '- https://aws.amazon.com/blogs/big-data/amazon-redshift-engineerings-advanced-table-design-playbook-distribution-styles-and-distribution-keys/\n'
        '- https://aws.amazon.com/blogs/big-data/automate-your-amazon-redshift-performance-tuning-with-automatic-table-optimization/\n'
    ),
    'REC_009': (
        '## To improve query performance, remove nested loop joins (cross-joins)\n\n'
        'Review queries that make use of cross-joins and remove them if possible by adding a join '
        'condition.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/query-performance-improvement-opportunities.html#nested-loop\n'
    ),
    'REC_010': (
        '## To improve query performance, remove the encoding on the first column of a sort key\n\n'
        'It is a best practice to not encode the first column of a sort key for optimal query '
        'performance. Using ENCODE AUTO to automatically manage the compression encoding for all columns '
        'in the table also ensures this. To change the encoding of the table to AUTO, the following '
        'command can be executed: ALTER TABLE [table_name] ALTER ENCODE AUTO;\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/t_Verifying_data_compression.html\n'
    ),
    'REC_011': (
        '## To optimize memory consumption and avoid disk spill, reduce varchar fields to be inline with their max length\n\n'
        'Use caution when setting a large length on character type fields such as VARCHAR. When '
        'allocating memory for queries using these fields, Amazon Redshift will allocate based on the '
        'maximum values and queries are more likely to spill to disk. To change the length of the '
        'column, the following command can be executed: ALTER TABLE [table_name] ALTER COLUMN '
        '[column_name] TYPE varchar([size])\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-smallest-column-size.html\n'
    ),
    'REC_012': (
        '## To save cost, remove extra compute nodes using elastic or classic resize\n\n'
        'You may have more compute than you need. If you can reduce the size of your cluster and '
        'maintain your SLAs, you may be able to save money. In addition, enable the concurrency scaling '
        'feature and leverage the 1 hour free credit per day on a given WLM queue. Apply the necessary '
        'concurrency scaling usage limits. Use of concurrency scaling allows the cluster to handle spiky '
        'compute needs and allow for queries in WLM queues in which it is enabled to get consistent '
        'performance.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/mgmt/managing-cluster-operations.html#elastic-resize\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/concurrency-scaling-queues.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/mgmt/managing-cluster-usage-limits.html\n'
        '- https://aws.amazon.com/blogs/big-data/accelerate-resize-and-encryption-of-amazon-redshift-clusters-with-faster-classic-resize/\n'
    ),
    'REC_013': (
        '## To improve query performance, ensure large tables with a sort key are vacuumed\n\n'
        'Tables which contain a sort key but have not been vacuumed will not benefit from the sort key. '
        'While Auto Vacuum should optimize most tables, in busy clusters, customers should schedule the '
        'VACUUM SORT RECLUSTER operation either as part of the regular data ingestion / transformation '
        'workload (especially those that affect a large number of rows) or as part of a recurring '
        'maintenance activity (e.g. weekly / monthly) based on the vacuum_sort_benefit column in '
        'SVV_TABLE_INFO. Use the DEEP COPY approach if the table does not need to be accessible for '
        'writes. A deep copy is much faster than a vacuum. The trade off is that you should not make '
        'concurrent updates during a deep copy operation unless you can track it and move the delta '
        'updates into the new table after the process has completed.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/r_VACUUM_command.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/performing-a-deep-copy.html\n'
    ),
    'REC_014': (
        '## To improve query performance and reduce maintenance overhead, replace Interleaved Sort keys with Materialized Views\n\n'
        'While interleaved sort keys may provide some benefit for tables with multiple access patterns, '
        'Materialized Views (MVs) are a newer strategy to optimize for performance in similar situations. '
        'MVs can be used to support not only different sorting strategies, but also calculated fields, '
        'different distribution strategies, and pre-aggregated results. Also, tables with an interleaved '
        'sort key are not eligible for concurrency scaling and data sharing. If your use case still '
        'requires interleaved sort keys, keep in mind a VACUUM REINDEX is required to take advantage of '
        'it, but it is an expensive operation and in many cases the performance benefit is not worth the '
        'additional maintenance effort.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/materialized-view-overview.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/r_VACUUM_command.html#vacuum-reindex\n'
    ),
    'REC_015': (
        '## To maximize system throughput and use resources most effectively, set up automatic WLM\n\n'
        'With automatic workload management (autoWLM), Amazon Redshift manages query concurrency and '
        'memory allocation. Automatic WLM determines the amount of resources that queries need, and '
        'adjusts the concurrency based on the workload. When queries requiring large amounts of '
        'resources are in the system (for example, hash joins between large tables), the concurrency is '
        'lower. When lighter queries (such as inserts, deletes, scans, or simple aggregations) are '
        'submitted, concurrency is higher.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/automatic-wlm.html\n'
        '- https://aws.amazon.com/blogs/big-data/benchmarking-the-performance-of-the-new-auto-wlm-with-adaptive-concurrency-in-amazon-redshift/\n'
    ),
    'REC_016': (
        '## Re-allocate your memory distribution to add up to 100%\n\n'
        'When using manual WLM total memory allocation should equal 100%. Allocating less than 100% may '
        'result in unpredictable query performance and/or inefficient use of cluster resources.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/cm-c-defining-query-queues.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/cm-c-defining-query-queues.html#wlm-memory-percent\n'
    ),
    'REC_017': (
        '## To improve query performance, configure no more than 20 WLM slots\n\n'
        'When using manual WLM, high slot counts can result in too little memory being allocated to each '
        'query and results spilling to disk which may affect the query performance and having a lower '
        'query throughput. When you use lower concurrency, query throughput is increased and overall '
        'system performance is improved for most workloads.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/cm-c-defining-query-queues.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/cm-c-defining-query-queues.html#cm-c-defining-query-queues-concurrency-level\n'
    ),
    'REC_018': (
        '## To have better visibility on resource usage by workload and optimize resource allocation, create separate query queues for each workload\n\n'
        'When you define multiple query queues, you can route queries to the appropriate queues at '
        'runtime. For example query queues can be defined for each type of workload: BI / Dashboard '
        'workload, ETL / Data Ingestion workload, Data Science workload, Adhoc workload, Application '
        'workload.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/cm-c-wlm-queue-assignment-rules.html\n'
    ),
    'REC_019': (
        '## For additional scalability, enable the concurrency scaling\n\n'
        'Use of concurrency scaling allows the cluster to handle spiky compute needs and allow for '
        'queries in WLM queues in which it is enabled to get consistent performance. Concurrency scaling '
        'is available 1 hour free per day. Additionally usage limits can be applied to manage costs.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/concurrency-scaling.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/concurrency-scaling-queues.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/mgmt/managing-cluster-usage-limits.html\n'
        '- https://aws.amazon.com/blogs/big-data/manage-and-control-your-cost-with-amazon-redshift-concurrency-scaling-and-spectrum/\n'
        '- https://www.youtube.com/watch?v=-2yQsI9xJKQ\n'
    ),
    'REC_020': (
        '## For additional scalability, enable short query acceleration\n\n'
        'If you enable SQA, you can reduce or eliminate workload management (WLM) queues that are '
        'dedicated to running short queries. Amazon Redshift uses a machine learning algorithm to '
        "analyze each eligible query and predict the query's execution time. By default, WLM "
        "dynamically assigns a value for the SQA maximum runtime based on analysis of your cluster's "
        'workload. Alternatively, you can specify a fixed value of 1 to 20 seconds.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/wlm-short-query-acceleration.html\n'
    ),
    'REC_021': (
        '## To ensure queries get resources based on importance, set priorities for each WLM queue\n\n'
        'Not all queries are of equal importance, and often performance of one workload or set of users '
        'might be more important. When auto WLM is enabled, you can define the relative importance of '
        'queries in a workload by setting a priority value. The priority is specified for a queue and '
        'inherited by all queries associated with the queue. Amazon Redshift uses the priority when '
        'letting queries into the system, and to determine the amount of resources allocated to a '
        'query.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/query-priority.html\n'
    ),
    'REC_022': (
        '## To set query performance boundaries on workloads, add QMR rules\n\n'
        'Query monitoring rules (QMR) define metrics-based performance boundaries for WLM queues and '
        'specify what action to take when a query goes beyond those boundaries. For example, to track '
        'poorly designed queries, you might have a rule that logs queries that contain nested loops or '
        'execute for more than 2 hours. You can define up to 25 rules for each queue, with a limit of '
        '25 rules for all queues. You can start with Query monitoring rules templates. WLM evaluates '
        'metrics every 10 seconds. If more than one rule is triggered during the same period, WLM '
        'initiates the most severe action: abort, then hop, then log. The most common metrics where QMR '
        'can protect your system include: query_execution_time (identifies sub-optimal table or query '
        'design), query_temp_blocks_to_disk (identifies queries using more than available memory which '
        'write intermediate results to disk), spectrum_scan_size_mb / spectrum_scan_row_count (a large '
        'scan may mean there is no partition pruning applied), and nested_loop_join_row_count (joins '
        'without a join condition that result in the Cartesian product of two tables).\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/cm-c-wlm-query-monitoring-rules.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/cm-c-wlm-query-monitoring-rules.html#cm-c-wlm-query-monitoring-templates\n'
    ),
    'REC_023': (
        '## Increase load performance by optimizing COPY operations\n\n'
        'Amazon Redshift can automatically load in parallel from multiple compressed data files. This '
        'divides the workload among the nodes in your cluster. However, if you use multiple concurrent '
        'COPY commands to load one table from multiple files, Amazon Redshift performs a serialized load '
        'which is slower than loading them using one operation. Optimal COPY performance can be achieved '
        'through a file count that is a multiple of the number of node slices. For optimum parallelism, '
        'the ideal file size is 1 to 125 MB after compression.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/t_Loading-data-from-S3.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/c_loading-data-best-practices.html\n'
        '- https://aws.amazon.com/blogs/big-data/part-1-introducing-new-features-for-amazon-redshift-copy/\n'
    ),
    'REC_024': (
        '## To avoid disk spill, review queries and add predicates to filter tables that participate in joins, even if the predicates apply the same filters\n\n'
        'Even though a filter may be redundant, the query planner can skip scanning large numbers of '
        'disk blocks when performing a join operation. For example, adding a predicate for sales.saletime '
        'to the WHERE clause returns the same result set without the filter because a product will always '
        'be sold after it is listed, but Amazon Redshift is able to filter the table before the join '
        'step.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/c_designing-queries-best-practices.html\n'
    ),
    'REC_025': (
        '## To reduce compile overhead, avoid drop/create operations in favor of delete/copy/insert\n\n'
        'High compile count can be caused by queries executed against new tables.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/c-query-performance.html\n'
        '- https://aws.amazon.com/blogs/big-data/fast-and-predictable-performance-with-serverless-compilation-using-amazon-redshift/\n'
    ),
    'REC_026': (
        '## For additional scalability, isolate your workloads using data sharing\n\n'
        'Amazon Redshift data sharing provides workload isolation by allowing multiple consumers to '
        'share data seamlessly without the need to unload and load data. Implementing workload isolation '
        'allows for agility, allows sizing of clusters independently, and creates a simple cost '
        'charge-back model.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/data_sharing_intro.html\n'
        '- https://aws.amazon.com/blogs/big-data/amazon-redshift-data-sharing-best-practices-and-considerations/\n'
        '- https://aws.amazon.com/blogs/big-data/sharing-amazon-redshift-data-securely-across-amazon-redshift-clusters-for-workload-isolation/\n'
        '- https://aws.amazon.com/blogs/big-data/implementing-multi-tenant-patterns-in-amazon-redshift-using-data-sharing/\n'
        '- https://aws.amazon.com/blogs/aws/cross-account-data-sharing-for-amazon-redshift/\n'
        '- https://aws.amazon.com/blogs/big-data/security-considerations-for-amazon-redshift-cross-account-data-sharing/\n'
        '- https://aws.amazon.com/blogs/big-data/share-data-securely-across-regions-using-amazon-redshift-data-sharing/\n'
    ),
    'REC_027': (
        '## Increase read performance from Spectrum tables, by optimizing your partitioning strategy\n\n'
        'When you partition your data, you can restrict the amount of data that Redshift Spectrum scans '
        'by filtering on the partition key. Amazon Redshift Spectrum can take advantage of partition '
        'pruning and skip scanning unneeded partitions and files by defining the S3 prefix based on the '
        'columns (e.g. transaction_date) frequently used in SQL predicates. A common practice is to '
        'partition the data based on time. For example, you might choose to partition by year, month, '
        'date, and hour. If you have data coming from multiple sources, you might partition by a data '
        'source identifier and date.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/c-spectrum-external-performance.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/c-spectrum-external-tables.html#c-spectrum-external-tables-partitioning\n'
        '- https://aws.amazon.com/blogs/big-data/10-best-practices-for-amazon-redshift-spectrum/\n'
    ),
    'REC_028': (
        '## To improve query performance, redesign the large table to a time series table\n\n'
        'If your data has a fixed retention period, you can organize your data as a sequence of '
        'time-series tables. In such a sequence, each table is identical but contains data for different '
        'time ranges. You can easily remove old data simply by running a DROP TABLE command on the '
        'corresponding tables. This approach is much faster than running a large-scale DELETE process and '
        'saves you from having to run a subsequent VACUUM process to reclaim space. To hide the fact '
        'that the data is stored in different tables, you can create a UNION ALL view. When you delete '
        'old data, simply refine your UNION ALL view to remove the dropped tables. Similarly, as you '
        'load new time periods into new tables, add the new tables to the view. To signal the optimizer '
        "to skip the scan on tables that don't match the query filter, your view definition filters for "
        'the date range that corresponds to each table. If your data requires processing of different '
        'time ranges, you can follow a similar approach but instead of a time range make use of another '
        'criteria for data segregation based on data access pattern such as geography (e.g. region). A '
        'sample conversion process: create multiple tables based on how the data needs to be accessed '
        '(e.g. by week, month, quarter, geography, account), create a view that consolidates all the '
        'time series tables (may include external tables queried using Redshift Spectrum), replace the '
        'query on the table with the query on the view. If a query filters on the sort key, the query '
        'planner can efficiently skip all the tables that are not used.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-time-series-tables.html\n'
    ),
    'REC_029': (
        '## Increase load performance by avoiding or minimizing multiple single row insert statements\n\n'
        'A data ingestion / loading process that runs a single row insert or multi row insert statement '
        'uses only the leader node for each execution and is slow when used to load large amounts of '
        'data compared to other data ingestion / loading options like a COPY command which engages '
        'compute nodes in parallel. Data compression is also inefficient when you add data only one row '
        'or a few rows at a time. Redesign the data ingestion process to replace multiple single row '
        'insert statements to either use: COPY command, COPY command with column mapping, ALTER TABLE '
        'APPEND, Bulk Insert, or Multi Row Insert.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/c_loading-data-best-practices.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/t_Updating_tables_with_DML_commands.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-use-copy.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/copy-parameters-column-mapping.html#copy-column-list\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/r_ALTER_TABLE_APPEND.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-bulk-inserts.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-multi-row-inserts.html\n'
    ),
    'REC_030': (
        '## To improve query performance, create a materialized view to use incremental refresh\n\n'
        'A materialized view contains a precomputed result set, based on an SQL query over one or more '
        'base tables. Materialized views are especially useful for speeding up queries that are '
        'predictable and repeated. Instead of performing resource-intensive queries against large tables '
        '(such as aggregates or multiple joins), applications can query a materialized view and retrieve '
        'a precomputed result set. From the user standpoint, the query results are returned much faster '
        'compared to when retrieving the same data from the base tables. To complete refresh of the '
        'materialized views with minimal impact to active workloads in your cluster, create a '
        'materialized view that can perform an incremental refresh in order to quickly identify the '
        'changes to the data in the base tables since the last refresh and update the data in the '
        'materialized view.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/materialized-view-refresh.html\n'
        '- https://aws.amazon.com/blogs/big-data/speed-up-your-elt-and-bi-queries-with-amazon-redshift-materialized-views/\n'
        '- https://aws.amazon.com/blogs/big-data/optimize-your-analytical-workloads-using-the-automatic-query-rewrite-feature-of-amazon-redshift-materialized-views/\n'
    ),
    'REC_031': (
        '## To keep the data accurate and up to date, recreate the materialized view\n\n'
        'Due to underlying DDL changes on the base tables used in the materialized view, the '
        'materialized view can no longer be refreshed.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/r_STV_MV_INFO.html\n'
    ),
    'REC_033': (
        '## To save cost, apply the necessary concurrency scaling usage limit\n\n'
        'You can define limits to monitor and control your usage and associated cost of some Amazon '
        'Redshift features. You can create daily, weekly, and monthly usage limits, and define actions '
        'that Amazon Redshift automatically takes if those limits are reached. Actions include logging '
        'an event to a system table, raising alerts with Amazon SNS and Amazon CloudWatch to notify an '
        'administrator, and disabling further usage to control costs. A concurrency scaling limit '
        'specifies the threshold of the total amount of time used by concurrency scaling in 1-minute '
        'increments.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/mgmt/managing-cluster-usage-limits.html\n'
        '- https://aws.amazon.com/blogs/big-data/manage-and-control-your-cost-with-amazon-redshift-concurrency-scaling-and-spectrum/\n'
    ),
    'REC_034': (
        '## To improve query performance, create a materialized view to use incremental refresh in the producer cluster and share the materialized view to the consumer cluster(s)\n\n'
        'Materialized views (MVs) provide a powerful route to precompute complex aggregations for use '
        'cases where high throughput is needed, and you can directly share a materialized view object '
        'via data sharing as well. For materialized views built on tables where there are frequent write '
        'operations, it is ideal to create the materialized view object on the producer itself and share '
        'the view. This method gives us the opportunity to centralize the management of the view on the '
        'producer cluster itself. For slowly changing data tables, you can share the table objects '
        'directly and build the materialized view on the shared objects directly on the consumer. This '
        'method gives us the flexibility of creating a customized view of data on each consumer '
        'according to your use case. This can help optimize the block metadata download and caching '
        'times in the data sharing query lifecycle. This also helps in materialized view refreshes '
        'because Redshift does not support incremental refresh for MVs built on shared objects.\n\n'
        'See also:\n'
        '- https://aws.amazon.com/blogs/big-data/speed-up-your-elt-and-bi-queries-with-amazon-redshift-materialized-views/\n'
        '- https://aws.amazon.com/blogs/big-data/amazon-redshift-data-sharing-best-practices-and-considerations/\n'
    ),
    'REC_035': (
        '## For better price performance, leverage Redshift serverless\n\n'
        'Redshift serverless provides the same or better price performance when compared to on demand '
        'especially with intermittent workloads. This is possible because of its ability to auto pause '
        'and resume so you only pay for the times the cluster is running.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-serverless.html\n'
        '- https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-billing.html\n'
        '- https://www.youtube.com/watch?v=XcRJjXudIf8\n'
        '- https://www.youtube.com/watch?v=JBPpmMq9OS8\n'
    ),
    'REC_036': (
        "## To avoid 'connection limit' errors and release unused resources, set idle session timeout and clean up idle sessions when needed\n\n"
        'Idle connections consume cluster connection slots and hold resources unnecessarily. Configuring '
        'idle session timeouts and periodically cleaning up stale sessions prevents connection limit '
        'errors and frees resources for active workloads.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/mgmt/connecting-drop-issues.html\n'
    ),
    'REC_037': (
        "## For increased stability, use the 'trailing' track for production workloads\n\n"
        'The trailing maintenance track applies cluster patches after they have been validated on the '
        'current track for several weeks. Using the trailing track for production clusters reduces the '
        'risk of encountering issues from newly released patches.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-clusters.html#rs-maintenance-tracks\n'
    ),
    'REC_038': (
        '## To reduce processing skew, perform a classic resize to rebalance your data\n\n'
        'Data distribution skew across slices can develop over time, especially after multiple elastic '
        'resizes. A classic resize redistributes all data evenly across the new slice configuration, '
        'eliminating processing skew and restoring balanced query execution.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/mgmt/managing-cluster-operations.html#rs-resize-tutorial\n'
    ),
    'REC_039': (
        '## Ensure materialized views are not stale for data accuracy and query rewrite\n\n'
        'A materialized view contains a pre-computed result set, based on an SQL query over one or more '
        'base tables. Materialized views are especially useful for speeding up queries that are '
        'predictable and repeated. In addition, materialized views can be useful for accessing data '
        "using an alternate distribution or sort key. From the user standpoint, they don't have to "
        're-write their queries; the re-writer will determine and use the appropriate MV and the query '
        'results are returned much faster compared to when retrieving the same data from the base '
        'tables. A stale MV does not have up-to-date data and will not be used by autorewrite.\n\n'
        'See also:\n'
        '- https://docs.aws.amazon.com/redshift/latest/dg/materialized-view-refresh.html\n'
        '- https://aws.amazon.com/blogs/big-data/speed-up-your-elt-and-bi-queries-with-amazon-redshift-materialized-views/\n'
        '- https://aws.amazon.com/blogs/big-data/optimize-your-analytical-workloads-using-the-automatic-query-rewrite-feature-of-amazon-redshift-materialized-views/\n'
    ),
}


# ---------------------------------------------------------------------------
# Review queries
# ---------------------------------------------------------------------------
# Each entry is a tuple of (query_name, sql, is_provisioned_only).
#
# The SQL wraps the original base query in ``WITH data AS (...)`` and then
# emits one ``SELECT count(*), '<REC_XXX>' FROM data WHERE ...`` per
# recommendation ID, joined with ``UNION ALL``.
#
# For signals that carry a PopulationCriteria the WHERE clause combines both:
#   WHERE <population_criteria> AND (<criteria>)
# ---------------------------------------------------------------------------

REVIEW_QUERIES: list[tuple[str, str, bool]] = [
    # ------------------------------------------------------------------
    # ATOWorkerActions
    # ------------------------------------------------------------------
    (
        'ATOWorkerActions',
        (
            '-- ATOWorkerActions\n'
            'WITH data AS (\n'
            'SELECT "schema" namespace, "table" table_name, alter_table_type, status, alter_from, event_time\n'
            'FROM (SELECT\n'
            '    "schema",  "table",  alter_table_type,\n'
            '    status, trim(alter_from) alter_from, event_time,\n'
            '    ROW_NUMBER() OVER (PARTITION BY o.table_id, o.alter_table_type ORDER BY event_time DESC) rownum\n'
            '  FROM SYS_AUTO_TABLE_OPTIMIZATION o\n'
            '  JOIN SVV_TABLE_INFO t on o.table_id = t.table_id\n'
            ') ato where rownum = 1\n'
            ')\n'
            '-- Signal: column encoding on table is not set to auto\n'
            "SELECT count(*), 'REC_004'\n"
            'FROM data\n'
            "WHERE trim(status) != 'Abort:This table is already the recommended style.' and trim(status) != 'Complete: 100%' AND (alter_table_type='encode')\n"
            'UNION ALL\n'
            '-- Signal: distribution style on table is not set to auto\n'
            "SELECT count(*), 'REC_008'\n"
            'FROM data\n'
            "WHERE trim(status) != 'Abort:This table is already the recommended style.' and trim(status) != 'Complete: 100%' AND (alter_table_type='distkey')\n"
            'UNION ALL\n'
            '-- Signal: sort key on table is not set to auto\n'
            "SELECT count(*), 'REC_007'\n"
            'FROM data\n'
            "WHERE trim(status) != 'Abort:This table is already the recommended style.' and trim(status) != 'Complete: 100%' AND (alter_table_type='sortkey')\n"
        ),
        False,
    ),
    # ------------------------------------------------------------------
    # AlterTableRecommendations
    # ------------------------------------------------------------------
    (
        'AlterTableRecommendations',
        (
            '-- AlterTableRecommendations\n'
            'WITH data AS (\n'
            'SELECT "database" db,\n'
            '       "schema" namespace,\n'
            '       "table" table_name,\n'
            '       type,\n'
            '       ddl,\n'
            '       auto_eligible\n'
            'FROM SVV_ALTER_TABLE_RECOMMENDATIONS\n'
            'JOIN SVV_TABLE_INFO using(table_id, database)\n'
            ')\n'
            '-- Signal: column encoding recommendation on table is not automatically applied\n'
            "SELECT count(*), 'REC_004'\n"
            'FROM data\n'
            "WHERE type='encode' and auto_eligible='f'\n"
            'UNION ALL\n'
            '-- Signal: sort key recommendation on table is not automatically applied\n'
            "SELECT count(*), 'REC_007'\n"
            'FROM data\n'
            "WHERE type='sortkey' and auto_eligible='f'\n"
            'UNION ALL\n'
            '-- Signal: dist key recommendation on table is not automatically applied\n'
            "SELECT count(*), 'REC_008'\n"
            'FROM data\n'
            "WHERE type='diststyle' and auto_eligible='f'\n"
        ),
        False,
    ),
    # ------------------------------------------------------------------
    # CopyPerformance
    # ------------------------------------------------------------------
    (
        'CopyPerformance',
        (
            '-- CopyPerformance\n'
            'WITH data AS (\n'
            'SELECT \n'
            '  end_time::DATE AS copy_date,\n'
            '  database_name db, \n'
            '  table_name, \n'
            "  split_part(data_source, '/', 3) s3_bucket,\n"
            '  file_format, \n'
            '  sum(case when splits > source_file_count then 1 else 0 end) split_copies,\n'
            '  sum(loaded_rows) rows_inserted, \n'
            '  sum(source_file_count) files_scanned, \n'
            '  sum((file_bytes_scanned/1000000)::int) mb_scanned,\n'
            '  avg(loaded_rows/(duration/1000000::decimal(18,2))) insert_rate_rows_per_second,\n'
            '  avg(source_file_count) avg_files_per_copy,\n'
            '  avg(file_bytes_scanned/source_file_count)::decimal(18,2) avg_file_size_mb,\n'
            '  avg(file_bytes_scanned/(duration/1000000::decimal(18,2))) avg_scan_kbps,\n'
            '  count(distinct query_id) no_of_copy,\n'
            '  max(query_id) sample_query,\n'
            '  sum(duration/1000000)::decimal(18,2) total_copy_time_secs,\n'
            '  avg(duration/1000000)::decimal(18,2) avg_copy_time_secs,\n'
            '  sum(error_count) error_count\n'
            'FROM SYS_LOAD_HISTORY join (\n'
            '  select user_id, query_id, \n'
            '    sum(splits_scanned) splits\n'
            '  from SYS_LOAD_DETAIL \n'
            '  group by 1,2) using (USER_ID, QUERY_ID)\n'
            'where loaded_rows > 0\n'
            'group by 1,2,3,4,5\n'
            ')\n'
            '-- Signal: files per copy are less than slice count\n'
            "SELECT count(*), 'REC_023'\n"
            'FROM data\n'
            'WHERE no_of_copy > 24 AND (avg_files_per_copy < 64)\n'
            'UNION ALL\n'
            '-- Signal: files with a small size\n'
            "SELECT count(*), 'REC_023'\n"
            'FROM data\n'
            'WHERE no_of_copy > 24 AND (avg_file_size_mb < 10)\n'
        ),
        False,
    ),
    # ------------------------------------------------------------------
    # DataShareConsumerUsage
    # ------------------------------------------------------------------
    (
        'DataShareConsumerUsage',
        (
            '-- DataShareConsumerUsage\n'
            'WITH usage as (SELECT \n'
            '    database_name,\n'
            '    user_name,\n'
            '    transaction_id,\n'
            '    request_id,\n'
            '    query_id,\n'
            '    min(record_time) over (partition by user_id, session_id, transaction_id) request_start_date,\n'
            '    max(record_time) over (partition by user_id, session_id, transaction_id) request_end_date,\n'
            '    request_start_date::date request_date,\n'
            '    round(execution_time/1000000.0,2) query_execution_secs,\n'
            "    round(datediff('milliseconds', min(record_time) over (partition by user_id, session_id, transaction_id), max(record_time) over(partition by user_id, session_id, transaction_id))/1000.0,2) as request_duration_secs,\n"
            "    case when trim(nvl(error_message,'')) = '' then 0 else 1 end error_cnt,\n"
            "    round(datediff('milliseconds',request_end_date,start_time)/1000.0, 2)  as request_interval_secs,\n"
            "    round(datediff('milliseconds',request_start_date,end_time)/1000.0, 2)  as execution_secs\n"
            'FROM SYS_DATASHARE_USAGE_CONSUMER \n'
            'JOIN SYS_QUERY_HISTORY using (user_id, session_id, transaction_id)\n'
            'JOIN SVV_USER_INFO using (user_id)), \n'
            'perc as (SELECT\n'
            '    request_date,\n'
            '    database_name, \n'
            '    user_name,\n'
            '    percentile_cont(0.8) within GROUP ( ORDER BY request_duration_secs) AS p80_request_sec,\n'
            '    percentile_cont(0.9) within GROUP ( ORDER BY request_duration_secs) AS p90_request_sec,\n'
            '    percentile_cont(0.99) within GROUP ( ORDER BY request_duration_secs) AS p99_request_sec\n'
            'FROM usage\n'
            'group by 1,2,3),\n'
            'data as (\n'
            'select \n'
            '    request_date, \n'
            '    database_name db,\n'
            '    user_name,\n'
            '    count(distinct query_id) query_count,\n'
            '    avg(query_execution_secs) as avg_query_execution_secs,\n'
            '    sum(query_execution_secs) as total_query_execution_secs, \n'
            '    avg(execution_secs)::decimal(18,2) as avg_execution_secs,\n'
            '    sum(execution_secs)::decimal(18,2) as total_execution_secs, \n'
            '    avg(request_duration_secs) as avg_request_duration_secs,\n'
            '    min(p80_request_sec) p80_request_sec,\n'
            '    min(p90_request_sec) p90_request_sec, \n'
            '    min(p99_request_sec) p99_request_sec,\n'
            '    sum(request_duration_secs) as total_request_duration_secs, \n'
            '    avg(request_interval_secs) as avg_request_interval_secs,\n'
            '    sum(request_interval_secs) as total_request_interval_secs,\n'
            '    count(distinct transaction_id) total_unique_transaction,\n'
            '    count(distinct request_id) total_usage_consumer_count,\n'
            '    sum(error_cnt) total_request_error_count\n'
            'FROM usage join perc using(request_date, database_name, user_name)\n'
            'GROUP BY 1,2,3\n'
            ')\n'
            '-- Signal: long running metadata sync\n'
            "SELECT count(*), 'REC_028'\n"
            'FROM data\n'
            'WHERE avg_request_duration_secs > 60\n'
            'UNION ALL\n'
            "SELECT count(*), 'REC_034'\n"
            'FROM data\n'
            'WHERE avg_request_duration_secs > 60\n'
        ),
        False,
    ),
    # ------------------------------------------------------------------
    # DataShareProducerObject
    # ------------------------------------------------------------------
    (
        'DataShareProducerObject',
        (
            '-- DataShareProducerObject\n'
            'WITH data AS (\n'
            'SELECT d.share_type,\n'
            '    d.share_name,\n'
            '    d.include_new,\n'
            '    d.producer_account,\n'
            '    d.object_type,\n'
            "    split_part(d.object_name, '.', 1) namespace,\n"
            "    split_part(d.object_name, '.', 2) table_name,\n"
            '    ti.estimated_visible_rows,\n'
            '    vi.record_time last_vacuum_date,\n'
            '    vi.vacuum_type,\n'
            '    mi.is_stale mv_is_stale,\n'
            "    CASE WHEN mi.state = 1 THEN 'Y' WHEN mi.state <> 1 THEN 'N' ELSE NULL END AS is_mv_incremental_refresh,\n"
            "    CASE WHEN mi.autorefresh = 1 THEN 'Y' WHEN mi.autorefresh <> 1 THEN 'N' ELSE NULL END AS is_mv_auto_refresh\n"
            'FROM SVV_DATASHARE_OBJECTS d\n'
            'LEFT OUTER JOIN SVV_TABLE_INFO ti ON (split_part(d.object_name, \'.\', 1) = ti."schema" and split_part(d.object_name, \'.\', 2) = ti."table" and current_database() = ti."database")\n'
            'LEFT OUTER JOIN SVV_MV_INFO mi ON (ti."database" = mi.database_name and ti."schema" = mi."schema_name" and ti."table" = mi."name")\n'
            'LEFT OUTER JOIN (SELECT record_time, table_id, table_name, status, vacuum_type,\n'
            '    row_number() over (PARTITION BY table_id order by record_time desc) rownum\n'
            '    FROM SYS_VACUUM_HISTORY \n'
            "    WHERE status != 'Skipped') vi on ti.table_id = vi.table_id and vi.rownum = 1\n"
            "WHERE share_type = 'OUTBOUND' and object_type = 'table'\n"
            'ORDER BY 2,3,5,4\n'
            ')\n'
            '-- Signal: materialized view shared by a producer is doing a full refresh\n'
            "SELECT count(*), 'REC_034'\n"
            'FROM data\n'
            "WHERE is_mv_incremental_refresh = 'N'\n"
        ),
        False,
    ),
    # ------------------------------------------------------------------
    # ExtQueryPerformance
    # ------------------------------------------------------------------
    (
        'ExtQueryPerformance',
        (
            '-- ExtQueryPerformance\n'
            'WITH data AS (\n'
            "SELECT source_type, split_part(table_name,'.',1) db, \n"
            "    case when split_part(table_name,'.',2) like 'pg_temp%' then 'pg_temp' else split_part(table_name,'.',2) end AS namespace,\n"
            "    case when namespace = 'pg_temp' then\n"
            "        substring(split_part(table_name,'.',3),1,len(split_part(table_name,'.',3))-14)\n"
            "        else split_part(table_name,'.',3) end AS external_table_name,\n"
            '    file_format,\n'
            "    split_part(file_location, '/', 3) s3_bucket,\n"
            "    CASE WHEN nvl(total_partitions,1) > 1 THEN 'Y' ELSE 'N' END AS is_table_partitioned,\n"
            '    nvl(max(total_partitions),1) AS external_table_partition_count,\n'
            '    COUNT(1) total_query_count,\n'
            '    SUM(CASE WHEN nvl(qualified_partitions,1) < nvl(total_partitions,1) THEN 1 ELSE 0 END) total_query_using_Partition_Pruning_count,\n'
            '    (total_query_using_Partition_Pruning_count / total_query_count)*100 AS pct_of_query_using_Partition_Pruning,\n'
            '    nvl(AVG(qualified_partitions),1) AS avg_Qualified_Partitions,\n'
            '    nvl(avg(scanned_files),0) AS avg_Files,\n'
            '    AVG(case when nvl(scanned_files,0) > 0 then (returned_bytes/scanned_files/1000000.0)::decimal(18,2) else 0 end) AS avg_file_size_mb,\n'
            '    AVG(duration / 1000000.0)::decimal(18,2) avg_Elapsed_sec,\n'
            '    SUM(duration / 1000000.0)::decimal(18,2) Total_Elapsed_sec,\n'
            '    SUM(nvl(error_cnt,0)) AS total_scan_error_count,\n'
            '    AVG(nvl(error_cnt,0)) AS avg_scan_error_count\n'
            'FROM SYS_EXTERNAL_QUERY_DETAIL \n'
            'LEFT JOIN (select user_id, query_id, count(1) error_cnt FROM SYS_EXTERNAL_QUERY_ERROR GROUP BY 1,2) e USING (user_id, query_id)\n'
            "WHERE table_name != '..' and table_name != '' and duration > 0\n"
            'group by 1,2,3,4,5,6,7\n'
            ')\n'
            '-- Signal: high count of long queries not using partition pruning\n'
            "SELECT count(*), 'REC_027'\n"
            'FROM data\n'
            'WHERE avg_qualified_partitions > 100 and avg_elapsed_sec > 60 AND (pct_of_query_using_partition_pruning < 95)\n'
        ),
        False,
    ),
    # ------------------------------------------------------------------
    # MaterializedView
    # ------------------------------------------------------------------
    (
        'MaterializedView',
        (
            '-- MaterializedView\n'
            'WITH data AS (\n'
            'SELECT \n'
            '  database_name db, schema_name namespace, user_name, name, is_stale, state, autorewrite, autorefresh, \n'
            '  CASE state\n'
            "    WHEN 0 THEN 'The MV is fully recomputed when refreshed'\n"
            "    WHEN 1 THEN 'The MV is incremental'\n"
            "    WHEN 101 THEN 'The MV cant be refreshed due to a dropped column. This constraint applies even if the column is not used in the MV'\n"
            "    WHEN 102 THEN 'The MV cant be refreshed due to a changed column type. This constraint applies even if the column is not used in the MV'\n"
            "    WHEN 103 THEN 'The MV cant be refreshed due to a renamed table'\n"
            "    WHEN 104 THEN 'The MV cant be refreshed due to a renamed column. This constraint applies even if the column is not used in the MV'\n"
            "    WHEN 105 THEN 'The MV cant be refreshed due to a renamed schema'\n"
            '    ELSE NULL\n'
            '  END AS state_desc,\n'
            '  mv_state, event_desc, event_starttime,\n'
            '  refresh_db_username, refresh_status, refresh_type, refresh_starttime, refresh_endtime, refresh_duration_secs\n'
            'FROM SVV_MV_INFO \n'
            'LEFT JOIN (SELECT database_name, mv_schema schema_name, mv_name name,\n'
            '  state AS mv_state, event_desc, start_time event_starttime \n'
            '  FROM SYS_MV_STATE s\n'
            '  QUALIFY ROW_NUMBER() OVER (PARTITION BY database_name, schema_name, mv_name ORDER BY start_time DESC) = 1)  \n'
            '  USING (database_name, schema_name, name)\n'
            'LEFT JOIN (SELECT database_name, schema_name, mv_name name, user_name refresh_db_username,\n'
            '    status refresh_status, refresh_type, start_time refresh_starttime, end_time refresh_endtime, duration/1000000 refresh_duration_secs\n'
            '  FROM SYS_MV_REFRESH_HISTORY h\n'
            '  JOIN SVV_USER_INFO u using (user_id)\n'
            '  QUALIFY ROW_NUMBER() OVER (PARTITION BY database_name, schema_name, mv_name ORDER BY start_time DESC) = 1\n'
            ") USING (database_name, schema_name, name) WHERE SVV_MV_INFO.schema_name <> 'pg_automv'\n"
            ')\n'
            '-- Signal: materialized view is doing a full refresh\n'
            "SELECT count(*), 'REC_030'\n"
            'FROM data\n'
            'WHERE state=0\n'
            'UNION ALL\n'
            '-- Signal: materialized view cannot be auto refreshed\n'
            "SELECT count(*), 'REC_031'\n"
            'FROM data\n'
            "WHERE state > 1 and is_stale = 't' and autorefresh = 'y'\n"
            'UNION ALL\n'
            '-- Signal: materialized view is stale\n'
            "SELECT count(*), 'REC_039'\n"
            'FROM data\n'
            "WHERE is_stale = 't'\n"
        ),
        False,
    ),
    # ------------------------------------------------------------------
    # NodeDetails (provisioned only)
    # ------------------------------------------------------------------
    (
        'NodeDetails',
        (
            '-- NodeDetails\n'
            'WITH data AS (\n'
            'SELECT CASE\n'
            "       WHEN capacity = 190633 THEN 'dc2.large'\n"
            "       WHEN capacity = 760956 THEN 'dc2.8xlarge'\n"
            "       WHEN capacity = 726296 THEN 'dc2.8xlarge'\n"
            "       WHEN capacity = 952455 THEN 'ds2.xlarge'\n"
            "       WHEN capacity = 945026 THEN 'ds2.8xlarge'\n"
            "       WHEN capacity < 2002943 THEN 'ra3.large'\n"
            "       WHEN capacity = 2002943 AND part_count = 1 THEN 'ra3.xlplus'\n"
            "       WHEN capacity > 2002943 AND part_count = 1 THEN 'ra3.4xlarge'\n"
            "       WHEN capacity > 2002943 AND part_count = 4 THEN 'ra3.16xlarge'\n"
            "       ELSE 'unknown'\n"
            '       END AS node_type,\n'
            '       s.node,\n'
            '       slice_count,\n'
            '       storage_utilization_pct,\n'
            '       storage_capacity_gb,\n'
            '       storage_used_gb\n'
            'FROM (SELECT distinct p.host node, p.capacity, count(1) part_count FROM stv_partitions p WHERE host = owner GROUP BY 1,2) AS s\n'
            "INNER JOIN (SELECT node,COUNT(1) AS slice_count FROM stv_slices WHERE type='D' GROUP BY node) n ON (s.node = n.node)\n"
            'INNER JOIN (SELECT node,\n'
            '       ROUND((used::decimal(18,2)/capacity)*100,2) AS storage_utilization_pct,\n'
            '       (capacity::decimal(18,2)/1000) AS storage_capacity_gb,\n'
            '       (used::decimal(18,2)/1000) AS storage_used_gb\n'
            '  FROM stv_node_storage_capacity) ns ON (s.node = ns.node)\n'
            'ORDER by 2\n'
            ')\n'
            '-- Signal: exceeds the recommended storage threshold of 70%\n'
            "SELECT count(*), 'REC_001'\n"
            'FROM data\n'
            "WHERE storage_utilization_pct > 70 and (node_type like 'dc%' or node_type like 'ds%')\n"
            'UNION ALL\n'
            "SELECT count(*), 'REC_002'\n"
            'FROM data\n'
            "WHERE storage_utilization_pct > 70 and (node_type like 'dc%' or node_type like 'ds%')\n"
            'UNION ALL\n'
            "SELECT count(*), 'REC_004'\n"
            'FROM data\n'
            "WHERE storage_utilization_pct > 70 and (node_type like 'dc%' or node_type like 'ds%')\n"
            'UNION ALL\n'
            "SELECT count(*), 'REC_005'\n"
            'FROM data\n'
            "WHERE storage_utilization_pct > 70 and (node_type like 'dc%' or node_type like 'ds%')\n"
            'UNION ALL\n'
            "SELECT count(*), 'REC_006'\n"
            'FROM data\n'
            "WHERE storage_utilization_pct > 70 and (node_type like 'dc%' or node_type like 'ds%')\n"
            'UNION ALL\n'
            '-- Signal: has under-utilized storage\n'
            "SELECT count(*), 'REC_012'\n"
            'FROM data\n'
            "WHERE storage_utilization_pct < 40 and not node_type like 'ra3%'\n"
            'UNION ALL\n'
            '-- Signal: has 10% data skew\n'
            "SELECT count(*), 'REC_008'\n"
            'FROM data\n'
            'WHERE 100*abs(storage_used_gb - (select min(storage_used_gb) from data))/storage_used_gb >= 10\n'
            'UNION ALL\n'
            '-- Signal: are using a legacy node type\n'
            "SELECT count(*), 'REC_001'\n"
            'FROM data\n'
            "WHERE node_type like 'dc1%' or node_type like 'ds2%'\n"
        ),
        True,
    ),
    # ------------------------------------------------------------------
    # TableInfo
    # ------------------------------------------------------------------
    (
        'TableInfo',
        (
            '-- TableInfo\n'
            'WITH data AS (\n'
            'SELECT\n'
            '  "database" db, \n'
            '  "schema" namespace, \n'
            '  "table" table_name,\n'
            '  max_varchar,\n'
            '  sortkey1,\n'
            '  tbl_rows,\n'
            '  skew_rows,\n'
            '  diststyle,\n'
            '  vacuum_sort_benefit,\n'
            '  stats_off,\n'
            '  sortkey1_enc,\n'
            '  sortkey_num,\n'
            '  CASE WHEN t.tbl_rows - t.estimated_visible_rows < 0 THEN 0 ELSE (t.tbl_rows - t.estimated_visible_rows) END  num_rows_marked_for_deletion,\n'
            '  case when nvl(tbl_rows,0) = 0 then 0 else (nvl(num_rows_marked_for_deletion,0) / nvl(tbl_rows,0))*100::decimal(18,2) end pct_rows_marked_for_deletion,\n'
            '  encoded_column_pct,\n'
            '  column_count,\n'
            '  encoded_column_count\n'
            'From SVV_TABLE_INFO T\n'
            'JOIN (SELECT attrelid,\n'
            '  COUNT(1) column_count,\n'
            '  Sum(CASE WHEN attisdistkey = false THEN 0 ELSE 1 END) distkey_column_count,\n'
            '  Sum(CASE WHEN attencodingtype IN ( 0, 128 ) THEN 0 ELSE 1 END) encoded_column_count,\n'
            '  Sum(CASE WHEN attencodingtype NOT IN ( 0, 128 ) AND attsortkeyord > 0 THEN 0 ELSE 1 END) encoded_sortkey_count,\n'
            '  ((encoded_column_count::decimal / column_count)*100)::int encoded_column_pct\n'
            'FROM   pg_attribute\n'
            'WHERE  attnum > 0\n'
            'GROUP  BY attrelid) c ON c.attrelid = t.table_id\n'
            "where \"schema\" not in ('information_schema', 'pg_catalog', 'pg_automv', 'pg_internal') and \"database\" not in ('sample_data_dev')\n"
            ')\n'
            '-- Signal: tables with wide columns\n'
            "SELECT count(*), 'REC_011'\n"
            'FROM data\n'
            'WHERE max_varchar > 1000\n'
            'UNION ALL\n'
            '-- Signal: large tables without a sort key\n'
            "SELECT count(*), 'REC_007'\n"
            'FROM data\n'
            "WHERE tbl_rows > 5000000 and sortkey1 != 'AUTO(SORTKEY%' AND (sortkey1 = '')\n"
            'UNION ALL\n'
            '-- Signal: large tables with skew\n'
            "SELECT count(*), 'REC_008'\n"
            'FROM data\n'
            "WHERE tbl_rows > 5000000 AND (skew_rows >= 4 and diststyle not like 'AUTO%')\n"
            'UNION ALL\n'
            '-- Signal: large tables with unsorted data\n'
            "SELECT count(*), 'REC_013'\n"
            'FROM data\n'
            'WHERE tbl_rows > 5000000 AND (vacuum_sort_benefit >= 10)\n'
            'UNION ALL\n'
            '-- Signal: tables with interleaved sort keys\n'
            "SELECT count(*), 'REC_014'\n"
            'FROM data\n'
            "WHERE tbl_rows > 5000000 AND (sortkey1 like '%INTERLEAVED%')\n"
            'UNION ALL\n'
            '-- Signal: small tables without an ALL distribution\n'
            "SELECT count(*), 'REC_008'\n"
            'FROM data\n'
            "WHERE tbl_rows <= 5000000 and diststyle not like 'AUTO%' AND (diststyle not like '%ALL%')\n"
            'UNION ALL\n'
            '-- Signal: small tables with a sort key\n'
            "SELECT count(*), 'REC_007'\n"
            'FROM data\n'
            "WHERE tbl_rows <= 5000000 and sortkey1 not like 'AUTO(SORTKEY%' AND (sortkey1 != '')\n"
            'UNION ALL\n'
            '-- Signal: large tables needing a vacuum delete\n'
            "SELECT count(*), 'REC_002'\n"
            'FROM data\n'
            'WHERE tbl_rows > 5000000 AND (pct_rows_marked_for_deletion > 10)\n'
            'UNION ALL\n'
            '-- Signal: tables with out of date statistics\n'
            "SELECT count(*), 'REC_003'\n"
            'FROM data\n'
            'WHERE stats_off > 10 or stats_off is null\n'
            'UNION ALL\n'
            '-- Signal: large tables with encoded sort keys\n'
            "SELECT count(*), 'REC_010'\n"
            'FROM data\n'
            "WHERE tbl_rows > 5000000 and not sortkey1 like 'AUTO(SORTKEY%' AND (sortkey1_enc != 'none' and sortkey1_enc != '')\n"
            'UNION ALL\n'
            '-- Signal: tables with low column compression\n'
            "SELECT count(*), 'REC_004'\n"
            'FROM data\n'
            "WHERE ((column_count - encoded_column_count) - (case when sortkey1_enc = 'none' or sortkey1_enc = '' then 1 else 0 end)) AND tbl_rows > 5000000 AND (encoded_column_pct < 80)\n"
            'UNION ALL\n'
            '-- Signal: large tables distributed by date or datetime\n'
            "SELECT count(*), 'REC_008'\n"
            'FROM data\n'
            "WHERE tbl_rows > 5000000 AND (diststyle like '%KEY%date%' or diststyle like '%KEY%dt%' or diststyle like '%KEY%timestamp%' or diststyle like '%KEY%datetime%')\n"
        ),
        False,
    ),
    # ------------------------------------------------------------------
    # Top50QueriesByRunTime
    # ------------------------------------------------------------------
    (
        'Top50QueriesByRunTime',
        (
            '-- Top50QueriesByRunTime\n'
            'WITH a as (\n'
            'SELECT  \n'
            '  database_name db, \n'
            '  user_name,\n'
            '  generic_query_hash,\n'
            '  query_id,\n'
            '  (execution_time/1000000) execution_time_sec,\n'
            '  count(1) over(partition by generic_query_hash) query_cnt,\n'
            '  avg(compile_time/1000000) over(partition by generic_query_hash) compile_time_sec, \n'
            '  avg(planning_time/1000000) over(partition by generic_query_hash) planning_time_sec,\n'
            '  avg(lock_wait_time/1000000) over(partition by generic_query_hash) lock_wait_time_sec,\n'
            '  avg(elapsed_time/1000000) over(partition by generic_query_hash) elapsed_time_sec,\n'
            '  avg(queue_time/1000000) over(partition by generic_query_hash) queue_time_sec,\n'
            '  avg(ROUND((queue_time*1.0/elapsed_time)*100,2)) over(partition by generic_query_hash) pct_wlm_queue_time,\n'
            '  service_class_id,\n'
            '  service_class_name,\n'
            '  query_type,\n'
            "  replace(error_message, '''', '\\\\''') error_message, \n"
            '  query_priority, \n'
            '  compute_type\n'
            'FROM SYS_QUERY_HISTORY \n'
            'JOIN SVV_USER_INFO using (user_id) \n'
            "WHERE user_id > 1 and service_class_id >= 5 and query_type != 'DDL' and execution_time > 1000000\n"
            'QUALIFY ROW_NUMBER() OVER (PARTITION BY generic_query_hash ORDER BY execution_time DESC) = 1\n'
            'order by execution_time_sec desc\n'
            'limit 50), \n'
            'b as (select query_id,\n'
            "  max(case when is_rrscan = 't' then 1 else 0 end) rrscan,\n"
            '  max(case when spilled_block_local_disk > 0 or spilled_block_remote_disk > 0 then 1 else 0 end) disk_spill,\n'
            '  max(case when spilled_block_local_disk > 0 then 1 else 0 end) local_disk_spill,\n'
            '  max(case when spilled_block_remote_disk > 0 then 1 else 0 end) remote_disk_spill,\n'
            '  max(case when spilled_block_local_disk > 0 then spilled_block_local_disk else 0 end) local_disk_spill_mb,\n'
            '  max(case when spilled_block_remote_disk > 0 then spilled_block_remote_disk else 0 end) remote_disk_spill_mb,\n'
            '  listagg(distinct case \n'
            "    when step_name = 'nestloop' and output_rows > 5000000 then 'Large nljoin' \n"
            "    when step_name = 'scan' and input_rows >5000000 and is_rrscan = 'f' and output_rows< (.25*input_rows) then 'Scanning unsorted data'\n"
            "    when step_name = 'broadcast' and output_rows >5000000 then 'Large broadcast'\n"
            "    when step_name = 'distribute' and output_rows >5000000 then 'Large distribution'\n"
            "    when alert like '%statistics%' then 'Missing statistics'\n"
            "    else alert end, ', ') alerts,\n"
            "  listagg(distinct case when table_name not like '%..%' and table_name != '' then table_name end, ', ') table_list,\n"
            '  local_disk_spill_mb + remote_disk_spill_mb total_disk_spill_mb\n'
            'from SYS_QUERY_DETAIL join a using (query_id)\n'
            'group by 1),\n'
            'data as (\n'
            'select \n'
            '  a.*,\n'
            '  b.alerts, b.rrscan, b.disk_spill, b.local_disk_spill, b.remote_disk_spill, b.local_disk_spill_mb, b.remote_disk_spill_mb, b.table_list, b.total_disk_spill_mb  \n'
            'FROM a LEFT JOIN b on a.query_id = b.query_id\n'
            'order by execution_time_sec desc\n'
            ')\n'
            '-- Signal: long running queries with missing Table Statistics\n'
            "SELECT count(*), 'REC_003'\n"
            'FROM data\n'
            "WHERE lower(alerts) like '%stat%'\n"
            'UNION ALL\n'
            '-- Signal: long running queries using Nested Loop Joins\n'
            "SELECT count(*), 'REC_009'\n"
            'FROM data\n'
            "WHERE lower(alerts) like '%nl%'\n"
            'UNION ALL\n'
            "SELECT count(*), 'REC_022'\n"
            'FROM data\n'
            "WHERE lower(alerts) like '%nl%'\n"
            'UNION ALL\n'
            '-- Signal: long running queries with Dist or Broadcast alerts\n'
            "SELECT count(*), 'REC_008'\n"
            'FROM data\n'
            "WHERE lower(alerts) like '%dist%' or lower(alerts) like '%broadcast%'\n"
            'UNION ALL\n'
            '-- Signal: long running queries with Sort alerts\n'
            "SELECT count(*), 'REC_007'\n"
            'FROM data\n'
            "WHERE lower(alerts) like '%sort%'\n"
            'UNION ALL\n'
            '-- Signal: high count of queries with large disk spill\n'
            "SELECT count(*), 'REC_005'\n"
            'FROM data\n'
            'WHERE total_disk_spill_mb > 100\n'
            'UNION ALL\n'
            "SELECT count(*), 'REC_011'\n"
            'FROM data\n'
            'WHERE total_disk_spill_mb > 100\n'
            'UNION ALL\n'
            "SELECT count(*), 'REC_022'\n"
            'FROM data\n'
            'WHERE total_disk_spill_mb > 100\n'
            'UNION ALL\n'
            "SELECT count(*), 'REC_024'\n"
            'FROM data\n'
            'WHERE total_disk_spill_mb > 100\n'
        ),
        False,
    ),
    # ------------------------------------------------------------------
    # UsagePattern
    # ------------------------------------------------------------------
    (
        'UsagePattern',
        (
            '-- UsagePattern\n'
            'WITH data AS (\n'
            'SELECT\n'
            "  date_trunc('hour',start_time) as workload_exec_hour, \n"
            '  service_class_id,\n'
            '  service_class_name,\n'
            '  count(1) query_count,\n'
            "  sum(case when query_type = 'COPY' then 1 else 0 end) copy_count,\n"
            "  sum(case when query_type = 'INSERT' then 1 else 0 end) insert_count,\n"
            "  sum(case when query_type = 'UPDATE' then 1 else 0 end) update_count,\n"
            "  sum(case when query_type = 'DDL' then 1 else 0 end) ddl_count,\n"
            "  sum(case when query_type = 'CTAS' then 1 else 0 end) ctas_count,\n"
            '  sum(case when result_cache_hit then 1 else 0 end) result_cache_hits,\n'
            '  sum(case when queue_time > 0 then 1 else 0 end) queued_queries,\n'
            "  sum(case when nvl(error_message,'') = '' then 0 else 1 end) error_queries,\n"
            "  sum(case when compute_type != 'primary' then 1 else 0 end) burst_queries,\n"
            "  sum(case when compute_type != 'primary' then execution_time/1000000.0 else 0 end)::decimal(18,2) burst_secs,\n"
            '  sum(case when compile_time > 0 then 1 else 0 end) compiled_queries,\n'
            '  sum(queue_time/1000000)::decimal(18,2) total_queue_time,\n'
            '  sum(compile_time/1000000)::decimal(18,2) total_compile_time,\n'
            '  sum(planning_time/1000000)::decimal(18,2) total_planning_time,\n'
            '  sum(lock_wait_time/1000000)::decimal(18,2) total_lock_wait_time,\n'
            '  sum(elapsed_time/1000000)::decimal(18,2) total_query_elapsed_time,\n'
            '  case when total_query_elapsed_time > 0 then ROUND((total_queue_time*1.0/total_query_elapsed_time)*100,2) else 0 end pct_wlm_queue_time,\n'
            "  sum(case when query_priority in ('low', 'lowest') then 1 else 0 end) low_priority_query_cnt,\n"
            "  sum(case when query_priority in ('high', 'highest') then 1 else 0 end) high_priority_query_cnt,\n"
            "  sum(case when short_query_accelerated = 'true' then 1 else 0 end) sqa_queries,\n"
            '  sum(rrscan_queries) rrscan_queries,\n'
            '  sum(disk_spill) total_disk_spill_count,\n'
            '  sum(local_disk_spill) local_disk_spill_count,\n'
            '  sum(remote_disk_spill) remote_disk_spill_count,\n'
            '  sum(local_disk_spill_mb) total_local_disk_spill_mb,\n'
            '  sum(remote_disk_spill_mb) total_remote_disk_spill_mb,\n'
            '  sum(case when approx_rows_inserted between 1 and 100 then 1 else 0 end) small_insert_count\n'
            'FROM SYS_QUERY_HISTORY \n'
            'LEFT JOIN (select query_id,\n'
            "  max(case when is_rrscan = 't' then 1 else 0 end) rrscan_queries,\n"
            '  max(case when spilled_block_local_disk > 0 or spilled_block_remote_disk > 0 then 1 else 0 end) disk_spill,\n'
            '  max(case when spilled_block_local_disk > 0 then 1 else 0 end) local_disk_spill,\n'
            '  max(case when spilled_block_remote_disk > 0 then 1 else 0 end) remote_disk_spill,\n'
            '  max(case when spilled_block_local_disk > 0 then spilled_block_local_disk else 0 end) local_disk_spill_mb,\n'
            '  max(case when spilled_block_remote_disk > 0 then spilled_block_remote_disk else 0 end) remote_disk_spill_mb,\n'
            "   sum(case when step_name = 'insert' then output_rows else 0 end) approx_rows_inserted\n"
            'from SYS_QUERY_DETAIL\n'
            'group by 1) SYS_QUERY_DETAIL using (QUERY_ID)\n'
            'where user_id > 1 and service_class_id >= 5\n'
            'group by 1,2,3\n'
            ')\n'
            '-- Signal: high count of COPY command\n'
            "SELECT count(*), 'REC_023'\n"
            'FROM data\n'
            'WHERE copy_count > 100\n'
            'UNION ALL\n'
            '-- Signal: high count of small_insert statements\n'
            "SELECT count(*), 'REC_029'\n"
            'FROM data\n'
            'WHERE small_insert_count > 100\n'
            'UNION ALL\n'
            '-- Signal: high count of DDL command\n'
            "SELECT count(*), 'REC_025'\n"
            'FROM data\n'
            'WHERE ddl_count > 10\n'
            'UNION ALL\n'
            '-- Signal: high count of CTAS command\n'
            "SELECT count(*), 'REC_025'\n"
            'FROM data\n'
            'WHERE ctas_count > 10\n'
            'UNION ALL\n'
            '-- Signal: high count of WLM queuing\n'
            "SELECT count(*), 'REC_019'\n"
            'FROM data\n'
            'WHERE pct_wlm_queue_time > 5\n'
            'UNION ALL\n'
            "SELECT count(*), 'REC_020'\n"
            'FROM data\n'
            'WHERE pct_wlm_queue_time > 5\n'
            'UNION ALL\n'
            "SELECT count(*), 'REC_026'\n"
            'FROM data\n'
            'WHERE pct_wlm_queue_time > 5\n'
            'UNION ALL\n'
            '-- Signal: high count of spilled to disk\n'
            "SELECT count(*), 'REC_005'\n"
            'FROM data\n'
            'WHERE total_disk_spill_count > 10\n'
            'UNION ALL\n'
            "SELECT count(*), 'REC_011'\n"
            'FROM data\n'
            'WHERE total_disk_spill_count > 10\n'
            'UNION ALL\n'
            "SELECT count(*), 'REC_022'\n"
            'FROM data\n'
            'WHERE total_disk_spill_count > 10\n'
            'UNION ALL\n'
            "SELECT count(*), 'REC_024'\n"
            'FROM data\n'
            'WHERE total_disk_spill_count > 10\n'
            'UNION ALL\n'
            '-- Signal: high count of compiled\n'
            "SELECT count(*), 'REC_025'\n"
            'FROM data\n'
            'WHERE compiled_queries > 100\n'
            'UNION ALL\n'
            '-- Signal: high concurrency scaling usage\n'
            "SELECT count(*), 'REC_033'\n"
            'FROM data\n'
            'WHERE burst_secs > 600\n'
        ),
        False,
    ),
    # ------------------------------------------------------------------
    # WLMConfig (provisioned only)
    # ------------------------------------------------------------------
    (
        'WLMConfig',
        (
            '-- WLMConfig\n'
            'WITH data AS (\n'
            'SELECT \n'
            "       min(case when scc.service_class >= 100 then 'auto' else 'manual' end) over (partition by null) wlm_mode,\n"
            '       scc.service_class::text AS service_class_id,\n'
            '       CASE\n'
            "         WHEN scc.service_class BETWEEN 1 AND 4 THEN 'System'\n"
            "         WHEN scc.service_class = 5 THEN 'Superuser'\n"
            "         WHEN scc.service_class BETWEEN 6 AND 13 THEN 'Manual WLM'\n"
            "         WHEN scc.service_class = 14 THEN 'SQA'\n"
            "         WHEN scc.service_class = 15 THEN 'Redshift Maintenance'\n"
            "         WHEN scc.service_class BETWEEN 100 AND 107 THEN 'Auto WLM'\n"
            '       END AS service_class_category,\n'
            '       trim(scc.name) AS queue_name,\n'
            '       CASE\n'
            "         WHEN scc.num_query_tasks = -1 THEN 'auto'\n"
            '         ELSE scc.num_query_tasks::text\n'
            '       END AS slots,\n'
            '       CASE\n'
            "         WHEN scc.query_working_mem = -1 THEN 'auto'\n"
            '         ELSE scc.query_working_mem::text\n'
            '       END AS query_working_memory_mb_per_slot,\n'
            '       SUM(case when scc.service_class BETWEEN 6 AND 13 then num_query_tasks*query_working_mem else NULL end) over (partition by null) AS total_memory_mb,\n'
            "       NVL(ROUND(((scc.num_query_tasks*scc.query_working_mem)::decimal(18,2)/ total_memory_mb::decimal(18,2))*100,0)::decimal(18,2)::varchar(12),'auto') cluster_memory_pct,\n"
            '       scc.max_execution_time AS query_timeout,\n'
            '       trim(scc.concurrency_scaling) AS concurrency_scaling,\n'
            '       trim(scc.query_priority) AS queue_priority,\n'
            '       nvl(qc.qmr_rule_count,0) AS qmr_rule_count,\n'
            "       coalesce(qc.is_queue_evictable,'N') is_queue_evicatable,\n"
            '       cnd.condition,\n'
            '       qc.qmr_rule\n'
            'FROM stv_wlm_service_class_config scc\n'
            'INNER JOIN (\n'
            "       select action_service_class, LISTAGG(TRIM(condition),', ') condition \n"
            '       from stv_wlm_classification_config\n'
            '       group by 1) cnd ON scc.service_class = cnd.action_service_class\n'
            'LEFT OUTER JOIN (\n'
            '       SELECT service_class,\n'
            '         COUNT(1) AS qmr_rule_count,\n'
            "         max(case when rule_name IS NOT NULL then 'Y' else 'N' end) is_queue_evictable,\n"
            "         LISTAGG(rule_name || ':' || '[' || action || '] ' || metric_name || metric_operator || metric_value::VARCHAR(256) || ',') within group(order by rule_name) as qmr_rule\n"
            '       FROM stv_wlm_qmr_config\n'
            '       GROUP BY 1) qc ON (scc.service_class = qc.service_class)\n'
            'WHERE scc.service_class > 4\n'
            'ORDER BY 2 ASC\n'
            ')\n'
            '-- Signal: queues do not have total memory = 100\n'
            "SELECT count(*), 'REC_016'\n"
            'FROM data\n'
            "WHERE wlm_mode='manual' and service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select sum(case when cluster_memory_pct = 'auto' then 0 else cluster_memory_pct::decimal end) from data) < 100)\n"
            'UNION ALL\n'
            '-- Signal: queues have total concurrency > 20\n'
            "SELECT count(*), 'REC_017'\n"
            'FROM data\n'
            "WHERE wlm_mode='manual' and service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select sum(case when slots = 'auto' then 0 else slots::int end) from data where service_class_id not in (5,14,15)) > 20)\n"
            'UNION ALL\n'
            '-- Signal: uses single WLM queue\n'
            "SELECT count(*), 'REC_018'\n"
            'FROM data\n'
            "WHERE service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select count(1) from data where service_class_category = 'Manual WLM') = 1 OR (select count(1) from data where service_class_category = 'Auto WLM') = 1)\n"
            'UNION ALL\n'
            '-- Signal: uses manual WLM\n'
            "SELECT count(*), 'REC_015'\n"
            'FROM data\n'
            "WHERE wlm_mode='manual' and service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select count(1) from data where wlm_mode='manual') > 0)\n"
            'UNION ALL\n'
            '-- Signal: Concurrency scaling is not enabled\n'
            "SELECT count(*), 'REC_019'\n"
            'FROM data\n'
            "WHERE service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select count(1) from data where concurrency_scaling = 'auto') = 0)\n"
            'UNION ALL\n'
            '-- Signal: short query acceleration (SQA) is not enabled\n'
            "SELECT count(*), 'REC_020'\n"
            'FROM data\n'
            "WHERE service_class_id <> 5 and service_class_id <> 15 AND ((select count(1) from data where service_class_category != 'SQA') = (select count(1) from data))\n"
            'UNION ALL\n'
            '-- Signal: all query queues having the same query priority\n'
            "SELECT count(*), 'REC_021'\n"
            'FROM data\n'
            'WHERE service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select count(distinct queue_priority) from data) = 1)\n'
            'UNION ALL\n'
            '-- Signal: no query monitoring rules (QMR) defined\n'
            "SELECT count(*), 'REC_022'\n"
            'FROM data\n'
            'WHERE service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select sum(qmr_rule_count) from data) = 0)\n'
            'UNION ALL\n'
            '-- Signal: no QMR defined for query_execution_time metric\n'
            "SELECT count(*), 'REC_022'\n"
            'FROM data\n'
            "WHERE service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select count(1) from data where coalesce(qmr_rule,'') not like '%query_execution_time%') = (select count(1) from data))\n"
            'UNION ALL\n'
            '-- Signal: no QMR defined for query_temp_blocks_to_disk metric\n'
            "SELECT count(*), 'REC_022'\n"
            'FROM data\n'
            "WHERE service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select count(1) from data where coalesce(qmr_rule,'') not like '%query_temp_blocks_to_disk%') = (select count(1) from data))\n"
            'UNION ALL\n'
            '-- Signal: no QMR defined for spectrum_scan_size_mb or spectrum_scan_row_count metric\n'
            "SELECT count(*), 'REC_022'\n"
            'FROM data\n'
            "WHERE service_class_id <> 5 and service_class_id <> 14 and service_class_id <> 15 AND ((select count(1) from data where coalesce(qmr_rule,'') not like '%spectrum_scan%') = (select count(1) from data))\n"
        ),
        True,
    ),
    # ------------------------------------------------------------------
    # WorkloadEvaluation
    # ------------------------------------------------------------------
    (
        'WorkloadEvaluation',
        (
            '-- WorkloadEvaluation\n'
            'WITH recursive min_list(start_min, end_min) as (\n'
            '  SELECT \n'
            "    dateadd(m,1,dateadd(d,-7,date_trunc('m',getdate()))) start_min, \n"
            "    dateadd(m,2,dateadd(d,-7,date_trunc('m',getdate()))) end_min\n"
            '  UNION ALL\n'
            "  SELECT dateadd(m, 1, start_min), dateadd(m, 1, end_min) from min_list where start_min < date_trunc('m',getdate())),\n"
            'scan_list as (\n'
            '  SELECT query_id, max(mb_scanned) max_scan_mb, \n'
            "    CASE WHEN max_scan_mb < 100 THEN 'small'\n"
            "      WHEN max_scan_mb > 500000 THEN 'large'\n"
            "      ELSE 'medium' END workloadtype\n"
            '    FROM (\n'
            '      SELECT query_id, segment_id, sum(blocks_read) mb_scanned\n'
            '      FROM SYS_QUERY_DETAIL\n'
            '      WHERE user_id > 1\n'
            '      GROUP BY 1,2) scan_sum\n'
            '  GROUP BY 1),\n'
            'daily_summary as (\n'
            '  SELECT \n'
            '    workloadtype,\n'
            "    datediff(m,start_min, date_trunc('m',getdate()))/1440 day_num,\n"
            '    count(distinct start_min) mins_of_day\n'
            '  FROM SYS_QUERY_HISTORY \n'
            '  JOIN scan_list using (query_id)\n'
            '  JOIN min_list ON start_time < end_min AND end_time > start_min\n'
            '  WHERE user_id > 1\n'
            '  GROUP BY 1,2),\n'
            'summary as (\n'
            '  SELECT workloadtype, \n'
            '    avg(mins_of_day) total_query_minutes_in_day, \n'
            '    ((total_query_minutes_in_day/1440.0)*100)::int perc_duration_in_day\n'
            '  FROM daily_summary\n'
            '  GROUP BY 1),\n'
            'workload_breakdown as (\n'
            '  SELECT \n'
            '    workloadtype, \n'
            '    sum(elapsed_time/1000000.0)::decimal(18,2) total_workload,\n'
            '    min(elapsed_time/1000000.0)::decimal(18,2) workload_exec_sec_min,\n'
            '    max(elapsed_time/1000000.0)::decimal(18,2) workload_exec_sec_max,\n'
            '    avg(elapsed_time/1000000.0)::decimal(18,2) workload_exec_sec_avg, \n'
            '    count(distinct query_id) query_cnt,\n'
            '    avg(max_scan_mb) scan_mb_avg\n'
            '  FROM SYS_QUERY_HISTORY\n'
            '  JOIN scan_list using (query_id)\n'
            "  WHERE start_time between dateadd(d,-7,date_trunc('m',getdate())) and date_trunc('m',getdate())\n"
            '    and user_id > 1\n'
            '  GROUP BY 1),\n'
            'data as (\n'
            'SELECT workloadtype, \n'
            '  ((total_workload*1.0 / sum(total_workload) over (partition by null))*100)::int perc_of_total_workload,\n'
            '  perc_duration_in_day, total_query_minutes_in_day,\n'
            '  (sum(total_query_minutes_in_day) over () / 1440.0 * 100)::int total_pct_busy,\n'
            '  workload_exec_sec_avg, workload_exec_sec_min, \n'
            '  workload_exec_sec_max, query_cnt, scan_mb_avg\n'
            'FROM summary s\n'
            'JOIN workload_breakdown b using(workloadtype)\n'
            ')\n'
            '-- Signal: Evaluate Workload for Serverless. Cluster is busy less than 75% of the time in a day.\n'
            "SELECT count(*), 'REC_035'\n"
            'FROM data\n'
            'WHERE total_pct_busy < 75\n'
        ),
        False,
    ),
]
