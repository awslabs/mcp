"""Tests for the server module of the diagrams-mcp-server."""

import os
import pytest
import tempfile
from awslabs.aws_diagram_mcp_server.models import DiagramType
from awslabs.aws_diagram_mcp_server.server import (
    mcp_generate_diagram,
    mcp_get_diagram_examples,
    mcp_list_diagram_icons,
)
from unittest.mock import MagicMock, patch


class TestMcpGenerateDiagram:
    """Tests for the mcp_generate_diagram function."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_diagram_mcp_server.server.generate_diagram')
    async def test_generate_diagram(self, mock_generate_diagram):
        """Test the mcp_generate_diagram function."""
        # Set up the mock
        mock_generate_diagram.return_value = MagicMock(
            model_dump=MagicMock(
                return_value={
                    'status': 'success',
                    'path': os.path.join(tempfile.gettempdir(), 'diagram.png'),
                    'message': 'Diagram generated successfully',
                }
            )
        )

        # Call the function
        result = await mcp_generate_diagram(
            code='with Diagram("Test", show=False):\n    ELB("lb") >> EC2("web")',
            filename='test',
            timeout=60,
            workspace_dir=tempfile.gettempdir(),
        )

        # Check the result
        assert result == {
            'status': 'success',
            'path': os.path.join(tempfile.gettempdir(), 'diagram.png'),
            'message': 'Diagram generated successfully',
        }

        # Check that generate_diagram was called with the correct arguments
        mock_generate_diagram.assert_called_once_with(
            'with Diagram("Test", show=False):\n    ELB("lb") >> EC2("web")',
            'test',
            60,
            tempfile.gettempdir(),
        )

    @pytest.mark.asyncio
    @patch('awslabs.aws_diagram_mcp_server.server.generate_diagram')
    async def test_generate_diagram_with_defaults(self, mock_generate_diagram):
        """Test the mcp_generate_diagram function with default values."""
        # Set up the mock
        mock_generate_diagram.return_value = MagicMock(
            model_dump=MagicMock(
                return_value={
                    'status': 'success',
                    'path': os.path.join(tempfile.gettempdir(), 'diagram.png'),
                    'message': 'Diagram generated successfully',
                }
            )
        )

        # Call the function with only the required arguments
        result = await mcp_generate_diagram(
            code='with Diagram("Test", show=False):\n    ELB("lb") >> EC2("web")',
        )

        # Check the result
        assert result == {
            'status': 'success',
            'path': os.path.join(tempfile.gettempdir(), 'diagram.png'),
            'message': 'Diagram generated successfully',
        }

        # Check that generate_diagram was called with the correct arguments
        mock_generate_diagram.assert_called_once_with(
            'with Diagram("Test", show=False):\n    ELB("lb") >> EC2("web")',
            None,  # Default filename
            90,  # Default timeout
            None,  # Default workspace_dir
        )

    @pytest.mark.asyncio
    @patch('awslabs.aws_diagram_mcp_server.server.generate_diagram')
    async def test_generate_diagram_error(self, mock_generate_diagram):
        """Test the mcp_generate_diagram function with an error."""
        # Set up the mock
        mock_generate_diagram.return_value = MagicMock(
            model_dump=MagicMock(
                return_value={
                    'status': 'error',
                    'path': None,
                    'message': 'Error generating diagram',
                }
            )
        )

        # Call the function
        result = await mcp_generate_diagram(
            code='with Diagram("Test", show=False):\n    ELB("lb") >> EC2("web")',
        )

        # Check the result
        assert result == {
            'status': 'error',
            'path': None,
            'message': 'Error generating diagram',
        }


class TestMcpGetDiagramExamples:
    """Tests for the mcp_get_diagram_examples function."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_diagram_mcp_server.server.get_diagram_examples')
    async def test_get_diagram_examples(self, mock_get_diagram_examples):
        """Test the mcp_get_diagram_examples function."""
        # Set up the mock
        mock_get_diagram_examples.return_value = MagicMock(
            model_dump=MagicMock(
                return_value={
                    'examples': {
                        'aws': 'with Diagram("AWS", show=False):\n    ELB("lb") >> EC2("web")',
                        'sequence': 'with Diagram("Sequence", show=False):\n    User("user") >> Action("action")',
                    }
                }
            )
        )

        # Call the function
        result = await mcp_get_diagram_examples(diagram_type=DiagramType.ALL)

        # Check the result
        assert result == {
            'examples': {
                'aws': 'with Diagram("AWS", show=False):\n    ELB("lb") >> EC2("web")',
                'sequence': 'with Diagram("Sequence", show=False):\n    User("user") >> Action("action")',
            }
        }

        # Check that get_diagram_examples was called with the correct arguments
        mock_get_diagram_examples.assert_called_once_with(DiagramType.ALL)

    @pytest.mark.asyncio
    @patch('awslabs.aws_diagram_mcp_server.server.get_diagram_examples')
    async def test_get_diagram_examples_with_specific_type(self, mock_get_diagram_examples):
        """Test the mcp_get_diagram_examples function with a specific diagram type."""
        # Set up the mock
        mock_get_diagram_examples.return_value = MagicMock(
            model_dump=MagicMock(
                return_value={
                    'examples': {
                        'aws': 'with Diagram("AWS", show=False):\n    ELB("lb") >> EC2("web")',
                    }
                }
            )
        )

        # Call the function
        result = await mcp_get_diagram_examples(diagram_type=DiagramType.AWS)

        # Check the result
        assert result == {
            'examples': {
                'aws': 'with Diagram("AWS", show=False):\n    ELB("lb") >> EC2("web")',
            }
        }

        # Check that get_diagram_examples was called with the correct arguments
        mock_get_diagram_examples.assert_called_once_with(DiagramType.AWS)


