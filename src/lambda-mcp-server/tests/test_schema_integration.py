"""Tests for schema integration features of the lambda-mcp-server."""

import logging
import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.lambda_mcp_server.server import (
        get_schema_from_registry,
        get_schema_arn_from_function_arn,
        create_lambda_tool,
    )


class TestSchemaRegistry:
    """Tests for EventBridge Schema Registry integration."""

    def test_get_schema_valid_arn(self, caplog):
        """Test fetching schema with valid ARN."""
        mock_schema_content = {
            "type": "object",
            "properties": {
                "test": {"type": "string"}
            }
        }

        with patch('awslabs.lambda_mcp_server.server.schemas_client') as mock_client:
            # Set up the mock
            mock_client.describe_schema.return_value = {'Content': mock_schema_content}

            # Call the function with a valid ARN
            result = get_schema_from_registry(
                'arn:aws:schemas:us-east-1:123456789012:schema/registry-name/schema-name'
            )

            # Verify the result
            assert result == mock_schema_content

            # Verify the client was called with correct parameters
            mock_client.describe_schema.assert_called_once_with(
                RegistryName='registry-name',
                SchemaName='schema-name',
            )

    def test_get_schema_invalid_arn_format(self, caplog):
        """Test with invalid ARN format."""
        with patch('awslabs.lambda_mcp_server.server.schemas_client') as mock_client:
            with caplog.at_level(logging.ERROR):
                # Test with invalid ARN
                result = get_schema_from_registry('invalid:arn:format')

                # Verify the result is None
                assert result is None

                # Verify error was logged
                assert 'Invalid schema ARN format' in caplog.text

                # Verify client was not called
                mock_client.describe_schema.assert_not_called()

    def test_get_schema_invalid_path(self, caplog):
        """Test with invalid schema path in ARN."""
        with patch('awslabs.lambda_mcp_server.server.schemas_client') as mock_client:
            with caplog.at_level(logging.ERROR):
                # Test with ARN containing invalid path
                result = get_schema_from_registry(
                    'arn:aws:schemas:us-east-1:123456789012:schema/invalid-path'
                )

                # Verify the result is None
                assert result is None

                # Verify error was logged
                assert 'Invalid schema path in ARN' in caplog.text

                # Verify client was not called
                mock_client.describe_schema.assert_not_called()

    def test_get_schema_client_error(self, caplog):
        """Test handling of schema client errors."""
        with patch('awslabs.lambda_mcp_server.server.schemas_client') as mock_client:
            # Set up the mock to raise an exception
            mock_client.describe_schema.side_effect = Exception('Schema client error')

            with caplog.at_level(logging.ERROR):
                # Call the function
                result = get_schema_from_registry(
                    'arn:aws:schemas:us-east-1:123456789012:schema/registry-name/schema-name'
                )

                # Verify the result is None
                assert result is None

                # Verify error was logged
                assert 'Error fetching schema from registry' in caplog.text
                assert 'Schema client error' in caplog.text


