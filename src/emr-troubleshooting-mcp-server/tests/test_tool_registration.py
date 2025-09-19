"""Tests for EMR troubleshooting tool registration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from awslabs.emr_troubleshooting_mcp_server.models import (
    EMRClusterAnalysisResponse,
    EMRLogAnalysisResponse,
)
from awslabs.emr_troubleshooting_mcp_server.tools import (
    EMRTroubleshootingTools,
)


class TestToolRegistration:
    """Test cases for EMR troubleshooting tool registration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tools = EMRTroubleshootingTools()
        self.mcp_mock = MagicMock()

        # Configure the tool decorator to capture the decorated function
        self.captured_tools = {}

        def mock_tool_decorator(*args, **kwargs):
            def decorator(func):
                name = kwargs.get('name', func.__name__)
                self.captured_tools[name] = func
                return func

            return decorator

        self.mcp_mock.tool = mock_tool_decorator

    @pytest.mark.asyncio
    async def test_analyze_emr_logs_tool_registration(self):
        """Test that analyze_emr_logs_tool properly awaits the async method."""
        # Create a mock response
        mock_response = EMRLogAnalysisResponse(
            matched_issues=[], summary='Test summary', total_matches=0
        )

        # Mock the analyze_emr_logs method to return our mock response
        with patch.object(self.tools, 'analyze_emr_logs', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_response

            # Register the tool with our mocked MCP instance
            self.tools.register(self.mcp_mock)

            # Get the captured tool function
            tool_func = self.captured_tools.get('analyze_emr_logs')
            assert tool_func is not None, 'Tool function was not registered'

            # Call the tool function with test data
            log_content = 'Test log content'
            result = await tool_func(log_content)

            # Verify that analyze_emr_logs was called with correct arguments
            mock_analyze.assert_called_once_with(log_content)

            # Verify that the result is our mock response
            assert result == mock_response

    @pytest.mark.asyncio
    async def test_analyze_emr_cluster_logs_tool_registration(self):
        """Test that analyze_emr_cluster_logs_tool awaits the async method."""
        # Create a mock response
        mock_response = EMRClusterAnalysisResponse(
            status='SUCCEEDED',
            source_type='cluster',
            source_id='j-test-cluster',
            issues_found=0,
            results=[],
        )

        # Mock the analyze_emr_cluster_logs method to return our mock response
        with patch.object(
            self.tools, 'analyze_emr_cluster_logs', new_callable=AsyncMock
        ) as mock_analyze:
            mock_analyze.return_value = mock_response

            # Register the tool with our mocked MCP instance
            self.tools.register(self.mcp_mock)

            # Get the captured tool function
            tool_func = self.captured_tools.get('analyze_emr_cluster_logs')
            assert tool_func is not None, 'Tool function was not registered'

            # Call the tool function with test data
            cluster_id = 'j-test-cluster'
            region = 'us-east-1'
            time_window = 3600
            result = await tool_func(cluster_id, region, time_window)

            # Verify that analyze_emr_cluster_logs was called correctly
            mock_analyze.assert_called_once_with(cluster_id, region, time_window)

            # Verify that the result is our mock response
            assert result == mock_response

    @pytest.mark.asyncio
    async def test_analyze_emr_logs_tool_error_handling(self):
        """Test that analyze_emr_logs_tool properly handles errors."""
        # Mock the analyze_emr_logs method to raise an exception
        with patch.object(self.tools, 'analyze_emr_logs', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = Exception('Test error')

            # Register the tool with our mocked MCP instance
            self.tools.register(self.mcp_mock)

            # Get the captured tool function
            tool_func = self.captured_tools.get('analyze_emr_logs')
            assert tool_func is not None, 'Tool function was not registered'

            # Call the tool function with test data
            log_content = 'Test log content'

            # The tool function should handle the exception and return an error
            with pytest.raises(Exception, match='Test error'):
                await tool_func(log_content)

            # Verify that analyze_emr_logs was called correctly
            mock_analyze.assert_called_once_with(log_content)

    @pytest.mark.asyncio
    async def test_analyze_emr_cluster_logs_tool_error_handling(self):
        """Test that analyze_emr_cluster_logs_tool handles errors."""
        # Mock the analyze_emr_cluster_logs method to raise an exception
        with patch.object(
            self.tools, 'analyze_emr_cluster_logs', new_callable=AsyncMock
        ) as mock_analyze:
            mock_analyze.side_effect = Exception('Test error')

            # Register the tool with our mocked MCP instance
            self.tools.register(self.mcp_mock)

            # Get the captured tool function
            tool_func = self.captured_tools.get('analyze_emr_cluster_logs')
            assert tool_func is not None, 'Tool function was not registered'

            # Call the tool function with test data
            cluster_id = 'j-test-cluster'
            region = 'us-east-1'
            time_window = 3600

            # The tool function should handle the exception and return an error
            with pytest.raises(Exception, match='Test error'):
                await tool_func(cluster_id, region, time_window)

            # Verify that analyze_emr_cluster_logs was called correctly
            mock_analyze.assert_called_once_with(cluster_id, region, time_window)


if __name__ == '__main__':
    pytest.main([__file__])
