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
    validate_read_only_query,
)
from unittest.mock import MagicMock, patch


class TestValidateReadOnlyQuery:
    """Test the validate_read_only_query function."""

    def test_valid_read_only_query(self):
        """Test that valid read-only queries pass validation."""
        valid_queries = [
            'SELECT * FROM table',
            'SELECT id, name FROM users WHERE active = true',
            'SELECT COUNT(*) FROM orders',
            'SELECT DISTINCT category FROM products',
            'SELECT * FROM table1 JOIN table2 ON table1.id = table2.id',
        ]

        for query in valid_queries:
            assert validate_read_only_query(query) is True

    def test_query_starting_with_write_operation(self):
        """Test that queries starting with write operations are rejected."""
        write_queries = [
            "INSERT INTO table VALUES (1, 'test')",
            "UPDATE users SET name = 'new' WHERE id = 1",
            'DELETE FROM table WHERE id = 1',
            'DROP TABLE users',
            'CREATE TABLE new_table (id INT)',
            'ALTER TABLE users ADD COLUMN email VARCHAR(255)',
            'TRUNCATE TABLE logs',
            'MERGE INTO target USING source ON target.id = source.id',
            "UPSERT INTO table VALUES (1, 'test')",
            "REPLACE INTO table VALUES (1, 'test')",
            "LOAD DATA FROM 'file.csv' INTO TABLE users",
            "COPY table FROM 's3://bucket/file.csv'",
            'WRITE TO table SELECT * FROM source',
        ]

        for query in write_queries:
            with pytest.raises(ValueError, match='Write operations are not allowed'):
                validate_read_only_query(query)

    def test_case_insensitive_validation(self):
        """Test that validation is case insensitive."""
        case_variations = [
            'insert into table values (1)',
            'INSERT INTO table VALUES (1)',
            'Insert Into Table Values (1)',
            'iNsErT iNtO tAbLe vAlUeS (1)',
        ]

        for query in case_variations:
            with pytest.raises(ValueError, match='Write operations are not allowed'):
                validate_read_only_query(query)

    def test_partial_word_matches_ignored(self):
        """Test that partial word matches are ignored."""
        # These should pass because they don't contain actual write operations
        safe_queries = [
            'SELECT * FROM insertion_logs',
            'SELECT * FROM deleted_records',
            'SELECT * FROM creation_timestamps',
            'SELECT * FROM alteration_history',
        ]

        for query in safe_queries:
            assert validate_read_only_query(query) is True


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
        with pytest.raises(ValueError, match='Write operations are not allowed'):
            _execute_database_query(
                table_bucket_arn=table_bucket_arn,
                namespace=namespace,
                query=query,
            )

    def test_read_only_validation_disabled(
        self, mock_env_region, mock_athena_engine, mock_athena_config
    ):
        """Test that read-only validation can be disabled."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        query = 'INSERT INTO table VALUES (1)'

        # Act
        result = _execute_database_query(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            query=query,
            validate_read_only=False,
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
                validate_read_only=True,
                region_name=None,
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
                validate_read_only=False,
                region_name=None,
            )