class TestSchemaArnRetrieval:
    """Tests for schema ARN retrieval from function tags."""

    @patch('os.environ', {'FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY': 'schema-arn-tag'})
    @patch('awslabs.lambda_mcp_server.server.FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY', 'schema-arn-tag')
    def test_get_schema_arn_from_tags(self):
        """Test getting schema ARN from function tags."""
        schema_arn = 'arn:aws:schemas:us-east-1:123456789012:schema/registry/schema'

        with patch('awslabs.lambda_mcp_server.server.lambda_client') as mock_client:
            # Set up the mock
            mock_client.list_tags.return_value = {
                'Tags': {'schema-arn-tag': schema_arn}
            }

            # Call the function
            result = get_schema_arn_from_function_arn('test-function-arn')

            # Verify the result
            assert result == schema_arn

            # Verify the client was called correctly
            mock_client.list_tags.assert_called_once_with(Resource='test-function-arn')

    def test_get_schema_arn_no_tag_key_configured(self):
        """Test when tag key is not configured."""
        with patch('awslabs.lambda_mcp_server.server.FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY', None):
            with patch('awslabs.lambda_mcp_server.server.lambda_client') as mock_client:
                # Call the function
                result = get_schema_arn_from_function_arn('test-function-arn')

                # Verify the result is None
                assert result is None

                # Verify client was not called
                mock_client.list_tags.assert_not_called()

    def test_get_schema_arn_tag_not_found(self):
        """Test when schema ARN tag is not found."""
        with patch('os.environ', {'FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY': 'schema-arn-tag'}):
            with patch('awslabs.lambda_mcp_server.server.FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY', 'schema-arn-tag'):
                with patch('awslabs.lambda_mcp_server.server.lambda_client') as mock_client:
                    # Set up the mock with different tag
                    mock_client.list_tags.return_value = {
                        'Tags': {'different-tag': 'value'}
                    }

                    # Call the function
                    result = get_schema_arn_from_function_arn('test-function-arn')

                    # Verify the result is None
                    assert result is None

    def test_get_schema_arn_client_error(self, caplog):
        """Test handling of tag retrieval errors."""
        with patch('os.environ', {'FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY': 'schema-arn-tag'}):
            with patch('awslabs.lambda_mcp_server.server.FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY', 'schema-arn-tag'):
                with patch('awslabs.lambda_mcp_server.server.lambda_client') as mock_client:
                    # Set up the mock to raise an exception
                    mock_client.list_tags.side_effect = Exception('Tag retrieval error')

                    with caplog.at_level(logging.WARNING):
                        # Call the function
                        result = get_schema_arn_from_function_arn('test-function-arn')

                        # Verify the result is None
                        assert result is None

                        # Verify error was logged
                        assert 'Error checking tags for function' in caplog.text
                        assert 'Tag retrieval error' in caplog.text


class TestToolCreationWithSchema:
    """Tests for Lambda tool creation with schemas."""

    @patch('awslabs.lambda_mcp_server.server.mcp')
    def test_create_tool_with_valid_schema(self, mock_mcp):
        """Test creating tool with valid schema."""
        # Set up the mocks
        mock_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_decorator

        schema_content = {
            "type": "object",
            "properties": {
                "test": {"type": "string"}
            }
        }

        with patch('awslabs.lambda_mcp_server.server.get_schema_from_registry') as mock_get_schema:
            # Set up the schema mock
            mock_get_schema.return_value = schema_content

            # Call the function
            function_name = 'test-function'
            description = 'Test function description'
            schema_arn = 'arn:aws:schemas:us-east-1:123456789012:schema/registry/schema'
            create_lambda_tool(function_name, description, schema_arn)

            # Verify schema was fetched
            mock_get_schema.assert_called_once_with(schema_arn)

            # Verify tool was created with schema in description
            mock_mcp.tool.assert_called_once_with(name='test_function')
            decorated_function = mock_decorator.call_args[0][0]
            assert description in decorated_function.__doc__
            assert str(schema_content) in decorated_function.__doc__

    @patch('awslabs.lambda_mcp_server.server.mcp')
    def test_create_tool_schema_fetch_error(self, mock_mcp, caplog):
        """Test tool creation when schema fetch fails."""
        # Set up the mocks
        mock_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_decorator

        with patch('awslabs.lambda_mcp_server.server.get_schema_from_registry') as mock_get_schema:
            # Set up the schema mock to return None (error case)
            mock_get_schema.return_value = None

            with caplog.at_level(logging.WARNING):
                # Call the function
                function_name = 'test-function'
                description = 'Test function description'
                schema_arn = 'arn:aws:schemas:us-east-1:123456789012:schema/registry/schema'
                create_lambda_tool(function_name, description, schema_arn)

                # Verify schema was attempted to be fetched
                mock_get_schema.assert_called_once_with(schema_arn)

                # Verify tool was created with original description
                mock_mcp.tool.assert_called_once_with(name='test_function')
                decorated_function = mock_decorator.call_args[0][0]
                assert decorated_function.__doc__ == description

    @patch('awslabs.lambda_mcp_server.server.mcp')
    def test_create_tool_without_schema(self, mock_mcp):
        """Test creating tool without schema ARN."""
        # Set up the mocks
        mock_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_decorator

        # Call the function without schema ARN
        function_name = 'test-function'
        description = 'Test function description'
        create_lambda_tool(function_name, description)

        # Verify tool was created with original description
        mock_mcp.tool.assert_called_once_with(name='test_function')
        decorated_function = mock_decorator.call_args[0][0]
        assert decorated_function.__doc__ == description
