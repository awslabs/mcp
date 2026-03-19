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
"""Comprehensive edge case tests for URL validation and Kiro support."""

import pytest
from awslabs.aws_documentation_mcp_server.server_aws import read_documentation
from unittest.mock import AsyncMock, MagicMock, patch


class MockContext:
    """Mock context for testing."""

    async def error(self, message):
        """Mock error method."""
        print(f'Error: {message}')


class TestURLValidationEdgeCases:
    """Test URL validation edge cases after regex fixes."""

    @pytest.mark.asyncio
    async def test_aws_url_with_html_extension_valid(self):
        """AWS URLs ending with .html should be VALID."""
        ctx = MockContext()
        url = 'https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html'
        
        # This should pass validation
        with patch('awslabs.aws_documentation_mcp_server.server_aws.read_documentation_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = "# S3 Bucket Naming Rules"
            result = await read_documentation(ctx, url=url, max_length=5000, start_index=0)
            assert result is not None
            mock_impl.assert_called_once()

    @pytest.mark.asyncio
    async def test_aws_url_without_html_extension_invalid(self):
        """AWS URLs NOT ending with .html should be INVALID."""
        ctx = MockContext()
        url = 'https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules/'
        
        # This should fail validation
        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await read_documentation(ctx, url=url, max_length=5000, start_index=0)

    @pytest.mark.asyncio
    async def test_aws_url_with_pdf_extension_invalid(self):
        """AWS URLs with .pdf should be INVALID."""
        ctx = MockContext()
        url = 'https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.pdf'
        
        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await read_documentation(ctx, url=url, max_length=5000, start_index=0)

    @pytest.mark.asyncio
    async def test_aws_url_with_txt_extension_invalid(self):
        """AWS URLs with .txt should be INVALID."""
        ctx = MockContext()
        url = 'https://docs.aws.amazon.com/lambda/latest/dg/index.txt'
        
        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await read_documentation(ctx, url=url, max_length=5000, start_index=0)

    @pytest.mark.asyncio
    async def test_kiro_url_with_trailing_slash_valid(self):
        """Kiro URLs with trailing slash should be VALID."""
        ctx = MockContext()
        url = 'https://kiro.dev/docs/cli/custom-agents/creating/'
        
        # This should pass validation (regex fix allows trailing slash)
        with patch('awslabs.aws_documentation_mcp_server.server_aws.read_documentation_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = "# Custom Agents"
            result = await read_documentation(ctx, url=url, max_length=5000, start_index=0)
            assert result is not None
            mock_impl.assert_called_once()

    @pytest.mark.asyncio
    async def test_kiro_url_without_trailing_slash_valid(self):
        """Kiro URLs without trailing slash should also be VALID."""
        ctx = MockContext()
        url = 'https://kiro.dev/docs/cli/custom-agents/creating'
        
        with patch('awslabs.aws_documentation_mcp_server.server_aws.read_documentation_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = "# Custom Agents"
            result = await read_documentation(ctx, url=url, max_length=5000, start_index=0)
            assert result is not None
            mock_impl.assert_called_once()

    @pytest.mark.asyncio
    async def test_kiro_url_nested_path_valid(self):
        """Kiro URLs with deeply nested paths should be VALID."""
        ctx = MockContext()
        url = 'https://kiro.dev/docs/cli/mcp/configuration/advanced/custom-integration/'
        
        with patch('awslabs.aws_documentation_mcp_server.server_aws.read_documentation_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = "# Advanced MCP Configuration"
            result = await read_documentation(ctx, url=url, max_length=5000, start_index=0)
            assert result is not None

    @pytest.mark.asyncio
    async def test_kiro_url_with_html_file_valid(self):
        """Kiro URLs with .html file (if they exist) should still be VALID."""
        ctx = MockContext()
        url = 'https://kiro.dev/docs/cli/custom-agents/creating/index.html'
        
        # Kiro regex allows any path, including .html files
        with patch('awslabs.aws_documentation_mcp_server.server_aws.read_documentation_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = "# Custom Agents"
            result = await read_documentation(ctx, url=url, max_length=5000, start_index=0)
            assert result is not None

    @pytest.mark.asyncio
    async def test_kiro_url_wrong_domain_invalid(self):
        """Non-kiro.dev URLs should be INVALID."""
        ctx = MockContext()
        url = 'https://kiro-docs.dev/docs/cli/custom-agents/creating/'
        
        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await read_documentation(ctx, url=url, max_length=5000, start_index=0)

    @pytest.mark.asyncio
    async def test_kiro_url_missing_docs_path_invalid(self):
        """Kiro URLs without /docs/ path should be INVALID."""
        ctx = MockContext()
        url = 'https://kiro.dev/cli/custom-agents/creating/'
        
        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await read_documentation(ctx, url=url, max_length=5000, start_index=0)

    @pytest.mark.asyncio
    async def test_kiro_url_root_only_invalid(self):
        """Kiro root URL without /docs/ should be INVALID."""
        ctx = MockContext()
        url = 'https://kiro.dev/'
        
        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await read_documentation(ctx, url=url, max_length=5000, start_index=0)

    @pytest.mark.asyncio
    async def test_neuron_url_with_html_extension_valid(self):
        """Neuron SDK URLs with .html should be VALID."""
        ctx = MockContext()
        url = 'https://awsdocs-neuron.readthedocs-hosted.com/en/latest/frameworks/index.html'
        
        with patch('awslabs.aws_documentation_mcp_server.server_aws.read_documentation_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = "# Neuron SDK"
            result = await read_documentation(ctx, url=url, max_length=5000, start_index=0)
            assert result is not None

    @pytest.mark.asyncio
    async def test_neuron_url_without_html_extension_invalid(self):
        """Neuron SDK URLs without .html should be INVALID."""
        ctx = MockContext()
        url = 'https://awsdocs-neuron.readthedocs-hosted.com/en/latest/frameworks/index'
        
        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await read_documentation(ctx, url=url, max_length=5000, start_index=0)

    @pytest.mark.asyncio
    async def test_http_aws_url_valid(self):
        """HTTP (non-HTTPS) AWS URLs should be VALID due to regex allowing http?."""
        ctx = MockContext()
        url = 'http://docs.aws.amazon.com/s3/latest/userguide/index.html'
        
        with patch('awslabs.aws_documentation_mcp_server.server_aws.read_documentation_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = "# S3"
            result = await read_documentation(ctx, url=url, max_length=5000, start_index=0)
            assert result is not None

    @pytest.mark.asyncio
    async def test_http_kiro_url_valid(self):
        """HTTP (non-HTTPS) Kiro URLs should be VALID due to regex allowing http?."""
        ctx = MockContext()
        url = 'http://kiro.dev/docs/cli/mcp/'
        
        with patch('awslabs.aws_documentation_mcp_server.server_aws.read_documentation_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = "# Kiro MCP"
            result = await read_documentation(ctx, url=url, max_length=5000, start_index=0)
            assert result is not None

    @pytest.mark.asyncio
    async def test_url_with_query_parameters_aws_invalid(self):
        """AWS URLs with query parameters should be INVALID (no .html before query)."""
        ctx = MockContext()
        url = 'https://docs.aws.amazon.com/s3/latest/userguide/index?version=latest'
        
        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await read_documentation(ctx, url=url, max_length=5000, start_index=0)

    @pytest.mark.asyncio
    async def test_url_with_query_parameters_aws_valid(self):
        """AWS URLs with .html followed by query parameters should be INVALID (regex doesn't allow this)."""
        ctx = MockContext()
        url = 'https://docs.aws.amazon.com/s3/latest/userguide/index.html?version=latest'
        
        # The regex `.*\.html$` requires the URL to END with .html, so query params fail
        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await read_documentation(ctx, url=url, max_length=5000, start_index=0)

    @pytest.mark.asyncio
    async def test_url_with_fragment_aws_invalid(self):
        """AWS URLs with fragments should be INVALID."""
        ctx = MockContext()
        url = 'https://docs.aws.amazon.com/s3/latest/userguide/index.html#section'
        
        # Fragment doesn't match `.*\.html$`
        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await read_documentation(ctx, url=url, max_length=5000, start_index=0)

    @pytest.mark.asyncio
    async def test_url_with_query_parameters_kiro_valid(self):
        """Kiro URLs with query parameters should be VALID (regex is permissive)."""
        ctx = MockContext()
        url = 'https://kiro.dev/docs/cli/mcp/?version=latest'
        
        # Kiro regex `.*$` allows anything including query params
        with patch('awslabs.aws_documentation_mcp_server.server_aws.read_documentation_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = "# Kiro"
            result = await read_documentation(ctx, url=url, max_length=5000, start_index=0)
            assert result is not None

    @pytest.mark.asyncio
    async def test_url_with_fragment_kiro_valid(self):
        """Kiro URLs with fragments should be VALID (regex is permissive)."""
        ctx = MockContext()
        url = 'https://kiro.dev/docs/cli/mcp/#section'
        
        with patch('awslabs.aws_documentation_mcp_server.server_aws.read_documentation_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = "# Kiro"
            result = await read_documentation(ctx, url=url, max_length=5000, start_index=0)
            assert result is not None

    @pytest.mark.asyncio
    async def test_url_uppercase_domain_invalid(self):
        """Uppercase domain names should be INVALID (regex is case-sensitive)."""
        ctx = MockContext()
        url = 'https://DOCS.AWS.AMAZON.COM/s3/latest/userguide/index.html'
        
        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await read_documentation(ctx, url=url, max_length=5000, start_index=0)

    @pytest.mark.asyncio
    async def test_url_mixed_case_domain_invalid(self):
        """Mixed case domain names should be INVALID."""
        ctx = MockContext()
        url = 'https://Docs.Aws.Amazon.Com/s3/latest/userguide/index.html'
        
        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await read_documentation(ctx, url=url, max_length=5000, start_index=0)

    @pytest.mark.asyncio
    async def test_empty_url_invalid(self):
        """Empty URLs should be INVALID."""
        ctx = MockContext()
        url = ''
        
        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await read_documentation(ctx, url=url, max_length=5000, start_index=0)

    @pytest.mark.asyncio
    async def test_none_url_invalid(self):
        """None URLs should raise an error."""
        ctx = MockContext()
        url = None
        
        with pytest.raises((ValueError, AttributeError, TypeError)):
            await read_documentation(ctx, url=url, max_length=5000, start_index=0)

    @pytest.mark.asyncio
    async def test_url_with_port_aws_invalid(self):
        """AWS URLs with port numbers should be INVALID."""
        ctx = MockContext()
        url = 'https://docs.aws.amazon.com:443/s3/latest/userguide/index.html'
        
        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await read_documentation(ctx, url=url, max_length=5000, start_index=0)

    @pytest.mark.asyncio
    async def test_url_with_port_kiro_valid(self):
        """Kiro URLs with port numbers should be VALID (permissive regex)."""
        ctx = MockContext()
        url = 'https://kiro.dev:8080/docs/cli/mcp/'
        
        # Kiro regex allows it
        with patch('awslabs.aws_documentation_mcp_server.server_aws.read_documentation_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = "# Kiro"
            result = await read_documentation(ctx, url=url, max_length=5000, start_index=0)
            assert result is not None

    @pytest.mark.asyncio
    async def test_relative_url_invalid(self):
        """Relative URLs should be INVALID."""
        ctx = MockContext()
        url = '/docs/cli/custom-agents/creating/'
        
        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await read_documentation(ctx, url=url, max_length=5000, start_index=0)

    @pytest.mark.asyncio
    async def test_url_with_special_characters_kiro_valid(self):
        """Kiro URLs with URL-encoded special characters should be VALID."""
        ctx = MockContext()
        url = 'https://kiro.dev/docs/cli/custom-agents/with%20spaces/'
        
        with patch('awslabs.aws_documentation_mcp_server.server_aws.read_documentation_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = "# Custom Agents"
            result = await read_documentation(ctx, url=url, max_length=5000, start_index=0)
            assert result is not None


class TestDocstringAccuracy:
    """Test that docstrings match actual implementation."""

    def test_read_documentation_docstring_mentions_supported_domains(self):
        """Docstring should list all 3 supported domains."""
        docstring = read_documentation.__doc__
        assert 'docs.aws.amazon.com' in docstring.lower()
        assert 'kiro.dev' in docstring.lower()
        assert 'awsdocs-neuron' in docstring.lower()

    def test_read_documentation_docstring_mentions_url_requirements(self):
        """Docstring should explain URL requirements for each domain."""
        docstring = read_documentation.__doc__
        assert 'html' in docstring.lower()
        assert 'kiro' in docstring.lower()

    def test_read_documentation_docstring_has_example_urls(self):
        """Docstring should have example URLs for each domain."""
        docstring = read_documentation.__doc__
        # Check for examples
        assert 'https://' in docstring
        assert 'docs.aws.amazon.com' in docstring
        assert 'kiro.dev' in docstring

    def test_read_documentation_docstring_no_contradictions(self):
        """Docstring should NOT say 'works with any URL'."""
        docstring = read_documentation.__doc__
        # Should not have contradictory claims
        assert 'any publicly accessible URL' not in docstring.lower()


class TestTestStructure:
    """Verify test file structure and discoverability."""

    def test_kiro_test_is_inside_class(self):
        """Test for kiro.dev should be inside TestReadDocumentation class."""
        from . import test_server_aws
        
        # Verify the method exists in the class
        assert hasattr(test_server_aws.TestReadDocumentation, 'test_read_documentation_works_for_kiro_url')

    def test_docstring_test_is_inside_class(self):
        """Test for docstring should be inside TestSearchDocumentation class."""
        from . import test_server_aws
        
        # Verify the method exists in the class
        assert hasattr(test_server_aws.TestSearchDocumentation, 'test_search_documentation_docstring_mentions_kiro')

    def test_no_module_level_test_functions(self):
        """Verify no orphan test functions exist at module level."""
        import ast
        import inspect
        
        from . import test_server_aws
        
        source = inspect.getsource(test_server_aws)
        tree = ast.parse(source)
        
        module_level_tests = [
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')
        ]

        # These tests should be methods on classes, not module-level functions.
        assert 'test_read_documentation_works_for_kiro_url' not in module_level_tests
        assert 'test_search_documentation_docstring_mentions_kiro' not in module_level_tests


class TestRegexPatternAccuracy:
    """Test the actual regex patterns used in validation."""

    def test_aws_regex_matches_html_urls(self):
        """AWS regex should match .html URLs."""
        import re
        pattern = r'^https?://docs\.aws\.amazon\.com/.*\.html$'
        
        assert re.match(pattern, 'https://docs.aws.amazon.com/s3/index.html')
        assert re.match(pattern, 'http://docs.aws.amazon.com/s3/index.html')
        assert not re.match(pattern, 'https://docs.aws.amazon.com/s3/index/')
        assert not re.match(pattern, 'https://docs.aws.amazon.com/s3/index.pdf')

    def test_kiro_regex_matches_any_path(self):
        """Kiro regex should match any path under /docs/."""
        import re
        pattern = r'^https?://kiro\.dev(:\d+)?/docs/.*$'
        
        assert re.match(pattern, 'https://kiro.dev/docs/cli/')
        assert re.match(pattern, 'https://kiro.dev/docs/cli/custom-agents/creating/')
        assert re.match(pattern, 'https://kiro.dev/docs/cli/mcp/index.html')
        assert re.match(pattern, 'https://kiro.dev/docs/')
        assert re.match(pattern, 'https://kiro.dev:8080/docs/cli/mcp/')
        assert not re.match(pattern, 'https://kiro.dev/cli/')
        assert not re.match(pattern, 'https://kiro-docs.dev/docs/cli/')

    def test_neuron_regex_matches_html_urls(self):
        """Neuron regex should match .html URLs."""
        import re
        pattern = r'^https?://awsdocs-neuron\.readthedocs-hosted\.com/.*\.html$'
        
        assert re.match(pattern, 'https://awsdocs-neuron.readthedocs-hosted.com/index.html')
        assert re.match(pattern, 'https://awsdocs-neuron.readthedocs-hosted.com/en/latest/guide.html')
        assert not re.match(pattern, 'https://awsdocs-neuron.readthedocs-hosted.com/en/latest/')
        assert not re.match(pattern, 'https://awsdocs-other.readthedocs-hosted.com/index.html')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
