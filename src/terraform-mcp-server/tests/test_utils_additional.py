"""Additional tests for the utils module of the terraform-mcp-server."""

import pytest
from awslabs.terraform_mcp_server.impl.tools.utils import (
    get_github_release_details,
    get_submodules,
    get_variables_tf,
)
from awslabs.terraform_mcp_server.models import TerraformVariable
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.asyncio


class TestGetGithubReleaseDetails:
    """Tests for the get_github_release_details function."""

    @pytest.mark.asyncio
    async def test_get_github_release_details_with_latest_release(self):
        """Test getting GitHub release details with a latest release."""
        # Mock the requests.get function
        with patch('requests.get') as mock_get:
            # Create a mock response for the latest release
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'tag_name': 'v1.0.0',
                'published_at': '2023-01-01T00:00:00Z',
            }
            mock_get.return_value = mock_response

            # Call the function
            result = await get_github_release_details('owner', 'repo')

            # Check that requests.get was called with the correct URL
            mock_get.assert_called_once_with(
                'https://api.github.com/repos/owner/repo/releases/latest'
            )

            # Check the result
            assert result['version'] == '1.0.0'
            assert result['details']['tag_name'] == 'v1.0.0'
            assert result['details']['published_at'] == '2023-01-01T00:00:00Z'

    @pytest.mark.asyncio
    async def test_get_github_release_details_with_tags(self):
        """Test getting GitHub release details with tags when no releases are found."""
        # Mock the requests.get function
        with patch('requests.get') as mock_get:
            # Create mock responses
            mock_release_response = MagicMock()
            mock_release_response.status_code = 404  # No releases found

            mock_tags_response = MagicMock()
            mock_tags_response.status_code = 200
            mock_tags_response.json.return_value = [
                {
                    'name': 'v0.9.0',
                    'commit': {
                        'sha': '1234567890abcdef',  # pragma: allowlist secret
                        'url': 'https://api.github.com/repos/owner/repo/commits/1234567890abcdef',
                    },
                },
                {
                    'name': 'v0.8.0',
                    'commit': {
                        'sha': '0987654321fedcba',  # pragma: allowlist secret
                        'url': 'https://api.github.com/repos/owner/repo/commits/0987654321fedcba',
                    },
                },
            ]

            # Configure the mock to return different responses for different URLs
            def side_effect(url):
                if 'releases/latest' in url:
                    return mock_release_response
                elif 'tags' in url:
                    return mock_tags_response
                return MagicMock(status_code=404)

            mock_get.side_effect = side_effect

            # Call the function
            result = await get_github_release_details('owner', 'repo')

            # Check that requests.get was called with the correct URLs
            assert mock_get.call_count == 2
            mock_get.assert_any_call('https://api.github.com/repos/owner/repo/releases/latest')
            mock_get.assert_any_call('https://api.github.com/repos/owner/repo/tags')

            # Check the result
            assert result['version'] == '0.9.0'
            assert result['details']['tag_name'] == 'v0.9.0'
            assert result['details']['published_at'] is None

    @pytest.mark.asyncio
    async def test_get_github_release_details_with_no_releases_or_tags(self):
        """Test getting GitHub release details with no releases or tags."""
        # Mock the requests.get function
        with patch('requests.get') as mock_get:
            # Create mock responses
            mock_release_response = MagicMock()
            mock_release_response.status_code = 404  # No releases found

            mock_tags_response = MagicMock()
            mock_tags_response.status_code = 200
            mock_tags_response.json.return_value = []  # No tags found

            # Configure the mock to return different responses for different URLs
            def side_effect(url):
                if 'releases/latest' in url:
                    return mock_release_response
                elif 'tags' in url:
                    return mock_tags_response
                return MagicMock(status_code=404)

            mock_get.side_effect = side_effect

            # Call the function
            result = await get_github_release_details('owner', 'repo')

            # Check that requests.get was called with the correct URLs
            assert mock_get.call_count == 2
            mock_get.assert_any_call('https://api.github.com/repos/owner/repo/releases/latest')
            mock_get.assert_any_call('https://api.github.com/repos/owner/repo/tags')

            # Check the result
            assert result['version'] == ''
            assert result['details'] == {}

    @pytest.mark.asyncio
    async def test_get_github_release_details_with_exception(self):
        """Test getting GitHub release details with an exception."""
        # Mock the requests.get function to raise an exception
        with patch('requests.get', side_effect=Exception('Test exception')):
            # Call the function
            result = await get_github_release_details('owner', 'repo')

            # Check the result
            assert result['version'] == ''
            assert result['details'] == {}


