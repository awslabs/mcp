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

"""Resource docstrings for the RDS Control Plane MCP Server."""

LIST_CLUSTERS_DOCSTRING = """List all available Amazon RDS clusters in your account.

<use_case>
Use this resource to discover all available RDS database clusters in your AWS account.
</use_case>

<important_notes>
1. The response provides essential information about each cluster
2. Cluster identifiers returned can be used with the db-cluster/{cluster_id} resource
3. Clusters are filtered to the AWS region specified in your environment configuration
</important_notes>

## Response structure
Returns a JSON document containing:
- `clusters`: Array of DB cluster objects
- `count`: Number of clusters found
- `resource_uri`: Base URI for accessing clusters
"""

GET_CLUSTER_DOCSTRING = """Get detailed information about a specific Amazon RDS cluster.

<use_case>
Use this resource to retrieve comprehensive details about a specific RDS database cluster
identified by its cluster ID.
</use_case>

<important_notes>
1. The cluster ID must exist in your AWS account and region
2. The response contains full configuration details about the specified cluster
3. Error responses will be returned if the cluster doesn't exist
</important_notes>

## Response structure
Returns a JSON document containing detailed cluster information including:
- Status, engine type, and version
- Endpoints for connection
- Backup configuration
- Member instances
- Security groups
"""

LIST_INSTANCES_DOCSTRING = """List all available Amazon RDS instances in your account.

<use_case>
Use this resource to discover all available RDS database instances in your AWS account.
</use_case>

<important_notes>
1. The response provides essential information about each instance
2. Instance identifiers returned can be used with the db-instance/{instance_id} resource
3. Instances are filtered to the AWS region specified in your environment configuration
</important_notes>

## Response structure
Returns a JSON document containing:
- `instances`: Array of DB instance objects
- `count`: Number of instances found
- `resource_uri`: Base URI for accessing instances
"""

GET_INSTANCE_DOCSTRING = """Get detailed information about a specific Amazon RDS instance.

<use_case>
Use this resource to retrieve comprehensive details about a specific RDS database instance
identified by its instance ID.
</use_case>

<important_notes>
1. The instance ID must exist in your AWS account and region
2. The response contains full configuration details about the specified instance
3. Error responses will be returned if the instance doesn't exist
</important_notes>

## Response structure
Returns a JSON document containing detailed instance information including:
- Status, engine type, and version
- Instance class and storage configuration
- Endpoint for connection
- Availability zone and Multi-AZ setting
- Security groups
- Parameter groups
- Option groups
"""

LIST_PERFORMANCE_REPORTS_DOCSTRING = """List all available performance reports for a specific Amazon RDS instance.

<use_case>
Use this resource to discover all available Performance Insights analysis reports for a specific RDS database instance.
Performance reports provide detailed analysis of database performance issues, helping you identify bottlenecks and optimization opportunities.
</use_case>

<important_notes>
1. The response provides information about performance analysis reports generated for the instance
2. You must provide a valid DB resource identifier to retrieve reports
3. Performance reports are only available for instances with Performance Insights enabled
4. Reports are provided in chronological order with the most recent reports first
5. Use the `aws-rds://db-instance/{dbi_resource_identifier}/performance_report/{report_identifier}` resource to get detailed information about a specific report
</important_notes>

## Response structure
Returns an array of performance report objects, each containing:
- `analysis_report_id`: Unique identifier for the performance report (string)
- `create_time`: Time when the report was created (datetime)
- `start_time`: Start time of the analysis period (datetime)
- `end_time`: End time of the analysis period (datetime)
- `status`: Current status of the report (RUNNING, SUCCEEDED, or FAILED) (string)
- `tags`: List of tags attached to the report (array of key-value pairs)

<examples>
Example usage scenarios:
1. Performance monitoring:
   - List all available performance reports to identify periods of potential performance issues
   - Track reports generated during specific time periods of interest

2. Preparation for optimization:
   - Find specific report identifiers for detailed performance analysis
   - Monitor the status of recently generated performance reports
   - Identify long-running or failed reports that may need investigation
</examples>
"""

READ_PERFORMANCE_REPORT_DOCSTRING = """Read the contents of a specific performance report for a specific Amazon RDS instance.

<use_case>
Use this resource to retrieve detailed performance analysis data from a specific Performance Insights report.
These reports contain comprehensive information about database performance issues, including root cause analysis,
top SQL queries causing load, wait events, and recommended actions for performance optimization.
</use_case>

<important_notes>
1. You must provide both a valid DB instance identifier and report identifier
2. The report must be in a SUCCEEDED status to be fully readable
3. Reports in RUNNING status may return partial results
4. Reports in FAILED status will return error information about why the analysis failed
5. Large reports may contain extensive data about the performance issues analyzed
</important_notes>

## Response structure
Returns a detailed performance report object containing:
- `AnalysisReportId`: Unique identifier for the performance report (string)
- `ServiceType`: Service type (always 'RDS' for RDS instances) (string)
- `CreateTime`: Time when the report was created (datetime)
- `StartTime`: Start time of the analysis period (datetime)
- `EndTime`: End time of the analysis period (datetime)
- `Status`: Current status of the report (RUNNING, SUCCEEDED, or FAILED) (string)
- `AnalysisData`: The detailed performance analysis (object)
  - May include metrics, anomalies, query analysis, and recommendations
- `Tags`: List of tags attached to the report (array of key-value pairs)

<examples>
Example usage scenarios:
1. Performance troubleshooting:
   - Analyze root causes of performance bottlenecks during a specific period
   - Identify top resource-consuming SQL queries during performance degradation
   - Review wait events that contributed to slowdowns

2. Performance optimization:
   - Review recommended actions to improve database performance
   - Analyze patterns in resource usage to guide optimization efforts
   - Document performance issues for change management or postmortem analysis
</examples>
"""

LIST_DB_LOG_FILES_DOCSTRING = """List all available log files for a specific Amazon RDS instance.

<use_case>
Use this resource to discover all available log files for a specific RDS database instance.
Log files provide detailed logs of database activities, helping you troubleshoot issues and monitor performance.
</use_case>

<important_notes>
1. The response provides information about log files generated for the instance
2. You must provide a valid DB instance identifier to retrieve log files
3. Log files are only available for instances with logs enabled
4. Log files are provided in chronological order with the most recent log files first
5. Use the `aws-rds://db-instance/{dbi_resource_identifier}/log/{log_file_identifier}` resource to get detailed information about a specific log file
</important_notes>

## Response structure
Returns an array of log file objects, each containing:
- `log_file_identifier`: Unique identifier for the log file (string)
- `last_write_time`: Time when the log file was last written to (datetime)
- `size`: Size of the log file in bytes (integer)

<examples>
Example usage scenarios:
1. Log analysis:
   - List all available log files to identify periods of potential issues
   - Track log files generated during specific time periods of interest

2. Log troubleshooting:
   - Find specific log file identifiers for detailed log analysis
   - Monitor the status of recently generated log files
   - Identify long-running or failed log files that may need investigation
</examples>
"""
