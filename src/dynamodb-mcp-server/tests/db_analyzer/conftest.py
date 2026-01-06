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

"""Shared fixtures for db_analyzer tests."""

import pytest
from awslabs.dynamodb_mcp_server.db_analyzer.mysql import MySQLPlugin
from awslabs.dynamodb_mcp_server.db_analyzer.postgresql import PostgreSQLPlugin
from awslabs.dynamodb_mcp_server.db_analyzer.sqlserver import SQLServerPlugin


@pytest.fixture
def mysql_plugin():
    """Create MySQL plugin instance."""
    return MySQLPlugin()


@pytest.fixture
def postgresql_plugin():
    """Create PostgreSQL plugin instance."""
    return PostgreSQLPlugin()


@pytest.fixture
def sqlserver_plugin():
    """Create SQL Server plugin instance."""
    return SQLServerPlugin()


@pytest.fixture
def mysql_connection_params():
    """Create sample MySQL connection parameters."""
    return {
        'cluster_arn': 'arn:aws:rds:us-east-1:123456789:cluster:test',
        'secret_arn': 'arn:aws:secretsmanager:us-east-1:123456789:secret:test',  # pragma: allowlist secret
        'database': 'test_db',
        'region': 'us-east-1',
        'max_results': 500,
    }
