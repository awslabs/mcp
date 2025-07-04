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

"""Tests for the database module."""

import os
import pytest
from awslabs.s3_tables_mcp_server.database import (
    _execute_database_query,
    modify_database_resource,
    query_database_resource,
)
from unittest.mock import MagicMock, patch


class TestExecuteDatabaseQuery:
    """Test the _execute_database_query function."""

    @pytest.fixture
    def mock_env_region(self):
        """Mock AWS_REGION environment variable."""
        with patch.dict(os.environ, {'AWS_REGION': 'us-west-2'}):
            yield

    @pytest.fixture
    def mock_athena_engine(self):
        """Mock AthenaEngine."""
        with patch('awslabs.s3_tables_mcp_server.database.AthenaEngine') as mock:
            engine_instance = MagicMock()
            engine_instance.test_connection.return_value = True
            engine_instance.execute_query.return_value = {
                'columns': ['id', 'name'],
                'rows': [['1', 'test']],
                'output_location': 's3://bucket/results/',
                'query_execution': {'QueryExecutionId': 'test-id'},
            }
            mock.return_value = engine_instance
            yield mock

    @pytest.fixture
    def mock_athena_config(self):
        """Mock AthenaConfig."""
        with patch('awslabs.s3_tables_mcp_server.database.AthenaConfig') as mock:
            yield mock

    def test_successful_query_execution(
        self, mock_env_region, mock_athena_engine, mock_athena_config
    ):
        """Test successful query execution."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        query = 'SELECT * FROM test_table'

        # Act
        result = _execute_database_query(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            query=query,
        )

        # Assert
        assert result['status'] == 'success'
        assert result['data']['columns'] == ['id', 'name']
        assert result['data']['rows'] == [['1', 'test']]
        assert 'metadata' in result['data']

        # Verify AthenaConfig was called with correct parameters
        mock_athena_config.assert_called_once()
        call_args = mock_athena_config.call_args
        assert (
            call_args[1]['output_location']
            == 's3://aws-athena-query-results-123456789012-us-west-2/'
        )
        assert call_args[1]['region'] == 'us-west-2'
        assert call_args[1]['database'] == 'test-namespace'
        assert call_args[1]['catalog'] == 's3tablescatalog/test-bucket'
        assert call_args[1]['workgroup'] == 'primary'

    def test_custom_output_location(self, mock_env_region, mock_athena_engine, mock_athena_config):
        """Test query execution with custom output location."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        query = 'SELECT * FROM test_table'
        custom_output = 's3://custom-bucket/results/'

        # Act
        result = _execute_database_query(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            query=query,
            output_location=custom_output,
        )

        # Assert
        assert result['status'] == 'success'
        mock_athena_config.assert_called_once()
        call_args = mock_athena_config.call_args
        assert call_args[1]['output_location'] == custom_output

    def test_custom_workgroup(self, mock_env_region, mock_athena_engine, mock_athena_config):
        """Test query execution with custom workgroup."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        query = 'SELECT * FROM test_table'
        custom_workgroup = 'custom-workgroup'

        # Act
        result = _execute_database_query(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            query=query,
            workgroup=custom_workgroup,
        )

        # Assert
        assert result['status'] == 'success'
        mock_athena_config.assert_called_once()
        call_args = mock_athena_config.call_args
        assert call_args[1]['workgroup'] == custom_workgroup

    def test_custom_region(self, mock_athena_engine, mock_athena_config):
        """Test query execution with custom region."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-east-1:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        query = 'SELECT * FROM test_table'
        custom_region = 'us-east-1'

        # Act
        result = _execute_database_query(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            query=query,
            region_name=custom_region,
        )

        # Assert
        assert result['status'] == 'success'
        mock_athena_config.assert_called_once()
        call_args = mock_athena_config.call_args
        assert call_args[1]['region'] == custom_region

    def test_missing_aws_region(self, mock_athena_engine, mock_athena_config):
        """Test that missing AWS_REGION raises ValueError."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        query = 'SELECT * FROM test_table'

        # Act & Assert
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match='AWS_REGION environment variable must be set'):
                _execute_database_query(
                    table_bucket_arn=table_bucket_arn,
                    namespace=namespace,
                    query=query,
                )

    def test_connection_failure(self, mock_env_region, mock_athena_engine, mock_athena_config):
        """Test that connection failure raises ConnectionError."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        query = 'SELECT * FROM test_table'

        # Mock connection failure
        engine_instance = mock_athena_engine.return_value
        engine_instance.test_connection.return_value = False

        # Act & Assert
        with pytest.raises(ConnectionError, match='Failed to connect to Athena'):
            _execute_database_query(
                table_bucket_arn=table_bucket_arn,
                namespace=namespace,
                query=query,
            )

    def test_read_only_validation_enabled(
        self, mock_env_region, mock_athena_engine, mock_athena_config
    ):
        """Test that read-only validation is enabled by default."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        query = 'INSERT INTO table VALUES (1)'

        # Act & Assert
        # _execute_database_query no longer validates read-only, so this test is not needed here
        result = _execute_database_query(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            query=query,
        )
        assert result['status'] == 'success'

    def test_read_only_validation_disabled(
        self, mock_env_region, mock_athena_engine, mock_athena_config
    ):
        """Test that read-only validation can be disabled (no longer relevant, always allowed)."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        query = 'INSERT INTO table VALUES (1)'

        # Act
        result = _execute_database_query(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            query=query,
        )

        # Assert
        assert result['status'] == 'success'

    def test_version_comment_prepended(
        self, mock_env_region, mock_athena_engine, mock_athena_config
    ):
        """Test that version comment is prepended to query."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        query = 'SELECT * FROM test_table'

        # Act
        _execute_database_query(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            query=query,
        )

        # Assert
        engine_instance = mock_athena_engine.return_value
        call_args = engine_instance.execute_query.call_args
        executed_query = call_args[0][0]
        assert executed_query.startswith('/* awslabs/mcp/s3-tables-mcp-server/')
        assert query in executed_query

    def test_bucket_arn_parsing(self, mock_env_region, mock_athena_engine, mock_athena_config):
        """Test that bucket ARN is correctly parsed."""
        # Arrange
        table_bucket_arn = (
            'arn:aws:s3tables:us-west-2:123456789012:table-bucket/complex/bucket/name'
        )
        namespace = 'test-namespace'
        query = 'SELECT * FROM test_table'

        # Act
        _execute_database_query(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            query=query,
        )

        # Assert
        mock_athena_config.assert_called_once()
        call_args = mock_athena_config.call_args
        assert (
            call_args[1]['catalog'] == 's3tablescatalog/name'
        )  # Should get last part after slashes


class TestQueryDatabaseResource:
    """Test the query_database_resource function."""

    @pytest.mark.asyncio
    async def test_query_database_resource(self):
        """Test query_database_resource function."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        query = 'SELECT * FROM test_table'
        expected_result = {'status': 'success', 'data': {'columns': [], 'rows': []}}

        with patch(
            'awslabs.s3_tables_mcp_server.database._execute_database_query'
        ) as mock_execute:
            mock_execute.return_value = expected_result

            # Act
            result = await query_database_resource(
                table_bucket_arn=table_bucket_arn,
                namespace=namespace,
                query=query,
            )

            # Assert
            assert result == expected_result
            mock_execute.assert_called_once_with(
                table_bucket_arn=table_bucket_arn,
                namespace=namespace,
                query=query,
                output_location=None,
                workgroup='primary',
                region_name=None,
            )

    @pytest.mark.asyncio
    async def test_query_database_resource_rejects_write(self):
        """Test that query_database_resource rejects write queries."""
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        query = 'INSERT INTO table VALUES (1)'
        with pytest.raises(ValueError, match='Write operations are not allowed'):
            await query_database_resource(
                table_bucket_arn=table_bucket_arn,
                namespace=namespace,
                query=query,
            )


