"""Tests for the get_schema_from_registry function."""

import logging
import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_tool_mcp_server.server import get_schema_from_registry


class TestGetSchema:
    """Tests for EventBridge Schema Registry integration."""

    @patch('awslabs.stepfunctions_tool_mcp_server.server.schemas_client')
    def test_get_schema_success(self, mock_schemas_client):
        """Test successful schema retrieval with valid ARN."""
        # Set up test data
        schema_arn = 'arn:aws:schemas:us-east-1:123456789012:schema/registry-name/schema-name'
        schema_content = {'type': 'object', 'properties': {'test': {'type': 'string'}}}

        # Set up mock response
        mock_schemas_client.describe_schema.return_value = {'Content': schema_content}

        # Call the function
        result = get_schema_from_registry(schema_arn)

        # Verify results
        assert result == schema_content
        mock_schemas_client.describe_schema.assert_called_once_with(
            RegistryName='registry-name',
            SchemaName='schema-name',
        )

    @patch('awslabs.stepfunctions_tool_mcp_server.server.schemas_client')
    def test_get_schema_invalid_arn(self, mock_schemas_client, caplog):
        """Test schema retrieval with invalid ARN format."""
        # Set up test data
        invalid_arn = 'invalid:arn:format'

        # Call the function and check logging
        with caplog.at_level(logging.ERROR):
            result = get_schema_from_registry(invalid_arn)

            # Verify results
            assert result is None
            assert 'Invalid schema ARN format' in caplog.text

        # Verify mock was not called
        mock_schemas_client.describe_schema.assert_not_called()

    @patch('awslabs.stepfunctions_tool_mcp_server.server.schemas_client')
    def test_get_schema_invalid_path(self, mock_schemas_client, caplog):
        """Test schema retrieval with invalid schema path in ARN."""
        # Set up test data
        invalid_path_arn = 'arn:aws:schemas:us-east-1:123456789012:schema/invalid-path'

        # Call the function and check logging
        with caplog.at_level(logging.ERROR):
            result = get_schema_from_registry(invalid_path_arn)

            # Verify results
            assert result is None
            assert 'Invalid schema path in ARN' in caplog.text

        # Verify mock was not called
        mock_schemas_client.describe_schema.assert_not_called()

    @patch('awslabs.stepfunctions_tool_mcp_server.server.schemas_client')
    def test_get_schema_client_error(self, mock_schemas_client, caplog):
        """Test error handling during schema retrieval."""
        # Set up test data
        schema_arn = 'arn:aws:schemas:us-east-1:123456789012:schema/registry-name/schema-name'

        # Set up mock to raise an exception
        mock_schemas_client.describe_schema.side_effect = Exception('Schema client error')

        # Call the function and check logging
        with caplog.at_level(logging.ERROR):
            result = get_schema_from_registry(schema_arn)

            # Verify results
            assert result is None
            assert 'Error fetching schema from registry' in caplog.text
            assert 'Schema client error' in caplog.text

        # Verify mock was called
        mock_schemas_client.describe_schema.assert_called_once_with(
            RegistryName='registry-name',
            SchemaName='schema-name',
        )

    @patch('awslabs.stepfunctions_tool_mcp_server.server.schemas_client')
    def test_get_schema_complex_content(self, mock_schemas_client):
        """Test retrieval of schema with complex content structure."""
        # Set up test data
        schema_arn = 'arn:aws:schemas:us-east-1:123456789012:schema/registry-name/schema-name'
        schema_content = {
            'type': 'object',
            'properties': {
                'data': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'string'},
                        'timestamp': {'type': 'string', 'format': 'date-time'},
                        'values': {'type': 'array', 'items': {'type': 'number'}},
                    },
                    'required': ['id', 'timestamp'],
                },
                'metadata': {
                    'type': 'object',
                    'properties': {'source': {'type': 'string'}, 'version': {'type': 'string'}},
                },
            },
        }

        # Set up mock response
        mock_schemas_client.describe_schema.return_value = {'Content': schema_content}

        # Call the function
        result = get_schema_from_registry(schema_arn)

        # Verify results
        assert result == schema_content
        mock_schemas_client.describe_schema.assert_called_once_with(
            RegistryName='registry-name',
            SchemaName='schema-name',
        )