class TestMcpListDiagramIcons:
    """Tests for the mcp_list_diagram_icons function."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_diagram_mcp_server.server.list_diagram_icons')
    async def test_list_diagram_icons(self, mock_list_diagram_icons):
        """Test the mcp_list_diagram_icons function."""
        # Set up the mock
        mock_list_diagram_icons.return_value = MagicMock(
            model_dump=MagicMock(
                return_value={
                    'providers': {
                        'aws': {
                            'compute': ['EC2', 'Lambda'],
                            'database': ['RDS', 'DynamoDB'],
                        },
                        'gcp': {
                            'compute': ['GCE', 'GKE'],
                        },
                    }
                }
            )
        )

        # Call the function
        result = await mcp_list_diagram_icons()

        # Check the result
        assert result == {
            'providers': {
                'aws': {
                    'compute': ['EC2', 'Lambda'],
                    'database': ['RDS', 'DynamoDB'],
                },
                'gcp': {
                    'compute': ['GCE', 'GKE'],
                },
            }
        }

        # Check that list_diagram_icons was called
        mock_list_diagram_icons.assert_called_once()


class TestServerIntegration:
    """Integration tests for the server module."""

    @pytest.mark.asyncio
    async def test_server_tool_registration(self):
        """Test that the server tools are registered correctly."""
        # Import the server module
        from awslabs.aws_diagram_mcp_server.server import mcp

        # Check that the tools are registered
        assert 'generate_diagram' in [tool['name'] for tool in mcp._tools]
        assert 'get_diagram_examples' in [tool['name'] for tool in mcp._tools]
        assert 'list_icons' in [tool['name'] for tool in mcp._tools]

        # Check that the tools have the correct descriptions
        generate_diagram_tool = next(
            tool for tool in mcp._tools if tool['name'] == 'generate_diagram'
        )
        assert 'Generate a diagram from Python code' in generate_diagram_tool['description']

        get_diagram_examples_tool = next(
            tool for tool in mcp._tools if tool['name'] == 'get_diagram_examples'
        )
        assert (
            'Get example code for different types of diagrams'
            in get_diagram_examples_tool['description']
        )

        list_icons_tool = next(tool for tool in mcp._tools if tool['name'] == 'list_icons')
        assert (
            'List all available icons from the diagrams package' in list_icons_tool['description']
        )
