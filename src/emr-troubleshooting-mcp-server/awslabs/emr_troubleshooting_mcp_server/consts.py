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

"""Constants for the EMR Troubleshooting MCP server."""

import os
import pathlib

# Environment variables with defaults
DEFAULT_AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
DEFAULT_AWS_PROFILE = os.environ.get('AWS_PROFILE')
LOG_LEVEL = os.environ.get('FASTMCP_LOG_LEVEL', 'WARNING')
ATHENA_TIMEOUT = int(os.environ.get('EMR_MCP_ATHENA_TIMEOUT', '300'))
MAX_ISSUES_RETURNED = int(os.environ.get('EMR_MCP_MAX_ISSUES', '10'))
S3_BUCKET_PREFIX = os.environ.get('EMR_MCP_S3_BUCKET_PREFIX', 'emr-log-analysis')

# File paths
CURRENT_DIR = pathlib.Path(__file__).parent.absolute()
DATA_DIR = CURRENT_DIR / 'data'

# Known issue files
SPARK_ISSUES_FILE = DATA_DIR / 'spark_known_issues.jsonl'
HADOOP_YARN_ISSUES_FILE = DATA_DIR / 'hadoop_yarn_known_issues.jsonl'
HADOOP_HDFS_ISSUES_FILE = DATA_DIR / 'hadoop_hdfs_known_issues.jsonl'
HIVE_ISSUES_FILE = DATA_DIR / 'hive_known_issues.jsonl'
HBASE_ISSUES_FILE = DATA_DIR / 'hbase_known_issues.jsonl'
PRESTO_ISSUES_FILE = DATA_DIR / 'presto_known_issues.jsonl'
EMR_SERVICE_ISSUES_FILE = DATA_DIR / 'emr_service_known_issues.jsonl'
EMR_SDK_ISSUES_FILE = DATA_DIR / 'emr_sdk_known_issues.jsonl'
ERROR_EXCEPTION_FILE = DATA_DIR / 'error_exception.json'

# Default values
DEFAULT_MAX_MATCHES = 5
DEFAULT_MIN_KEYWORD_LENGTH = 10

# Log analysis settings
MAX_LOG_SIZE_MB = 10  # Maximum log size to analyze in MB
LOG_CHUNK_SIZE = 1024 * 1024  # 1MB chunks for processing large logs

# Messages
NO_MATCHES_MESSAGE = 'No known issues were found in the provided log content.'
MULTIPLE_MATCHES_MESSAGE = (
    'Multiple issues were found in the logs. Recommendations are provided in order of relevance.'
)

# Athena query templates based on the original implementation
ATHENA_QUERY_TEMPLATES = {
    'create_logs_table': """
    CREATE EXTERNAL TABLE IF NOT EXISTS {table_name}(
        data string COMMENT 'from deserializer'
    )
    STORED AS INPUTFORMAT 'org.apache.hadoop.mapred.TextInputFormat'
    OUTPUTFORMAT
        'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
    LOCATION '{logs_location}'
    """,
    'create_kb_table': """
    CREATE EXTERNAL TABLE IF NOT EXISTS {table_name}(
        id string,
        summary string,
        description string,
        keywords array<string>,
        knowledge_center_links array<string>
    )
    ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
    WITH SERDEPROPERTIES ('ignore.malformed.json' = 'true')
    LOCATION '{kb_location}'
    """,
    'create_results_table': """
    CREATE EXTERNAL TABLE IF NOT EXISTS {table_name}(
        issue_id STRING,
        matched_keyword STRING,
        data STRING,
        filepath STRING
    )
    ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
    LOCATION '{results_location}'
    TBLPROPERTIES ("skip.header.line.count"="1")
    """,
    'keyword_matching_analysis': """
    SELECT
        k.id AS issue_id,
        k.unnested_keywords AS matched_keyword,
        emr."data" AS data,
        emr."$PATH" AS filepath
    FROM {logs_table} emr
    JOIN (
        SELECT id, unnested_keywords
        FROM {kb_table}
        CROSS JOIN UNNEST(keywords) AS t(unnested_keywords)
    ) k ON strpos(emr."data", k.unnested_keywords) > 0
    """,
    'aggregate_results': """
    SELECT
        results.issue_id,
        results.matched_keyword,
        count(results.matched_keyword) as issue_occurrences,
        km.summary,
        km.description,
        km.knowledge_center_links,
        array_agg(substr(results.data, 1, 200) LIMIT 3) as sample_logs
    FROM {results_table} results
    LEFT OUTER JOIN (
        SELECT id, summary, description, knowledge_center_links,
               unnested_keywords
        FROM {kb_table}
        CROSS JOIN UNNEST(keywords) AS t(unnested_keywords)
    ) km ON strpos(results.matched_keyword, km.unnested_keywords) > 0
    WHERE regexp_like("$PATH", '.csv') AND "$PATH" NOT LIKE '%metadata'
    GROUP BY results.issue_id, results.matched_keyword, km.summary,
             km.description, km.knowledge_center_links
    ORDER BY issue_occurrences DESC
    """,
    'filepath_analysis': """
    SELECT
        filepath,
        count(issue_id) as issue_occurrences,
        array_agg(distinct(matched_keyword)) as matched_keywords
    FROM {results_table}
    WHERE regexp_like("$PATH",'.csv') AND "$PATH" NOT LIKE '%metadata'
    GROUP BY filepath
    ORDER BY issue_occurrences DESC
    """,
}
