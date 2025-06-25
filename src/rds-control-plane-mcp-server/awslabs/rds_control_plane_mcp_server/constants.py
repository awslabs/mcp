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

"""Constants for RDS Control Plane MCP Server."""

# MCP Server Version
MCP_SERVER_VERSION = '0.1.0'

# Error Messages
ERROR_READONLY_MODE = (
    'This operation requires write access. The server is currently in read-only mode.'
)
ERROR_MISSING_PARAMS = 'Missing required parameters: {}'
ERROR_INVALID_PARAMS = 'Invalid parameters: {}'
ERROR_AWS_API = 'AWS API error: {}'
ERROR_UNEXPECTED = 'Unexpected error: {}'
ERROR_NOT_FOUND = 'Resource not found: {}'
ERROR_OPERATION_FAILED = 'Operation failed: {}'

# Success Messages
SUCCESS_CREATED = 'Successfully created {}'
SUCCESS_MODIFIED = 'Successfully modified {}'
SUCCESS_DELETED = 'Successfully deleted {}'

# Resource URI Prefixes
RESOURCE_PREFIX_DB_CLUSTER = 'aws-rds://db-cluster'
RESOURCE_PREFIX_DB_INSTANCE = 'aws-rds://db-instance'

# AWS RDS Engine Types
ENGINE_AURORA = 'aurora'
ENGINE_AURORA_MYSQL = 'aurora-mysql'
ENGINE_AURORA_POSTGRESQL = 'aurora-postgresql'
ENGINE_MYSQL = 'mysql'
ENGINE_POSTGRESQL = 'postgres'
ENGINE_MARIADB = 'mariadb'
ENGINE_ORACLE = 'oracle'
ENGINE_SQLSERVER = 'sqlserver'

# Default Values
DEFAULT_BACKUP_RETENTION_PERIOD = 7
DEFAULT_PORT_MYSQL = 3306
DEFAULT_PORT_POSTGRESQL = 5432
DEFAULT_PORT_MARIADB = 3306
DEFAULT_PORT_ORACLE = 1521
DEFAULT_PORT_SQLSERVER = 1433
DEFAULT_PORT_AURORA = 3306  # compatible with MySQL
DEFAULT_PORT_AURORA_POSTGRESQL = 5432  # Aurora PostgreSQL
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

"""Constants for RDS Control Plane MCP Server."""

# MCP Server Version
MCP_SERVER_VERSION = '0.1.0'

# Error Messages
ERROR_AWS_API = 'AWS API error: {}'
ERROR_UNEXPECTED = 'Unexpected error: {}'
