"""Tests for the create_state_machine_tool function."""

import logging
import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_mcp_server.server import (
        create_state_machine_tool,
    )


class TestCreateTool:
    """Tests for the create_state_machine_tool function."""

    @pytest.fixture(autouse=True)
    def setup_schema_env(self):
        """Set up schema environment for tests."""
        with patch(
            'awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY',
            'schema-arn-tag',
        ):
            yield

    @patch('awslabs.stepfunctions_mcp_server.server.mcp')
    def test_create_tool_basic(self, mock_mcp):
        """Test creating a basic Step Functions tool."""
        # Set up test data
        state_machine_name = 'test-state-machine'
        description = 'Test state machine description'
        mock_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_decorator

        # Call the function
        create_state_machine_tool(
            state_machine_name,
            'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine',
            'STANDARD',
            description,
        )

        # Verify results
        mock_mcp.tool.assert_called_once_with(name='test_state_machine')
        mock_decorator.assert_called_once()
        decorated_function = mock_decorator.call_args[0][0]
        assert decorated_function.__doc__ == description

    @patch('awslabs.stepfunctions_mcp_server.server.mcp')
    @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_PREFIX', 'test-')
    def test_create_tool_with_prefix(self, mock_mcp):
        """Test creating a Step Functions tool with prefix."""
        # Set up test data
        state_machine_name = 'prefix-test-state-machine'
        description = 'Test state machine description'
        mock_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_decorator

        # Call the function
        create_state_machine_tool(
            state_machine_name,
            'arn:aws:states:us-east-1:123456789012:stateMachine:prefix-test-state-machine',
            'STANDARD',
            description,
        )

        # Verify results
        mock_mcp.tool.assert_called_once_with(name=state_machine_name.replace('-', '_'))

    @patch('awslabs.stepfunctions_mcp_server.server.mcp')
    @patch('awslabs.stepfunctions_mcp_server.server.get_schema_from_registry')
    def test_create_tool_with_schema(self, mock_get_schema, mock_mcp):
        """Test creating tool with valid schema."""
        # Set up test data
        state_machine_name = 'test-state-machine'
        state_machine_arn = 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine'
        description = 'Test state machine description'
        schema_arn = 'arn:aws:schemas:us-east-1:123456789012:schema/registry/schema'
        schema_content = {'type': 'object', 'properties': {'test': {'type': 'string'}}}
        mock_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_decorator
        mock_get_schema.return_value = schema_content

        # Call the function
        create_state_machine_tool(
            state_machine_name, state_machine_arn, 'STANDARD', description, schema_arn
        )

        # Verify results
        mock_get_schema.assert_called_once_with(schema_arn)
        mock_mcp.tool.assert_called_once_with(name='test_state_machine')
        decorated_function = mock_decorator.call_args[0][0]
        assert description in decorated_function.__doc__
        assert str(schema_content) in decorated_function.__doc__

    @patch('awslabs.stepfunctions_mcp_server.server.mcp')
    @patch('awslabs.stepfunctions_mcp_server.server.get_schema_from_registry')
    def test_create_tool_schema_error(self, mock_get_schema, mock_mcp, caplog):
        """Test tool creation when schema fetch fails."""
        # Set up test data
        state_machine_name = 'test-state-machine'
        state_machine_arn = 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine'
        description = 'Test state machine description'
        schema_arn = 'arn:aws:schemas:us-east-1:123456789012:schema/registry/schema'
        mock_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_decorator
        mock_get_schema.return_value = None

        # Call the function and check logging
        with caplog.at_level(logging.WARNING):
            create_state_machine_tool(
                state_machine_name, state_machine_arn, 'STANDARD', description, schema_arn
            )

            # Verify results
            mock_get_schema.assert_called_once_with(schema_arn)
            mock_mcp.tool.assert_called_once_with(name='test_state_machine')
            decorated_function = mock_decorator.call_args[0][0]
            assert decorated_function.__doc__ == description

    @pytest.mark.asyncio
    @patch('awslabs.stepfunctions_mcp_server.server.invoke_standard_state_machine_impl')
    @patch('awslabs.stepfunctions_mcp_server.server.invoke_express_state_machine_impl')
    @patch('awslabs.stepfunctions_mcp_server.server.mcp')
    async def test_create_tool_standard_impl(
        self, mock_mcp, mock_express_impl, mock_standard_impl
    ):
        """Test that STANDARD state machine uses standard implementation."""
        # Set up test data
        state_machine_name = 'test-standard-machine'
        state_machine_arn = (
            f'arn:aws:states:us-east-1:123456789012:stateMachine:{state_machine_name}'
        )
        description = 'Test standard state machine'
        mock_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_decorator

        # Call the function
        create_state_machine_tool(state_machine_name, state_machine_arn, 'STANDARD', description)

        # Get the decorated function
        decorated_function = mock_decorator.call_args[0][0]

        # Call the decorated function with test parameters
        ctx = MagicMock()
        await decorated_function({'test': 'value'}, ctx)

        # Verify results
        mock_standard_impl.assert_called_once_with(
            state_machine_name, state_machine_arn, {'test': 'value'}, ctx
        )
        mock_express_impl.assert_not_called()

    @pytest.mark.asyncio
    @patch('awslabs.stepfunctions_mcp_server.server.invoke_standard_state_machine_impl')
    @patch('awslabs.stepfunctions_mcp_server.server.invoke_express_state_machine_impl')
    @patch('awslabs.stepfunctions_mcp_server.server.mcp')
    async def test_create_tool_express_impl(self, mock_mcp, mock_express_impl, mock_standard_impl):
        """Test that EXPRESS state machine uses express implementation."""
        # Set up test data
        state_machine_name = 'test-express-machine'
        state_machine_arn = (
            f'arn:aws:states:us-east-1:123456789012:stateMachine:{state_machine_name}'
        )
        description = 'Test express state machine'
        mock_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_decorator

        # Call the function
        create_state_machine_tool(state_machine_name, state_machine_arn, 'EXPRESS', description)

        # Get the decorated function
        decorated_function = mock_decorator.call_args[0][0]

        # Call the decorated function with test parameters
        ctx = MagicMock()
        await decorated_function({'test': 'value'}, ctx)

        # Verify results
        mock_express_impl.assert_called_once_with(
            state_machine_name, state_machine_arn, {'test': 'value'}, ctx
        )
        mock_standard_impl.assert_not_called()
