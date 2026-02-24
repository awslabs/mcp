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

"""Constants for the MWAA MCP Server."""

# Environment variable names
ENV_AWS_REGION = 'AWS_REGION'
ENV_AWS_PROFILE = 'AWS_PROFILE'
ENV_LOG_LEVEL = 'FASTMCP_LOG_LEVEL'

# Default values
DEFAULT_REGION = 'us-east-1'

# Environment name validation pattern (1-80 chars, starts with letter)
ENVIRONMENT_NAME_PATTERN = r'^[a-zA-Z][0-9a-zA-Z\-_]{0,79}$'

# Airflow REST API v2 path templates
AIRFLOW_API_PREFIX = '/api/v2'

# DAG endpoints
DAGS_PATH = f'{AIRFLOW_API_PREFIX}/dags'
DAG_PATH = f'{AIRFLOW_API_PREFIX}/dags/{{dag_id}}'
DAG_SOURCE_PATH = f'{AIRFLOW_API_PREFIX}/dagSources/{{file_token}}'

# DAG run endpoints
DAG_RUNS_PATH = f'{AIRFLOW_API_PREFIX}/dags/{{dag_id}}/dagRuns'
DAG_RUN_PATH = f'{AIRFLOW_API_PREFIX}/dags/{{dag_id}}/dagRuns/{{dag_run_id}}'

# Task instance endpoints
TASK_INSTANCES_PATH = f'{AIRFLOW_API_PREFIX}/dags/{{dag_id}}/dagRuns/{{dag_run_id}}/taskInstances'
TASK_INSTANCE_PATH = (
    f'{AIRFLOW_API_PREFIX}/dags/{{dag_id}}/dagRuns/{{dag_run_id}}/taskInstances/{{task_id}}'
)
TASK_LOGS_PATH = (
    f'{AIRFLOW_API_PREFIX}/dags/{{dag_id}}/dagRuns/{{dag_run_id}}'
    f'/taskInstances/{{task_id}}/logs/{{try_number}}'
)

# Other endpoints
CONNECTIONS_PATH = f'{AIRFLOW_API_PREFIX}/connections'
VARIABLES_PATH = f'{AIRFLOW_API_PREFIX}/variables'
IMPORT_ERRORS_PATH = f'{AIRFLOW_API_PREFIX}/importErrors'

# Sensitive fields to redact from connection responses
CONNECTION_SENSITIVE_FIELDS = ('password', 'extra')
