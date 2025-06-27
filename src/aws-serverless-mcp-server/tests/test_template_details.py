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
"""Tests for the template_details resource."""

import json
import pytest
from awslabs.aws_serverless_mcp_server.resources.template_details import handle_template_details


class TestTemplateDetails:
    """Tests for the template_details resource."""

    @pytest.mark.parametrize('template_name', ['backend', 'frontend', 'fullstack'])
    def test_handle_template_details_valid_templates(self, template_name):
        """Test the handle_template_details function with valid template names."""
        # Call the function
        result = handle_template_details(template_name)

        # Verify the result structure
        assert 'contents' in result
        assert 'metadata' in result
        assert 'name' in result['metadata']
        assert result['metadata']['name'] == template_name

        # Verify the contents
        assert len(result['contents']) == 1
        assert result['contents'][0]['uri'] == f'template:{template_name}'

        # Parse the template details
        template_details = json.loads(result['contents'][0]['text'])

        # Verify the template details structure
        assert 'name' in template_details
        assert template_details['name'] == template_name
        assert 'description' in template_details
        assert 'frameworks' in template_details
        assert isinstance(template_details['frameworks'], list)
        assert 'parameters' in template_details
        assert 'example' in template_details

    def test_handle_template_details_invalid_template(self):
        """Test the handle_template_details function with an invalid template name."""
        # Call the function with an invalid template name
        invalid_template_name = 'nonexistent'
        result = handle_template_details(invalid_template_name)

        # Verify the result structure for an error response
        assert 'contents' in result
        assert 'metadata' in result
        assert 'error' in result['metadata']
        assert f"Template '{invalid_template_name}' not found" in result['metadata']['error']

        # Verify the contents
        assert len(result['contents']) == 1
        assert result['contents'][0]['uri'] == f'template:{invalid_template_name}'

        # Parse the error message
        error_message = json.loads(result['contents'][0]['text'])
        assert 'error' in error_message
        assert f"Template '{invalid_template_name}' not found" in error_message['error']

    def test_backend_template_details(self):
        """Test the specific structure of the backend template."""
        result = handle_template_details('backend')
        template_details = json.loads(result['contents'][0]['text'])

        # Verify backend-specific parameters
        assert 'runtime' in template_details['parameters']
        assert 'memorySize' in template_details['parameters']
        assert 'timeout' in template_details['parameters']

        # Verify example configuration
        assert template_details['example']['deploymentType'] == 'backend'
        assert 'backendConfiguration' in template_details['example']['configuration']

    def test_frontend_template_details(self):
        """Test the specific structure of the frontend template."""
        result = handle_template_details('frontend')
        template_details = json.loads(result['contents'][0]['text'])

        # Verify frontend-specific parameters
        assert 'type' in template_details['parameters']
        assert 'indexDocument' in template_details['parameters']
        assert 'errorDocument' in template_details['parameters']

        # Verify example configuration
        assert template_details['example']['deploymentType'] == 'frontend'
        assert 'frontendConfiguration' in template_details['example']['configuration']

    def test_fullstack_template_details(self):
        """Test the specific structure of the fullstack template."""
        result = handle_template_details('fullstack')
        template_details = json.loads(result['contents'][0]['text'])

        # Verify fullstack-specific parameters
        assert 'backend' in template_details['parameters']
        assert 'frontend' in template_details['parameters']

        # Verify example configuration
        assert template_details['example']['deploymentType'] == 'fullstack'
        assert 'backendConfiguration' in template_details['example']['configuration']
        assert 'frontendConfiguration' in template_details['example']['configuration']