class TestGetSubmodules:
    """Tests for the get_submodules function."""

    @pytest.mark.asyncio
    async def test_get_submodules_with_submodules(self):
        """Test getting submodules with submodules."""
        # Mock the requests.get function
        with patch('requests.get') as mock_get:
            # Create mock responses
            mock_modules_response = MagicMock()
            mock_modules_response.status_code = 200
            mock_modules_response.json.return_value = [
                {
                    'name': 'submodule1',
                    'path': 'modules/submodule1',
                    'type': 'dir',
                },
                {
                    'name': 'submodule2',
                    'path': 'modules/submodule2',
                    'type': 'dir',
                },
                {
                    'name': 'not-a-dir',
                    'path': 'modules/not-a-dir',
                    'type': 'file',  # This should be filtered out
                },
            ]

            mock_readme1_response = MagicMock()
            mock_readme1_response.status_code = 200
            mock_readme1_response.text = """# Submodule 1

This is a description of submodule 1.

## Usage

```hcl
module "submodule1" {
  source = "./modules/submodule1"
}
```
"""

            mock_readme2_response = MagicMock()
            mock_readme2_response.status_code = 404  # No README found

            # Configure the mock to return different responses for different URLs
            def side_effect(url, **kwargs):
                if 'contents/modules' in url:
                    return mock_modules_response
                elif 'submodule1/README.md' in url:
                    return mock_readme1_response
                elif 'submodule2/README.md' in url:
                    return mock_readme2_response
                elif 'submodule2/readme.md' in url:
                    return mock_readme2_response
                return MagicMock(status_code=404)

            mock_get.side_effect = side_effect

            # Call the function with explicit branch parameter
            result = await get_submodules('owner', 'repo', 'master')

            # Check that requests.get was called with the correct URLs
            assert mock_get.call_count >= 3
            mock_get.assert_any_call(
                'https://api.github.com/repos/owner/repo/contents/modules?ref=master',
                headers={'Accept': 'application/vnd.github.v3+json'},
                timeout=3.0,
            )

            # Check the result
            assert len(result) == 2
            assert result[0].name == 'submodule1'
            assert result[0].path == 'modules/submodule1'
            assert 'This is a description of submodule 1.' in result[0].readme_content
            assert result[1].name == 'submodule2'
            assert result[1].path == 'modules/submodule2'

    @pytest.mark.asyncio
    async def test_get_submodules_with_no_modules_directory(self):
        """Test getting submodules with no modules directory."""
        # Mock the requests.get function
        with patch('requests.get') as mock_get:
            # Create a mock response
            mock_response = MagicMock()
            mock_response.status_code = 404  # No modules directory found
            mock_get.return_value = mock_response

            # Call the function with explicit branch parameter
            result = await get_submodules('owner', 'repo', 'master')

            # Check that requests.get was called with the correct URL
            mock_get.assert_called_once_with(
                'https://api.github.com/repos/owner/repo/contents/modules?ref=master',
                headers={'Accept': 'application/vnd.github.v3+json'},
                timeout=3.0,
            )

            # Check the result
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_submodules_with_rate_limit(self):
        """Test getting submodules with a rate limit error."""
        # Mock the requests.get function
        with patch('requests.get') as mock_get:
            # Create a mock response
            mock_response = MagicMock()
            mock_response.status_code = 403  # Rate limit exceeded
            mock_get.return_value = mock_response

            # Call the function with explicit branch parameter
            result = await get_submodules('owner', 'repo', 'master')

            # Check that requests.get was called with the correct URL
            mock_get.assert_called_once_with(
                'https://api.github.com/repos/owner/repo/contents/modules?ref=master',
                headers={'Accept': 'application/vnd.github.v3+json'},
                timeout=3.0,
            )

            # Check the result
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_submodules_with_exception(self):
        """Test getting submodules with an exception."""
        # Mock the requests.get function to raise an exception
        with patch('requests.get', side_effect=Exception('Test exception')):
            # Call the function
            result = await get_submodules('owner', 'repo')

            # Check the result
            assert len(result) == 0


class TestGetVariablesTf:
    """Tests for the get_variables_tf function."""

    @pytest.mark.asyncio
    async def test_get_variables_tf_with_variables(self):
        """Test getting variables.tf with variables."""
        # Mock the requests.get function
        with patch('requests.get') as mock_get:
            # Create a mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = """
