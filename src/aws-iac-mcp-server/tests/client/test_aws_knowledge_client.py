import json
import pytest
from awslabs.aws_iac_mcp_server.client.aws_knowledge_client import (
    _parse_read_documentation_result,
    _parse_search_documentation_result,
    read_documentation,
    search_documentation,
)
from mcp.types import TextContent
from unittest.mock import AsyncMock, MagicMock, patch


class TestSearchDocumentation:
    """Test cases for the search_documentation function."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_iac_mcp_server.client.aws_knowledge_client.Client')
    async def test_successful_search(self, mock_client_class):
        """Test successful search returns parsed results.

        Verifies that when the MCP client returns valid JSON data,
        the function correctly parses and returns search results.
        """
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_result = MagicMock()
        mock_result.is_error = False
        mock_content = TextContent(
            type='text',
            text=json.dumps(
                {
                    'content': {
                        'result': [
                            {
                                'rank_order': 1,
                                'title': 'AWS Lambda',
                                'url': 'https://docs.aws.amazon.com/lambda/',
                                'context': 'Serverless compute service',
                            }
                        ]
                    }
                }
            ),
        )
        mock_result.content = [mock_content]
        mock_client.call_tool.return_value = mock_result

        result = await search_documentation('lambda', 'cdk', limit=5)

        mock_client_class.assert_called_once_with('https://knowledge-mcp.global.api.aws')
        mock_client.call_tool.assert_called_once_with(
            'aws___search_documentation',
            {'search_phrase': 'lambda', 'limit': 5, 'topics': ['cdk']},
        )
        assert len(result) == 1
        assert result[0].title == 'AWS Lambda'

    @pytest.mark.asyncio
    @patch('awslabs.aws_iac_mcp_server.client.aws_knowledge_client.Client')
    async def test_client_exception(self, mock_client_class):
        """Test client initialization failure is handled gracefully.

        Verifies that when the MCP client fails to initialize,
        the function raises the exception.
        """
        mock_client_class.side_effect = Exception('Connection failed')

        with pytest.raises(Exception, match='Connection failed'):
            await search_documentation('lambda', 'cdk')

    @pytest.mark.asyncio
    @patch('awslabs.aws_iac_mcp_server.client.aws_knowledge_client.Client')
    async def test_call_tool_exception(self, mock_client_class):
        """Test tool call failure is handled gracefully.

        Verifies that when the MCP client tool call fails,
        the function raises the exception.
        """
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.call_tool.side_effect = Exception('Tool call failed')

        with pytest.raises(Exception, match='Tool call failed'):
            await search_documentation('lambda', 'cdk')


class TestParseSearchResult:
    """Test cases for the _parse_search_documentation_result function."""

    def test_valid_result(self):
        """Test parsing of valid search results.

        Verifies that well-formed JSON responses with all required fields
        are correctly parsed into SearchResult objects.
        """
        mock_result = MagicMock()
        mock_result.is_error = False
        mock_content = TextContent(
            type='text',
            text=json.dumps(
                {
                    'content': {
                        'result': [
                            {
                                'rank_order': 1,
                                'title': 'AWS Lambda',
                                'url': 'https://docs.aws.amazon.com/lambda/',
                                'context': 'Serverless compute service',
                            },
                            {
                                'rank_order': 2,
                                'title': 'Lambda Functions',
                                'url': 'https://docs.aws.amazon.com/lambda/functions/',
                                'context': 'Function configuration',
                            },
                        ]
                    }
                }
            ),
        )
        mock_result.content = [mock_content]

        parsed = _parse_search_documentation_result(mock_result)

        assert len(parsed) == 2
        assert parsed[0].rank == 1
        assert parsed[0].title == 'AWS Lambda'
        assert parsed[1].rank == 2
        assert parsed[1].title == 'Lambda Functions'

    def test_empty_results(self):
        """Test parsing of empty search results.

        Verifies that valid JSON responses with empty result arrays
        are handled correctly without errors.
        """
        mock_result = MagicMock()
        mock_result.is_error = False
        mock_content = TextContent(type='text', text=json.dumps({'content': {'result': []}}))
        mock_result.content = [mock_content]

        parsed = _parse_search_documentation_result(mock_result)

        assert parsed == []

    def test_is_error_true(self):
        """Test handling of error responses from MCP client.

        Verifies that when the MCP client indicates an error occurred,
        the parser returns an appropriate error message.
        """
        mock_result = MagicMock()
        mock_result.is_error = True
        mock_result.content = 'Error occurred'

        with pytest.raises(Exception, match='Tool call returned an error'):
            _parse_search_documentation_result(mock_result)

    def test_empty_content(self):
        """Test handling of empty content arrays.

        Verifies that responses with empty content arrays
        are handled gracefully with appropriate error messages.
        """
        mock_result = MagicMock()
        mock_result.is_error = False
        mock_result.content = []

        with pytest.raises(Exception, match='Empty response from tool'):
            _parse_search_documentation_result(mock_result)

    def test_none_content(self):
        """Test handling of None content.

        Verifies that responses with None content
        are handled gracefully with appropriate error messages.
        """
        mock_result = MagicMock()
        mock_result.is_error = False
        mock_result.content = None

        with pytest.raises(Exception, match='Empty response from tool'):
            _parse_search_documentation_result(mock_result)

    def test_content_not_text_type(self):
        """Test handling of non-text content types.

        Verifies that responses containing non-TextContent objects
        are rejected with appropriate error messages.
        """
        mock_result = MagicMock()
        mock_result.is_error = False
        mock_content = MagicMock()
        mock_result.content = [mock_content]

        with pytest.raises(Exception, match='Content is not text type'):
            _parse_search_documentation_result(mock_result)

    def test_invalid_json(self):
        """Test handling of malformed JSON responses.

        Verifies that responses with invalid JSON syntax
        are handled gracefully with appropriate error messages.
        """
        mock_result = MagicMock()
        mock_result.is_error = False
        mock_content = TextContent(type='text', text='invalid json')
        mock_result.content = [mock_content]

        with pytest.raises(json.JSONDecodeError):
            _parse_search_documentation_result(mock_result)

    def test_missing_content_key(self):
        """Test handling of responses missing the 'content' key.

        Verifies that JSON responses without the expected 'content' key
        are rejected with appropriate error messages.
        """
        mock_result = MagicMock()
        mock_result.is_error = False
        mock_content = TextContent(type='text', text=json.dumps({}))
        mock_result.content = [mock_content]

        with pytest.raises(KeyError):
            _parse_search_documentation_result(mock_result)

    def test_missing_result_key(self):
        """Test handling of responses missing the 'result' key.

        Verifies that JSON responses without the expected 'result' key
        within the content object are rejected with appropriate error messages.
        """
        mock_result = MagicMock()
        mock_result.is_error = False
        mock_content = TextContent(type='text', text=json.dumps({'content': {}}))
        mock_result.content = [mock_content]

        with pytest.raises(KeyError):
            _parse_search_documentation_result(mock_result)

    def test_missing_required_field_in_item(self):
        """Test handling of search result items missing required fields.

        Verifies that search result items missing required fields like
        'url' or 'context' are rejected with appropriate error messages.
        """
        mock_result = MagicMock()
        mock_result.is_error = False
        mock_content = TextContent(
            type='text',
            text=json.dumps(
                {
                    'content': {
                        'result': [
                            {
                                'rank_order': 1,
                                'title': 'AWS Lambda',
                                # Missing url and context
                            }
                        ]
                    }
                }
            ),
        )
        mock_result.content = [mock_content]

        with pytest.raises(KeyError):
            _parse_search_documentation_result(mock_result)


class TestReadDocumentation:
    """Test cases for the read_documentation function."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_iac_mcp_server.client.aws_knowledge_client.Client')
    async def test_successful_read(self, mock_client_class):
        """Test successful read returns parsed content.

        Verifies that when the MCP client returns valid JSON data,
        the function correctly parses and returns documentation content.
        """
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_result = MagicMock()
        mock_result.is_error = False
        mock_content = TextContent(
            type='text',
            text=json.dumps({'content': {'result': 'This is the documentation content'}}),
        )
        mock_result.content = [mock_content]
        mock_client.call_tool.return_value = mock_result

        result = await read_documentation('https://docs.aws.amazon.com/lambda/', 100)

        mock_client_class.assert_called_once_with('https://knowledge-mcp.global.api.aws')
        mock_client.call_tool.assert_called_once_with(
            'aws___read_documentation',
            {'url': 'https://docs.aws.amazon.com/lambda/', 'start_index': 100},
        )
        assert len(result) == 1
        assert result[0].context == 'This is the documentation content'

    @pytest.mark.asyncio
    @patch('awslabs.aws_iac_mcp_server.client.aws_knowledge_client.Client')
    async def test_client_exception(self, mock_client_class):
        """Test client initialization failure is handled gracefully.

        Verifies that when the MCP client fails to initialize,
        the function raises the exception.
        """
        mock_client_class.side_effect = Exception('Connection failed')

        with pytest.raises(Exception, match='Connection failed'):
            await read_documentation('https://docs.aws.amazon.com/lambda/')

    @pytest.mark.asyncio
    @patch('awslabs.aws_iac_mcp_server.client.aws_knowledge_client.Client')
    async def test_call_tool_exception(self, mock_client_class):
        """Test tool call failure is handled gracefully.

        Verifies that when the MCP client tool call fails,
        the function raises the exception.
        """
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.call_tool.side_effect = Exception('Tool call failed')

        with pytest.raises(Exception, match='Tool call failed'):
            await read_documentation('https://docs.aws.amazon.com/lambda/')


