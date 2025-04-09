"""Tests for the diagrams module of the diagrams-mcp-server."""

import os
import pytest
from awslabs.aws_diagram_mcp_server.diagrams import (
    generate_diagram,
    get_diagram_examples,
    list_diagram_icons,
)
from awslabs.aws_diagram_mcp_server.models import DiagramType


class TestGetDiagramExamples:
    """Tests for the get_diagram_examples function."""

    def test_get_all_examples(self):
        """Test getting all diagram examples."""
        response = get_diagram_examples(DiagramType.ALL)
        assert response.examples is not None
        assert len(response.examples) > 0
        # Check that we have examples for each diagram type
        assert any(key.startswith('aws_') for key in response.examples.keys())
        assert any(key.startswith('sequence') for key in response.examples.keys())
        assert any(key.startswith('flow') for key in response.examples.keys())
        assert any(key.startswith('class') for key in response.examples.keys())
        assert any(key.startswith('k8s_') for key in response.examples.keys())
        assert any(key.startswith('onprem_') for key in response.examples.keys())
        assert any(key.startswith('custom_') for key in response.examples.keys())

    def test_get_aws_examples(self):
        """Test getting AWS diagram examples."""
        response = get_diagram_examples(DiagramType.AWS)
        assert response.examples is not None
        assert len(response.examples) > 0
        # Check that all examples are AWS examples
        assert all(key.startswith('aws_') for key in response.examples.keys())
        # Check that we have the expected AWS examples
        assert 'aws_basic' in response.examples
        assert 'aws_grouped_workers' in response.examples
        assert 'aws_clustered_web_services' in response.examples
        assert 'aws_event_processing' in response.examples
        assert 'aws_bedrock' in response.examples

    def test_get_sequence_examples(self):
        """Test getting sequence diagram examples."""
        response = get_diagram_examples(DiagramType.SEQUENCE)
        assert response.examples is not None
        assert len(response.examples) > 0
        # Check that we have the sequence example
        assert 'sequence' in response.examples

    def test_get_flow_examples(self):
        """Test getting flow diagram examples."""
        response = get_diagram_examples(DiagramType.FLOW)
        assert response.examples is not None
        assert len(response.examples) > 0
        # Check that we have the flow example
        assert 'flow' in response.examples

    def test_get_class_examples(self):
        """Test getting class diagram examples."""
        response = get_diagram_examples(DiagramType.CLASS)
        assert response.examples is not None
        assert len(response.examples) > 0
        # Check that we have the class example
        assert 'class' in response.examples

    def test_get_k8s_examples(self):
        """Test getting Kubernetes diagram examples."""
        response = get_diagram_examples(DiagramType.K8S)
        assert response.examples is not None
        assert len(response.examples) > 0
        # Check that we have the expected K8s examples
        assert 'k8s_exposed_pod' in response.examples
        assert 'k8s_stateful' in response.examples

    def test_get_onprem_examples(self):
        """Test getting on-premises diagram examples."""
        response = get_diagram_examples(DiagramType.ONPREM)
        assert response.examples is not None
        assert len(response.examples) > 0
        # Check that we have the expected on-premises examples
        assert 'onprem_web_service' in response.examples
        assert 'onprem_web_service_colored' in response.examples

    def test_get_custom_examples(self):
        """Test getting custom diagram examples."""
        response = get_diagram_examples(DiagramType.CUSTOM)
        assert response.examples is not None
        assert len(response.examples) > 0
        # Check that we have the custom example
        assert 'custom_rabbitmq' in response.examples


class TestListDiagramIcons:
    """Tests for the list_diagram_icons function."""

    def test_list_icons(self):
        """Test listing diagram icons."""
        response = list_diagram_icons()
        assert response.providers is not None
        assert len(response.providers) > 0
        # Check that we have the expected providers
        assert 'aws' in response.providers
        assert 'gcp' in response.providers
        assert 'k8s' in response.providers
        assert 'onprem' in response.providers
        assert 'programming' in response.providers
        # Check that we have services for AWS
        assert 'compute' in response.providers['aws']
        assert 'database' in response.providers['aws']
        assert 'network' in response.providers['aws']
        # Check that we have icons for AWS compute
        assert 'EC2' in response.providers['aws']['compute']
        assert 'Lambda' in response.providers['aws']['compute']