class TestModifyDatabaseResource:
    """Test the modify_database_resource function."""

    @pytest.mark.asyncio
    async def test_modify_database_resource(self):
        """Test modify_database_resource function."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        query = 'INSERT INTO test_table VALUES (1)'
        expected_result = {'status': 'success', 'data': {'columns': [], 'rows': []}}

        with patch(
            'awslabs.s3_tables_mcp_server.database._execute_database_query'
        ) as mock_execute:
            mock_execute.return_value = expected_result

            # Act
            result = await modify_database_resource(
                table_bucket_arn=table_bucket_arn,
                namespace=namespace,
                query=query,
            )

            # Assert
            assert result == expected_result
            mock_execute.assert_called_once_with(
                table_bucket_arn=table_bucket_arn,
                namespace=namespace,
                query=query,
                output_location=None,
                workgroup='primary',
                region_name=None,
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'operation',
        [
            'DELETE',
            'DROP',
            'MERGE',
            'REPLACE',
            'TRUNCATE',
            'VACUUM',
        ],
    )
    async def test_modify_database_resource_rejects_destructive_ops(self, operation):
        """Test that modify_database_resource rejects destructive operations."""
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        query = f'{operation} FROM test_table'
        with pytest.raises(
            ValueError,
            match=rf'Destructive operations are not allowed in write queries:.*{operation}',
        ):
            await modify_database_resource(
                table_bucket_arn=table_bucket_arn,
                namespace=namespace,
                query=query,
            )