class TestParseReadResult:
    """Test cases for the _parse_read_documentation_result function."""

    def test_valid_result(self):
        """Test parsing of valid read results.

        Verifies that well-formed JSON responses with documentation content
        are correctly parsed into KnowledgeResult objects.
        """
        mock_result = MagicMock()
        mock_result.is_error = False
        mock_content = TextContent(
            type='text',
            text=json.dumps({'content': {'result': 'This is the documentation content'}}),
        )
        mock_result.content = [mock_content]

        parsed = _parse_read_documentation_result(mock_result)

        assert len(parsed) == 1
        assert parsed[0].context == 'This is the documentation content'
        assert parsed[0].rank == 1

    def test_is_error_true(self):
        """Test handling of error responses from MCP client.

        Verifies that when the MCP client indicates an error occurred,
        the parser returns an appropriate error message.
        """
        mock_result = MagicMock()
        mock_result.is_error = True
        mock_result.content = 'Error occurred'

        with pytest.raises(Exception, match='Tool call returned an error'):
            _parse_read_documentation_result(mock_result)

    def test_empty_content(self):
        """Test handling of empty content arrays.

        Verifies that responses with empty content arrays
        are handled gracefully with appropriate error messages.
        """
        mock_result = MagicMock()
        mock_result.is_error = False
        mock_result.content = []

        with pytest.raises(Exception, match='Empty response from tool'):
            _parse_read_documentation_result(mock_result)

    def test_content_not_text_type(self):
        """Test handling of non-text content types.

        Verifies that responses containing non-TextContent objects
        are rejected with appropriate error messages.
        """
        mock_result = MagicMock()
        mock_result.is_error = False
        mock_content = MagicMock()
        mock_result.content = [mock_content]

        with pytest.raises(Exception, match='Content is not text type'):
            _parse_read_documentation_result(mock_result)

    def test_invalid_json(self):
        """Test handling of malformed JSON responses.

        Verifies that responses with invalid JSON syntax
        are handled gracefully with appropriate error messages.
        """
        mock_result = MagicMock()
        mock_result.is_error = False
        mock_content = TextContent(type='text', text='invalid json')
        mock_result.content = [mock_content]

        with pytest.raises(json.JSONDecodeError):
            _parse_read_documentation_result(mock_result)

    def test_missing_content_key(self):
        """Test handling of responses missing the 'content' key.

        Verifies that JSON responses without the expected 'content' key
        are rejected with appropriate error messages.
        """
        mock_result = MagicMock()
        mock_result.is_error = False
        mock_content = TextContent(type='text', text=json.dumps({}))
        mock_result.content = [mock_content]

        with pytest.raises(KeyError):
            _parse_read_documentation_result(mock_result)