class TestGenerateDiagram:
    """Tests for the generate_diagram function."""

    @pytest.mark.asyncio
    async def test_generate_diagram_success(self, aws_diagram_code, temp_workspace_dir):
        """Test successful diagram generation."""
        result = await generate_diagram(
            code=aws_diagram_code,
            filename='test_aws_diagram',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'success'
        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.path.endswith('.png')
        # Check that the file is in the expected location
        expected_path = os.path.join(
            temp_workspace_dir, 'generated-diagrams', 'test_aws_diagram.png'
        )
        assert result.path == expected_path

    @pytest.mark.asyncio
    async def test_generate_diagram_with_absolute_path(self, aws_diagram_code, temp_workspace_dir):
        """Test diagram generation with an absolute path."""
        absolute_path = os.path.join(temp_workspace_dir, 'absolute_path_diagram')
        result = await generate_diagram(
            code=aws_diagram_code,
            filename=absolute_path,
        )
        assert result.status == 'success'
        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.path.endswith('.png')
        # Check that the file is in the expected location
        expected_path = f'{absolute_path}.png'
        assert result.path == expected_path

    @pytest.mark.asyncio
    async def test_generate_diagram_with_random_filename(
        self, aws_diagram_code, temp_workspace_dir
    ):
        """Test diagram generation with a random filename."""
        result = await generate_diagram(
            code=aws_diagram_code,
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'success'
        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.path.endswith('.png')
        # Check that the file is in the expected location
        assert os.path.dirname(result.path) == os.path.join(
            temp_workspace_dir, 'generated-diagrams'
        )
        assert os.path.basename(result.path).startswith('diagram_')

    @pytest.mark.asyncio
    async def test_generate_diagram_with_invalid_code(
        self, invalid_diagram_code, temp_workspace_dir
    ):
        """Test diagram generation with invalid code."""
        result = await generate_diagram(
            code=invalid_diagram_code,
            filename='test_invalid_diagram',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'error'
        assert result.path is None
        assert 'error' in result.message.lower()

    @pytest.mark.asyncio
    async def test_generate_diagram_with_dangerous_code(
        self, dangerous_diagram_code, temp_workspace_dir
    ):
        """Test diagram generation with dangerous code."""
        result = await generate_diagram(
            code=dangerous_diagram_code,
            filename='test_dangerous_diagram',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'error'
        assert result.path is None
        assert 'security issues' in result.message.lower()

    @pytest.mark.asyncio
    async def test_generate_diagram_with_timeout(self, aws_diagram_code, temp_workspace_dir):
        """Test diagram generation with a timeout."""
        # Use a very short timeout to force a timeout error
        result = await generate_diagram(
            code=aws_diagram_code,
            filename='test_timeout_diagram',
            timeout=1,  # 1 second timeout
            workspace_dir=temp_workspace_dir,
        )
        # The test could pass or fail depending on how fast the diagram is generated
        # If it's fast enough, it will succeed; if not, it will timeout
        if result.status == 'error':
            assert 'timeout' in result.message.lower()
        else:
            assert result.status == 'success'
            assert result.path is not None
            assert os.path.exists(result.path)

    @pytest.mark.asyncio
    async def test_generate_sequence_diagram(self, sequence_diagram_code, temp_workspace_dir):
        """Test generating a sequence diagram."""
        result = await generate_diagram(
            code=sequence_diagram_code,
            filename='test_sequence_diagram',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'success'
        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.path.endswith('.png')

    @pytest.mark.asyncio
    async def test_generate_flow_diagram(self, flow_diagram_code, temp_workspace_dir):
        """Test generating a flow diagram."""
        result = await generate_diagram(
            code=flow_diagram_code,
            filename='test_flow_diagram',
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'success'
        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.path.endswith('.png')
        # Check that the file is in the expected location
        expected_path = os.path.join(
            temp_workspace_dir, 'generated-diagrams', 'test_flow_diagram.png'
        )
        assert result.path == expected_path


    @pytest.mark.asyncio
    async def test_generate_diagram_with_show_parameter(self, temp_workspace_dir):
        """Test diagram generation with show parameter already set."""
        code = """with Diagram("Test Show Parameter", show=False, filename='test_show_param'):
    ELB("lb") >> EC2("web") >> RDS("userdb")
"""
        result = await generate_diagram(
            code=code,
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'success'
        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.path.endswith('.png')

    @pytest.mark.asyncio
    async def test_generate_diagram_with_filename_parameter(self, temp_workspace_dir):
        """Test diagram generation with filename parameter already set."""
        code = """with Diagram("Test Filename Parameter", filename='test_filename_param'):
    ELB("lb") >> EC2("web") >> RDS("userdb")
"""
        result = await generate_diagram(
            code=code,
            workspace_dir=temp_workspace_dir,
        )
        assert result.status == 'success'
        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.path.endswith('.png')
        # The filename in the code should be overridden by the workspace_dir path
        assert os.path.dirname(result.path) == os.path.join(
            temp_workspace_dir, 'generated-diagrams'
        )