variable "region" {
  type        = string
  description = "AWS region"
  default     = "us-west-2"
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type"
}
"""
            mock_get.return_value = mock_response

            # Mock the parse_variables_tf function
            with patch(
                'awslabs.terraform_mcp_server.impl.tools.utils.parse_variables_tf'
            ) as mock_parse:
                mock_var1 = TerraformVariable(
                    name='region',
                    type='string',
                    description='AWS region',
                    default='us-west-2',
                    required=False,
                )
                mock_var2 = TerraformVariable(
                    name='instance_type',
                    type='string',
                    description='EC2 instance type',
                    default=None,
                    required=True,
                )
                mock_parse.return_value = [mock_var1, mock_var2]

                # Call the function
                content, variables = await get_variables_tf('owner', 'repo')

                # Check that requests.get was called with the correct URL
                mock_get.assert_called_once_with(
                    'https://raw.githubusercontent.com/owner/repo/main/variables.tf',
                    timeout=3.0,
                )

                # Check that parse_variables_tf was called with the correct content
                mock_parse.assert_called_once_with(mock_response.text)

                # Check the result
                assert content == mock_response.text
                assert len(variables) == 2
                assert variables[0].name == 'region'
                assert variables[0].type == 'string'
                assert variables[0].description == 'AWS region'
                assert variables[0].default == 'us-west-2'
                assert variables[0].required is False
                assert variables[1].name == 'instance_type'
                assert variables[1].type == 'string'
                assert variables[1].description == 'EC2 instance type'
                assert variables[1].default is None
                assert variables[1].required is True

    @pytest.mark.asyncio
    async def test_get_variables_tf_with_no_variables_tf(self):
        """Test getting variables.tf with no variables.tf file."""
        # Mock the requests.get function
        with patch('requests.get') as mock_get:
            # Create mock responses
            mock_main_response = MagicMock()
            mock_main_response.status_code = 404  # No variables.tf found in main branch

            mock_master_response = MagicMock()
            mock_master_response.status_code = 404  # No variables.tf found in master branch

            # Configure the mock to return different responses for different URLs
            def side_effect(url, **kwargs):
                if 'main/variables.tf' in url:
                    return mock_main_response
                elif 'master/variables.tf' in url:
                    return mock_master_response
                return MagicMock(status_code=404)

            mock_get.side_effect = side_effect

            # Call the function
            content, variables = await get_variables_tf('owner', 'repo')

            # Check that requests.get was called with the correct URLs
            assert mock_get.call_count == 2
            mock_get.assert_any_call(
                'https://raw.githubusercontent.com/owner/repo/main/variables.tf',
                timeout=3.0,
            )
            mock_get.assert_any_call(
                'https://raw.githubusercontent.com/owner/repo/master/variables.tf',
                timeout=3.0,
            )

            # Check the result
            assert content is None
            assert variables is None

    @pytest.mark.asyncio
    async def test_get_variables_tf_with_master_branch_fallback(self):
        """Test getting variables.tf from the master branch as fallback."""
        # Mock the requests.get function
        with patch('requests.get') as mock_get:
            # Create mock responses
            mock_main_response = MagicMock()
            mock_main_response.status_code = 404  # No variables.tf found in main branch

            mock_master_response = MagicMock()
            mock_master_response.status_code = 200
            mock_master_response.text = """
variable "region" {
  type        = string
  description = "AWS region"
  default     = "us-west-2"
}
"""

            # Configure the mock to return different responses for different URLs
            def side_effect(url, **kwargs):
                if 'main/variables.tf' in url:
                    return mock_main_response
                elif 'master/variables.tf' in url:
                    return mock_master_response
                return MagicMock(status_code=404)

            mock_get.side_effect = side_effect

            # Mock the parse_variables_tf function
            with patch(
                'awslabs.terraform_mcp_server.impl.tools.utils.parse_variables_tf'
            ) as mock_parse:
                mock_var = TerraformVariable(
                    name='region',
                    type='string',
                    description='AWS region',
                    default='us-west-2',
                    required=False,
                )
                mock_parse.return_value = [mock_var]

                # Call the function
                content, variables = await get_variables_tf('owner', 'repo')

                # Check that requests.get was called with the correct URLs
                assert mock_get.call_count == 2
                mock_get.assert_any_call(
                    'https://raw.githubusercontent.com/owner/repo/main/variables.tf',
                    timeout=3.0,
                )
                mock_get.assert_any_call(
                    'https://raw.githubusercontent.com/owner/repo/master/variables.tf',
                    timeout=3.0,
                )

                # Check that parse_variables_tf was called with the correct content
                mock_parse.assert_called_once_with(mock_master_response.text)

                # Check the result
                assert content == mock_master_response.text
                assert len(variables) == 1
                assert variables[0].name == 'region'
                assert variables[0].type == 'string'
                assert variables[0].description == 'AWS region'
                assert variables[0].default == 'us-west-2'
                assert variables[0].required is False

    @pytest.mark.asyncio
    async def test_get_variables_tf_with_exception(self):
        """Test getting variables.tf with an exception."""
        # Mock the requests.get function to raise an exception
        with patch('requests.get', side_effect=Exception('Test exception')):
            # Call the function
            content, variables = await get_variables_tf('owner', 'repo')

            # Check the result
            assert content is None
            assert variables is None
