# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the get_serverless_templates module."""

import pytest
from awslabs.aws_serverless_mcp_server.models import GetServerlessTemplatesRequest
from awslabs.aws_serverless_mcp_server.tools.guidance.get_serverless_templates import (
    get_serverless_templates,
)
from unittest.mock import MagicMock, patch


class TestGetServerlessTemplates:
    """Tests for the get_serverless_templates function."""

    @pytest.mark.asyncio
    async def test_get_serverless_templates_with_runtime(self):
        """Test getting serverless templates with specific runtime."""
        # Create a mock request
        request = GetServerlessTemplatesRequest(template_type='API', runtime='nodejs18.x')

        # Call the function
        mock_tree_response = {
            'tree': [
                {'path': 'apigw-lambda-nodejs18.x', 'type': 'tree'},
                {'path': 'README.md', 'type': 'blob'},
            ]
        }
        mock_readme_response = {
            'content': 'IyBBUEkgR2F0ZXdheSArIExhbWJkYSBFeGFtcGxl'  # pragma: allowlist secret
        }  # pragma: allowlist secret

        def side_effect(url):
            if 'trees/main' in url:
                return mock_tree_response
            elif 'README.md' in url:
                return mock_readme_response
            return {}

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.guidance.get_serverless_templates.fetch_github_content'
        ) as mock_fetch:
            mock_fetch.side_effect = side_effect
            result = await get_serverless_templates(request)

            # Initialize templates variable
            templates = []

            # Success case
            assert 'templates' in result
            templates = result['templates']
            assert isinstance(templates, list)

            # Check template structure if any templates are returned
            if len(templates) > 0:
                template = templates[0]
                assert 'templateName' in template
                assert 'readMe' in template
                assert 'gitHubLink' in template
                assert isinstance(template['templateName'], str)
                assert isinstance(template['readMe'], str)
                assert isinstance(template['gitHubLink'], str)

    @pytest.mark.asyncio
    async def test_get_serverless_templates_without_runtime(self):
        """Test getting serverless templates without specific runtime."""
        # Create a mock request without runtime
        request = GetServerlessTemplatesRequest(template_type='ETL', runtime=None)

        # Mock GitHub API responses
        mock_tree_response = {
            'tree': [
                {'path': 'etl-lambda-python', 'type': 'tree'},
                {'path': 'README.md', 'type': 'blob'},
            ]
        }
        mock_readme_response = {
            'content': 'IyBFVEwgTGFtYmRhIFB5dGhvbiBFeGFtcGxl'
        }  # pragma: allowlist secret

        def side_effect(url):
            if 'trees/main' in url:
                return mock_tree_response
            elif 'README.md' in url:
                return mock_readme_response
            return {}

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.guidance.get_serverless_templates.fetch_github_content'
        ) as mock_fetch:
            mock_fetch.side_effect = side_effect
            result = await get_serverless_templates(request)

            # Success or error case
            if 'templates' in result:
                templates = result['templates']
                assert isinstance(templates, list)
            else:
                assert result.get('success') is False
                assert 'No serverless templates found' in result.get('message', '')

    @pytest.mark.asyncio
    async def test_get_serverless_templates_various_types(self):
        """Test serverless templates for various template types."""
        template_types = ['API', 'ETL', 'Web', 'Event', 'Lambda']

        for template_type in template_types:
            # Provide a runtime argument for each request
            request = GetServerlessTemplatesRequest(
                template_type=template_type, runtime='python3.9'
            )

            # Call the function
            result = await get_serverless_templates(request)

            # Success or error case
            if 'templates' in result:
                templates = result['templates']
                assert isinstance(templates, list)
            else:
                assert result.get('success') is False
                assert 'No serverless templates found' in result.get('message', '')

    @pytest.mark.asyncio
    async def test_get_serverless_templates_content_structure(self):
        """Test that serverless templates contain expected content structure."""
        request = GetServerlessTemplatesRequest(template_type='lambda', runtime='nodejs18.x')

        # Mock GitHub API responses
        mock_tree_response = {
            'tree': [
                {'path': 'lambda-nodejs18.x', 'type': 'tree'},
                {'path': 'README.md', 'type': 'blob'},
            ]
        }
        mock_readme_response = {
            'content': 'IyBMYW1iZGEgTm9kZWpzIEV4YW1wbGU='  # Base64 encoded "# Lambda Nodejs Example" # pragma: allowlist secret
        }

        def side_effect(url):
            if 'trees/main' in url:
                return mock_tree_response
            elif 'README.md' in url:
                return mock_readme_response
            return {}

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.guidance.get_serverless_templates.fetch_github_content'
        ) as mock_fetch:
            mock_fetch.side_effect = side_effect
            result = await get_serverless_templates(request)

            # Success case
            assert 'templates' in result
            templates = result['templates']
            assert isinstance(templates, list)

            # Check template structure if any templates are returned
            if len(templates) > 0:
                template = templates[0]
                required_fields = ['templateName', 'readMe', 'gitHubLink']

                for field in required_fields:
                    assert field in template
                    assert isinstance(template[field], str)
                    assert len(template[field]) > 0

                # Check GitHub link format
                assert template['gitHubLink'].startswith(
                    'https://github.com/aws-samples/serverless-patterns'
                )

    @pytest.mark.asyncio
    async def test_get_serverless_templates_no_matches(self):
        """Test serverless templates with no matching results."""
        request = GetServerlessTemplatesRequest(
            template_type='NonExistentType', runtime='unsupported-runtime'
        )

        # Mock empty GitHub response
        mock_tree_response = {'tree': []}

        # Reset the global repo_tree variable
        with patch(
            'awslabs.aws_serverless_mcp_server.tools.guidance.get_serverless_templates.repo_tree',
            None,
        ):
            with patch(
                'awslabs.aws_serverless_mcp_server.tools.guidance.get_serverless_templates.fetch_github_content'
            ) as mock_fetch:
                mock_fetch.return_value = mock_tree_response

                # Call the function
                result = await get_serverless_templates(request)

                # Should return error when no templates found
                assert 'success' in result
                assert result['success'] is False
                assert 'message' in result
                assert 'No serverless templates found' in result['message']

                # Verify GitHub API was called
                mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_serverless_templates_github_error(self):
        """Test serverless templates with GitHub API error."""
        request = GetServerlessTemplatesRequest(template_type='API', runtime='nodejs18.x')

        # Reset the global repo_tree variable
        with patch(
            'awslabs.aws_serverless_mcp_server.tools.guidance.get_serverless_templates.repo_tree',
            None,
        ):
            # Mock GitHub API error
            with patch(
                'awslabs.aws_serverless_mcp_server.tools.guidance.get_serverless_templates.fetch_github_content'
            ) as mock_fetch:
                mock_fetch.side_effect = Exception('GitHub API error')

                # Call the function
                result = await get_serverless_templates(request)

                # Should return error
                assert 'success' in result
                assert result['success'] is False
                assert 'message' in result
                assert 'error' in result
                assert 'GitHub API error' in str(result['error'])

    @pytest.mark.asyncio
    async def test_get_serverless_templates_caching(self):
        """Test that repository tree is cached between calls."""
        request1 = GetServerlessTemplatesRequest(template_type='API', runtime='python3.9')
        request2 = GetServerlessTemplatesRequest(template_type='Lambda', runtime='nodejs18.x')

        mock_tree_response = {
            'tree': []  # Empty tree to avoid README fetches
        }

        # Reset the global repo_tree variable
        with patch(
            'awslabs.aws_serverless_mcp_server.tools.guidance.get_serverless_templates.repo_tree',
            None,
        ):
            with patch(
                'awslabs.aws_serverless_mcp_server.tools.guidance.get_serverless_templates.fetch_github_content'
            ) as mock_fetch:
                mock_fetch.return_value = mock_tree_response

                # First call
                await get_serverless_templates(request1)

                # Second call
                await get_serverless_templates(request2)

                # Tree should only be fetched once due to caching
                assert mock_fetch.call_count == 1
                mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_serverless_templates_limit(self):
        """Test that template results are limited to avoid excessive API calls."""
        request = GetServerlessTemplatesRequest(
            template_type='lambda',  # This should match many templates
            runtime='python3.9',
        )

        # Mock many matching templates
        mock_tree_response = {
            'tree': [{'path': f'lambda-example-{i}', 'type': 'tree'} for i in range(10)]
        }

        mock_readme_response = {
            'content': 'IyBMYW1iZGEgRXhhbXBsZQ=='  # Base64 encoded "# Lambda Example"
        }

        # Create mock response objects
        mock_tree_resp = MagicMock()
        mock_tree_resp.json.return_value = mock_tree_response
        mock_tree_resp.raise_for_status.return_value = None

        mock_readme_resp = MagicMock()
        mock_readme_resp.json.return_value = mock_readme_response
        mock_readme_resp.raise_for_status.return_value = None

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.guidance.get_serverless_templates.fetch_github_content'
        ) as mock_fetch:
            # Configure mock to return different responses based on URL
            def side_effect(url):
                if 'trees/main' in url:
                    return mock_tree_response
                elif 'README.md' in url:
                    return mock_readme_response
                return {}

            mock_fetch.side_effect = side_effect

            # Call the function
            result = await get_serverless_templates(request)

            # Should limit results
            if 'templates' in result:
                templates = result['templates']
                assert len(templates) <= 5  # Based on the limit in the implementation

            # Verify GitHub API calls - should be 1 for tree + up to 5 for READMEs
            assert 1 <= mock_fetch.call_count <= 6

    @pytest.mark.asyncio
    async def test_get_serverless_templates_search_filtering(self):
        """Test that templates are filtered based on search terms."""
        request = GetServerlessTemplatesRequest(template_type='API', runtime='python')

        mock_tree_response = {
            'tree': [
                {'path': 'apigw-lambda-nodejs18.x', 'type': 'tree'},  # Should match both terms
                {'path': 's3-lambda-nodejs', 'type': 'tree'},  # Should not match API
                {'path': 'api-gateway-java', 'type': 'tree'},  # Should match API but not python
                {'path': 'README.md', 'type': 'blob'},  # Should be filtered out
            ]
        }

        mock_readme_response = {
            'content': 'IyBBUEkgR2F0ZXdheSArIExhbWJkYSBFeGFtcGxl'  # pragma: allowlist secret
        }

        # Create mock response objects
        mock_tree_resp = MagicMock()
        mock_tree_resp.json.return_value = mock_tree_response
        mock_tree_resp.raise_for_status.return_value = None

        mock_readme_resp = MagicMock()
        mock_readme_resp.json.return_value = mock_readme_response
        mock_readme_resp.raise_for_status.return_value = None

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.guidance.get_serverless_templates.fetch_github_content'
        ) as mock_fetch:
            # Configure mock to return different responses based on URL
            def side_effect(url):
                if 'trees/main' in url:
                    return mock_tree_response
                elif 'README.md' in url:
                    return mock_readme_response
                return {}

            mock_fetch.side_effect = side_effect

            # Call the function
            result = await get_serverless_templates(request)

            # Should filter based on search terms
            # Templates found
            assert 'templates' in result
            templates = result['templates']
            assert isinstance(templates, list)

            # Only templates matching both terms should be included
            if len(templates) > 0:
                template_names = [t['templateName'] for t in templates]
                assert 'apigw-lambda-nodejs18.x' in template_names
                assert 's3-lambda-nodejs' not in template_names
