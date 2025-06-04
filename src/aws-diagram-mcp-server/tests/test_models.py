#
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
#

"""Tests for the models module of the diagrams-mcp-server."""

import os
import pytest
import tempfile
from awslabs.aws_diagram_mcp_server.models import (
    DiagramExampleResponse,
    DiagramGenerateRequest,
    DiagramGenerateResponse,
    DiagramIconsResponse,
    DiagramType,
)
from pydantic import ValidationError


class TestDiagramType:
    """Tests for the DiagramType enum."""

    def test_diagram_type_values(self):
        """Test that DiagramType enum has the expected values."""
        assert DiagramType.AWS == 'aws'
        assert DiagramType.SEQUENCE == 'sequence'
        assert DiagramType.FLOW == 'flow'
        assert DiagramType.CLASS == 'class'
        assert DiagramType.K8S == 'k8s'
        assert DiagramType.ONPREM == 'onprem'
        assert DiagramType.CUSTOM == 'custom'
        assert DiagramType.ALL == 'all'

    def test_diagram_type_from_string(self):
        """Test that DiagramType can be created from strings."""
        assert DiagramType('aws') == DiagramType.AWS
        assert DiagramType('sequence') == DiagramType.SEQUENCE
        assert DiagramType('flow') == DiagramType.FLOW
        assert DiagramType('class') == DiagramType.CLASS
        assert DiagramType('k8s') == DiagramType.K8S
        assert DiagramType('onprem') == DiagramType.ONPREM
        assert DiagramType('custom') == DiagramType.CUSTOM
        assert DiagramType('all') == DiagramType.ALL

    def test_invalid_diagram_type(self):
        """Test that invalid diagram types raise an error."""
        with pytest.raises(ValueError):
            DiagramType('invalid')


class TestDiagramGenerateRequest:
    """Tests for the DiagramGenerateRequest model."""

    def test_valid_request(self):
        """Test that a valid request is accepted."""
        request = DiagramGenerateRequest(
            code='with Diagram("Test", show=False):\n    ELB("lb") >> EC2("web")',
            filename='test',
            timeout=60,
            workspace_dir=tempfile.gettempdir(),
        )
        assert request.code == 'with Diagram("Test", show=False):\n    ELB("lb") >> EC2("web")'
        assert request.filename == 'test'
        assert request.timeout == 60
        assert request.workspace_dir == tempfile.gettempdir()

    def test_minimal_request(self):
        """Test that a minimal request with only required fields is accepted."""
        request = DiagramGenerateRequest(
            code='with Diagram("Test", show=False):\n    ELB("lb") >> EC2("web")',
            filename=None,
            timeout=90,
            workspace_dir=None,
        )
        assert request.code == 'with Diagram("Test", show=False):\n    ELB("lb") >> EC2("web")'
        assert request.filename is None
        assert request.timeout == 90  # Default value
        assert request.workspace_dir is None

    def test_invalid_code(self):
        """Test that code without a Diagram definition is rejected."""
        with pytest.raises(ValidationError):
            DiagramGenerateRequest(
                code='print("Hello, world!")',
                filename=None,
                timeout=90,
                workspace_dir=None,
            )

    def test_invalid_timeout(self):
        """Test that invalid timeout values are rejected."""
        with pytest.raises(ValidationError):
            DiagramGenerateRequest(
                code='with Diagram("Test", show=False):\n    ELB("lb") >> EC2("web")',
                filename=None,
                timeout=0,
                workspace_dir=None,
            )
        with pytest.raises(ValidationError):
            DiagramGenerateRequest(
                code='with Diagram("Test", show=False):\n    ELB("lb") >> EC2("web")',
                filename=None,
                timeout=301,  # Greater than the maximum allowed (300)
                workspace_dir=None,
            )


class TestDiagramGenerateResponse:
    """Tests for the DiagramGenerateResponse model."""

    def test_success_response(self):
        """Test that a success response is created correctly."""
        response = DiagramGenerateResponse(
            status='success',
            path=os.path.join(tempfile.gettempdir(), 'diagram.png'),
            message='Diagram generated successfully',
        )
        assert response.status == 'success'
        assert response.path == os.path.join(tempfile.gettempdir(), 'diagram.png')
        assert response.message == 'Diagram generated successfully'

    def test_error_response(self):
        """Test that an error response is created correctly."""
        response = DiagramGenerateResponse(
            status='error',
            message='Error generating diagram',
        )
        assert response.status == 'error'
        assert response.path is None
        assert response.message == 'Error generating diagram'


class TestDiagramExampleResponse:
    """Tests for the DiagramExampleResponse model."""

    def test_example_response(self):
        """Test that an example response is created correctly."""
        response = DiagramExampleResponse(
            examples={
                'aws': 'with Diagram("AWS", show=False):\n    ELB("lb") >> EC2("web")',
                'sequence': 'with Diagram("Sequence", show=False):\n    User("user") >> Action("action")',
            }
        )
        assert len(response.examples) == 2
        assert 'aws' in response.examples
        assert 'sequence' in response.examples
        assert response.examples['aws'].startswith('with Diagram("AWS", show=False):')
        assert response.examples['sequence'].startswith('with Diagram("Sequence", show=False):')


class TestDiagramIconsResponse:
    """Tests for the DiagramIconsResponse model."""

    def test_icons_response(self):
        """Test that an icons response is created correctly."""
        response = DiagramIconsResponse(
            providers={
                'aws': {
                    'compute': ['EC2', 'Lambda'],
                    'database': ['RDS', 'DynamoDB'],
                },
                'gcp': {
                    'compute': ['GCE', 'GKE'],
                },
            }
        )
        assert len(response.providers) == 2
        assert 'aws' in response.providers
        assert 'gcp' in response.providers
        assert 'compute' in response.providers['aws']
        assert 'database' in response.providers['aws']
        assert 'compute' in response.providers['gcp']
        assert 'EC2' in response.providers['aws']['compute']
        assert 'Lambda' in response.providers['aws']['compute']
        assert 'RDS' in response.providers['aws']['database']
        assert 'DynamoDB' in response.providers['aws']['database']
        assert 'GCE' in response.providers['gcp']['compute']
        assert 'GKE' in response.providers['gcp']['compute']
