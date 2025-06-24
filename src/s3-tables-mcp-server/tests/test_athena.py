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

"""Tests for the Athena engine module."""

import pytest
from awslabs.s3_tables_mcp_server.engines.athena import AthenaEngine
from awslabs.s3_tables_mcp_server.engines.config import AthenaConfig
from unittest.mock import MagicMock, patch


class TestAthenaEngine:
    """Test the AthenaEngine class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock AthenaConfig."""
        return AthenaConfig(
            output_location='s3://test-bucket/results/',
            workgroup='primary',
            region='us-west-2',
            database='test_database',
            catalog='test_catalog',
        )

    @pytest.fixture
    def mock_athena_client(self):
        """Create a mock Athena client."""
        return MagicMock()

    @pytest.fixture
    def engine_with_mock_client(self, mock_config, mock_athena_client):
        """Create an AthenaEngine with a mocked client."""
        with patch(
            'awslabs.s3_tables_mcp_server.engines.athena.get_athena_client'
        ) as mock_get_client:
            mock_get_client.return_value = mock_athena_client
            engine = AthenaEngine(mock_config)
            return engine, mock_athena_client

    def test_init_success(self, mock_config):
        """Test successful initialization of AthenaEngine."""
        with patch(
            'awslabs.s3_tables_mcp_server.engines.athena.get_athena_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            engine = AthenaEngine(mock_config)

            assert engine.config == mock_config
            assert engine._client == mock_client
            mock_get_client.assert_called_once_with(region_name='us-west-2')

    def test_init_connection_failure(self, mock_config):
        """Test initialization failure when connection cannot be established."""
        with patch(
            'awslabs.s3_tables_mcp_server.engines.athena.get_athena_client'
        ) as mock_get_client:
            mock_get_client.side_effect = Exception('Connection failed')

            with pytest.raises(
                ConnectionError, match='Failed to initialize Athena connection: Connection failed'
            ):
                AthenaEngine(mock_config)

    def test_execute_query_success_with_results(self, engine_with_mock_client):
        """Test successful query execution with results."""
        engine, mock_client = engine_with_mock_client

        # Mock the query execution flow
        mock_client.start_query_execution.return_value = {'QueryExecutionId': 'test-query-id'}

        mock_client.get_query_execution.return_value = {
            'QueryExecution': {
                'Status': {'State': 'SUCCEEDED'},
                'QueryExecutionId': 'test-query-id',
                'Query': 'SELECT * FROM test_table',
                'StatementType': 'DML',
                'ResultConfiguration': {'OutputLocation': 's3://test-bucket/results/'},
                'QueryExecutionContext': {'Database': 'test_database'},
                'WorkGroup': 'primary',
                'EngineVersion': 'Athena engine version 3',
                'SubstatementType': 'SELECT',
            }
        }

        mock_client.get_query_results.return_value = {
            'ResultSet': {
                'ResultSetMetadata': {'ColumnInfo': [{'Name': 'id'}, {'Name': 'name'}]},
                'Rows': [
                    {'Data': [{'VarCharValue': 'id'}, {'VarCharValue': 'name'}]},  # Header row
                    {'Data': [{'VarCharValue': '1'}, {'VarCharValue': 'test1'}]},
                    {'Data': [{'VarCharValue': '2'}, {'VarCharValue': 'test2'}]},
                ],
            }
        }

        result = engine.execute_query('SELECT * FROM test_table')

        # Verify the result structure
        assert result['columns'] == ['id', 'name']
        assert result['rows'] == [['1', 'test1'], ['2', 'test2']]
        assert result['query_execution_id'] == 'test-query-id'
        assert result['output_location'] == 's3://test-bucket/results/'
        assert 'query_execution' in result

        # Verify the query execution details
        query_execution = result['query_execution']
        assert query_execution['QueryExecutionId'] == 'test-query-id'
        assert query_execution['Query'] == 'SELECT * FROM test_table'
        assert query_execution['StatementType'] == 'DML'
        assert query_execution['WorkGroup'] == 'primary'
        assert query_execution['EngineVersion'] == 'Athena engine version 3'
        assert query_execution['SubstatementType'] == 'SELECT'

        # Verify the client calls
        mock_client.start_query_execution.assert_called_once_with(
            QueryString='SELECT * FROM test_table',
            QueryExecutionContext={
                'Database': 'test_database',
                'Catalog': 'test_catalog',
            },
            WorkGroup='primary',
            ResultConfiguration={'OutputLocation': 's3://test-bucket/results/'},
        )

    def test_execute_query_success_no_results(self, engine_with_mock_client):
        """Test successful query execution with no results."""
        engine, mock_client = engine_with_mock_client

        # Mock the query execution flow
        mock_client.start_query_execution.return_value = {'QueryExecutionId': 'test-query-id'}

        mock_client.get_query_execution.return_value = {
            'QueryExecution': {
                'Status': {'State': 'SUCCEEDED'},
                'QueryExecutionId': 'test-query-id',
                'Query': 'SELECT * FROM empty_table',
                'StatementType': 'DML',
                'ResultConfiguration': {'OutputLocation': 's3://test-bucket/results/'},
                'QueryExecutionContext': {'Database': 'test_database'},
                'WorkGroup': 'primary',
                'EngineVersion': 'Athena engine version 3',
                'SubstatementType': 'SELECT',
            }
        }

        mock_client.get_query_results.return_value = {
            'ResultSet': {'ResultSetMetadata': {'ColumnInfo': []}, 'Rows': []}
        }

        result = engine.execute_query('SELECT * FROM empty_table')

        # Verify the result structure for empty results
        assert result['columns'] == []
        assert result['rows'] == []
        assert result['query_execution_id'] == 'test-query-id'
        assert result['output_location'] == 's3://test-bucket/results/'
        assert 'query_execution' in result

    def test_execute_query_failed_state(self, engine_with_mock_client):
        """Test query execution when query fails."""
        engine, mock_client = engine_with_mock_client

        # Mock the query execution flow
        mock_client.start_query_execution.return_value = {'QueryExecutionId': 'test-query-id'}

        mock_client.get_query_execution.return_value = {
            'QueryExecution': {
                'Status': {'State': 'FAILED', 'StateChangeReason': 'Table not found'}
            }
        }

        with pytest.raises(Exception, match='Query failed: Table not found'):
            engine.execute_query('SELECT * FROM nonexistent_table')

    def test_execute_query_cancelled_state(self, engine_with_mock_client):
        """Test query execution when query is cancelled."""
        engine, mock_client = engine_with_mock_client

        # Mock the query execution flow
        mock_client.start_query_execution.return_value = {'QueryExecutionId': 'test-query-id'}

        mock_client.get_query_execution.return_value = {
            'QueryExecution': {'Status': {'State': 'CANCELLED'}}
        }

        with pytest.raises(Exception, match='Query was cancelled'):
            engine.execute_query('SELECT * FROM test_table')

    def test_execute_query_running_state_transition(self, engine_with_mock_client):
        """Test query execution with state transitions from RUNNING to SUCCEEDED."""
        engine, mock_client = engine_with_mock_client

        # Mock the query execution flow
        mock_client.start_query_execution.return_value = {'QueryExecutionId': 'test-query-id'}

        # First call returns RUNNING, second call returns SUCCEEDED
        mock_client.get_query_execution.side_effect = [
            {
                'QueryExecution': {
                    'Status': {'State': 'RUNNING'},
                    'QueryExecutionId': 'test-query-id',
                    'Query': 'SELECT * FROM test_table',
                    'StatementType': 'DML',
                    'ResultConfiguration': {'OutputLocation': 's3://test-bucket/results/'},
                    'QueryExecutionContext': {'Database': 'test_database'},
                    'WorkGroup': 'primary',
                    'EngineVersion': 'Athena engine version 3',
                    'SubstatementType': 'SELECT',
                }
            },
            {
                'QueryExecution': {
                    'Status': {'State': 'SUCCEEDED'},
                    'QueryExecutionId': 'test-query-id',
                    'Query': 'SELECT * FROM test_table',
                    'StatementType': 'DML',
                    'ResultConfiguration': {'OutputLocation': 's3://test-bucket/results/'},
                    'QueryExecutionContext': {'Database': 'test_database'},
                    'WorkGroup': 'primary',
                    'EngineVersion': 'Athena engine version 3',
                    'SubstatementType': 'SELECT',
                }
            },
        ]

        mock_client.get_query_results.return_value = {
            'ResultSet': {
                'ResultSetMetadata': {'ColumnInfo': [{'Name': 'id'}]},
                'Rows': [
                    {'Data': [{'VarCharValue': 'id'}]},  # Header row
                    {'Data': [{'VarCharValue': '1'}]},
                ],
            }
        }

        with patch('time.sleep') as mock_sleep:  # Mock sleep to speed up test
            result = engine.execute_query('SELECT * FROM test_table')

            assert result['columns'] == ['id']
            assert result['rows'] == [['1']]
            mock_sleep.assert_called_once_with(1)  # Should have slept once

    def test_execute_query_no_client(self, mock_config):
        """Test execute_query when no client is available."""
        engine = AthenaEngine.__new__(AthenaEngine)
        engine.config = mock_config
        engine._client = None

        with pytest.raises(ConnectionError, match='No active connection to Athena'):
            engine.execute_query('SELECT * FROM test_table')

    def test_execute_query_client_exception(self, engine_with_mock_client):
        """Test execute_query when client raises an exception."""
        engine, mock_client = engine_with_mock_client

        mock_client.start_query_execution.side_effect = Exception('Client error')

        with pytest.raises(Exception, match='Error executing query: Client error'):
            engine.execute_query('SELECT * FROM test_table')

    def test_execute_query_missing_state_change_reason(self, engine_with_mock_client):
        """Test query execution when StateChangeReason is missing."""
        engine, mock_client = engine_with_mock_client

        # Mock the query execution flow
        mock_client.start_query_execution.return_value = {'QueryExecutionId': 'test-query-id'}

        mock_client.get_query_execution.return_value = {
            'QueryExecution': {
                'Status': {'State': 'FAILED'}  # No StateChangeReason
            }
        }

        with pytest.raises(Exception, match='Query failed: Unknown error'):
            engine.execute_query('SELECT * FROM test_table')

    def test_execute_query_with_null_values(self, engine_with_mock_client):
        """Test query execution with null values in results."""
        engine, mock_client = engine_with_mock_client

        # Mock the query execution flow
        mock_client.start_query_execution.return_value = {'QueryExecutionId': 'test-query-id'}

        mock_client.get_query_execution.return_value = {
            'QueryExecution': {
                'Status': {'State': 'SUCCEEDED'},
                'QueryExecutionId': 'test-query-id',
                'Query': 'SELECT * FROM test_table',
                'StatementType': 'DML',
                'ResultConfiguration': {'OutputLocation': 's3://test-bucket/results/'},
                'QueryExecutionContext': {'Database': 'test_database'},
                'WorkGroup': 'primary',
                'EngineVersion': 'Athena engine version 3',
                'SubstatementType': 'SELECT',
            }
        }

        mock_client.get_query_results.return_value = {
            'ResultSet': {
                'ResultSetMetadata': {
                    'ColumnInfo': [{'Name': 'id'}, {'Name': 'name'}, {'Name': 'description'}]
                },
                'Rows': [
                    {
                        'Data': [
                            {'VarCharValue': 'id'},
                            {'VarCharValue': 'name'},
                            {'VarCharValue': 'description'},
                        ]
                    },  # Header row
                    {
                        'Data': [{'VarCharValue': '1'}, {'VarCharValue': 'test1'}, {}]
                    },  # Null value in third column
                    {
                        'Data': [{'VarCharValue': '2'}, {}, {'VarCharValue': 'desc2'}]
                    },  # Null value in second column
                ],
            }
        }

        result = engine.execute_query('SELECT * FROM test_table')

        # Verify that null values are handled as empty strings
        assert result['columns'] == ['id', 'name', 'description']
        assert result['rows'] == [['1', 'test1', ''], ['2', '', 'desc2']]

    def test_test_connection_success(self, engine_with_mock_client):
        """Test successful connection test."""
        engine, mock_client = engine_with_mock_client

        # Mock successful query execution
        mock_client.start_query_execution.return_value = {'QueryExecutionId': 'test-query-id'}
        mock_client.get_query_execution.return_value = {
            'QueryExecution': {
                'Status': {'State': 'SUCCEEDED'},
                'QueryExecutionId': 'test-query-id',
                'Query': 'SELECT 1',
                'StatementType': 'DML',
                'ResultConfiguration': {'OutputLocation': 's3://test-bucket/results/'},
                'QueryExecutionContext': {'Database': 'test_database'},
                'WorkGroup': 'primary',
                'EngineVersion': 'Athena engine version 3',
                'SubstatementType': 'SELECT',
            }
        }
        mock_client.get_query_results.return_value = {
            'ResultSet': {
                'ResultSetMetadata': {'ColumnInfo': [{'Name': '_col0'}]},
                'Rows': [{'Data': [{'VarCharValue': '_col0'}]}, {'Data': [{'VarCharValue': '1'}]}],
            }
        }

        result = engine.test_connection()
        assert result is True

    def test_test_connection_failure(self, engine_with_mock_client):
        """Test connection test failure."""
        engine, mock_client = engine_with_mock_client

        # Mock failed query execution
        mock_client.start_query_execution.side_effect = Exception('Connection failed')

        result = engine.test_connection()
        assert result is False

    def test_test_connection_query_failure(self, engine_with_mock_client):
        """Test connection test when query fails."""
        engine, mock_client = engine_with_mock_client

        # Mock query execution that fails
        mock_client.start_query_execution.return_value = {'QueryExecutionId': 'test-query-id'}
        mock_client.get_query_execution.return_value = {
            'QueryExecution': {
                'Status': {'State': 'FAILED', 'StateChangeReason': 'Database not found'}
            }
        }

        result = engine.test_connection()
        assert result is False

    def test_config_properties_used_correctly(self, mock_config):
        """Test that all config properties are used correctly in query execution."""
        with patch(
            'awslabs.s3_tables_mcp_server.engines.athena.get_athena_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            engine = AthenaEngine(mock_config)

            # Mock successful query execution
            mock_client.start_query_execution.return_value = {'QueryExecutionId': 'test-query-id'}
            mock_client.get_query_execution.return_value = {
                'QueryExecution': {
                    'Status': {'State': 'SUCCEEDED'},
                    'QueryExecutionId': 'test-query-id',
                    'Query': 'SELECT * FROM test_table',
                    'StatementType': 'DML',
                    'ResultConfiguration': {'OutputLocation': 's3://test-bucket/results/'},
                    'QueryExecutionContext': {'Database': 'test_database'},
                    'WorkGroup': 'primary',
                    'EngineVersion': 'Athena engine version 3',
                    'SubstatementType': 'SELECT',
                }
            }
            mock_client.get_query_results.return_value = {
                'ResultSet': {
                    'ResultSetMetadata': {'ColumnInfo': [{'Name': 'id'}]},
                    'Rows': [
                        {'Data': [{'VarCharValue': 'id'}]},
                        {'Data': [{'VarCharValue': '1'}]},
                    ],
                }
            }

            engine.execute_query('SELECT * FROM test_table')

            # Verify that all config properties are used
            mock_client.start_query_execution.assert_called_once_with(
                QueryString='SELECT * FROM test_table',
                QueryExecutionContext={
                    'Database': 'test_database',
                    'Catalog': 'test_catalog',
                },
                WorkGroup='primary',
                ResultConfiguration={'OutputLocation': 's3://test-bucket/results/'},
            )

    def test_config_with_optional_fields_none(self):
        """Test AthenaEngine with config where optional fields are None."""
        config = AthenaConfig(
            output_location='s3://test-bucket/results/'
            # All other fields are None by default
        )

        with patch(
            'awslabs.s3_tables_mcp_server.engines.athena.get_athena_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            engine = AthenaEngine(config)

            # Mock successful query execution
            mock_client.start_query_execution.return_value = {'QueryExecutionId': 'test-query-id'}
            mock_client.get_query_execution.return_value = {
                'QueryExecution': {
                    'Status': {'State': 'SUCCEEDED'},
                    'QueryExecutionId': 'test-query-id',
                    'Query': 'SELECT * FROM test_table',
                    'StatementType': 'DML',
                    'ResultConfiguration': {'OutputLocation': 's3://test-bucket/results/'},
                    'QueryExecutionContext': {'Database': None, 'Catalog': None},
                    'WorkGroup': None,
                    'EngineVersion': 'Athena engine version 3',
                    'SubstatementType': 'SELECT',
                }
            }
            mock_client.get_query_results.return_value = {
                'ResultSet': {
                    'ResultSetMetadata': {'ColumnInfo': [{'Name': 'id'}]},
                    'Rows': [
                        {'Data': [{'VarCharValue': 'id'}]},
                        {'Data': [{'VarCharValue': '1'}]},
                    ],
                }
            }

            engine.execute_query('SELECT * FROM test_table')

            # Verify that None values are handled correctly
            mock_client.start_query_execution.assert_called_once_with(
                QueryString='SELECT * FROM test_table',
                QueryExecutionContext={
                    'Database': None,
                    'Catalog': None,
                },
                WorkGroup=None,
                ResultConfiguration={'OutputLocation': 's3://test-bucket/results/'},
            )
