# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

DSQL_MCP_SERVER_APPLICATION_NAME = 'awslabs.aurora-dsql-mcp-server'
DSQL_DB_NAME = 'postgres'
DSQL_DB_PORT = '5432'

# Connection management
CONNECTION_IDLE_TIMEOUT_SECONDS = 3600  # 1 hour
CONNECTION_TEST_QUERY = 'SELECT 1'

ERROR_EMPTY_SQL_PASSED_TO_READONLY_QUERY = (
    'Incorrect invocation: readonly_query invoked without a SQL statement'
)
ERROR_EMPTY_SQL_LIST_PASSED_TO_TRANSACT = (
    'Incorrect invocation: transact invoked with no sql statements'
)
ERROR_TRANSACT_INVOKED_IN_READ_ONLY_MODE = 'Your mcp server does not allow writes. To use transact, change the MCP configuration per README.md'
ERROR_EMPTY_TABLE_NAME_PASSED_TO_SCHEMA = (
    'Incorrect invocation: Schema invoked without a table name'
)
ERROR_CREATE_CONNECTION = 'Failed to create connection due to error'
ERROR_EXECUTE_QUERY = 'Failed to execute query due to error'
BEGIN_READ_ONLY_TRANSACTION_SQL = 'BEGIN TRANSACTION READ ONLY'
COMMIT_TRANSACTION_SQL = 'COMMIT'
ROLLBACK_TRANSACTION_SQL = 'ROLLBACK'
BEGIN_TRANSACTION_SQL = 'BEGIN'
GET_SCHEMA_SQL = (
    'SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s'
)
ERROR_BEGIN_READ_ONLY_TRANSACTION = 'Failed to begin read only transaction'
INTERNAL_ERROR = 'Internal Error'
READ_ONLY_QUERY_WRITE_ERROR = 'readonly_query does not support write operations. Use transact'
ERROR_ROLLBACK_TRANSACTION = 'Failed to rollback transaction'
ERROR_READONLY_QUERY = 'Error executing readonly_query'
ERROR_BEGIN_TRANSACTION = 'Failed to begin transaction'
ERROR_TRANSACT = 'Error executing transact'
ERROR_GET_SCHEMA = 'Error executing get_schema'
