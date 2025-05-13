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

ERROR_EMPTY_SQL_PASSED_TO_QUERY = 'Incorrect invocation: Query invoked without a SQL statement'
ERROR_EMPTY_SQL_LIST_PASSED_TO_TRANSACT = (
    'Incorrect invocation: Transact invoked with no sql statements'
)
ERROR_TRANSACT_INVOKED_IN_READ_ONLY_MODE = (
    'transact cannot be used due to read only mode. Use query for executing a sql statement'
)
ERROR_EMPTY_TABLE_NAME_PASSED_TO_SCHEMA = (
    'Incorrect invocation: Schema invoked without a table name'
)
ERROR_EMPTY_SQL_PASSED_TO_EXPLAIN = 'Incorrect invocation: Explain invoked without a SQL statement'
ERROR_CREATE_CONNECTION = 'Failed to create connection due to error'
ERROR_EXECUTE_QUERY = 'Failed to execute query due to error'
