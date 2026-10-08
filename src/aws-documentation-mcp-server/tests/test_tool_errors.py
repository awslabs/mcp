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
"""Anticipated read-path failures must reach the client as ToolError.

The MCP SDK forwards a ``ToolError``'s message to the client and withholds the text of every
other exception, keeping crash details off the wire (python-sdk#3314). Each failure the read path
raises deliberately already builds a message for the caller, so the type it is raised as decides
whether that message arrives or is replaced by a bare "Error executing tool <name>".

These tests assert the type, which holds on any SDK version. Whether the message is then
forwarded is the SDK's behaviour and differs by release: 2.0.0 appends the text of any exception,
while 2.1.0 and later forward only a ToolError's.
"""

import httpx
import pytest
from awslabs.aws_documentation_mcp_server.server_aws import (
    read_documentation,
    read_sections,
    search_table,
)
from awslabs.aws_documentation_mcp_server.server_utils import (
    read_documentation_impl,
    read_sections_impl,
    search_table_impl,
)
from awslabs.aws_documentation_mcp_server.util import (
    DocumentationToolError,
    UnreadablePageError,
)
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from unittest.mock import AsyncMock, MagicMock, patch


def _ctx():
    ctx = MagicMock(spec=Context)
    ctx.error = AsyncMock()
    return ctx


def _response(
    *,
    status=200,
    text='<html><body><main><p>x</p></main></body></html>',
    ctype='text/html',
    url='https://docs.aws.amazon.com/t.html',
):
    response = MagicMock()
    response.status_code = status
    response.text = text
    response.headers = {'content-type': ctype}
    response.url = url
    return response


def _client_for(response=None, side_effect=None):
    """Patch httpx.AsyncClient so a fetch returns the response, or raises."""
    patcher = patch('httpx.AsyncClient')
    mock_class = patcher.start()
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.get = AsyncMock(return_value=response, side_effect=side_effect)
    mock_class.return_value = client
    return patcher


class TestExceptionHierarchy:
    """The type has to satisfy the SDK and the existing callers at the same time."""

    def test_documentation_tool_error_is_both(self):
        """ToolError so the message travels, ValueError so existing callers still catch it."""
        error = DocumentationToolError('message for the caller')
        assert isinstance(error, ToolError)
        assert isinstance(error, ValueError)
        assert str(error) == 'message for the caller'

    def test_unreadable_page_error_is_both(self):
        """It escapes to tool callers, so it needs the same treatment."""
        error = UnreadablePageError('nothing to convert')
        assert isinstance(error, ToolError)
        assert isinstance(error, ValueError)
        assert isinstance(error, DocumentationToolError)


class TestValidationFailures:
    """Rejections that happen before any fetch."""

    @pytest.mark.asyncio
    async def test_read_documentation_rejects_unsupported_domain(self):
        """A host outside the allowlist is rejected before any fetch."""
        with pytest.raises(ToolError, match='supported domains'):
            await read_documentation(
                _ctx(), url='https://example.com/t.html', max_length=1000, start_index=0
            )

    @pytest.mark.asyncio
    async def test_read_documentation_rejects_non_html(self):
        """A path that is not .html is rejected before any fetch."""
        with pytest.raises(ToolError, match='must end with .html'):
            await read_documentation(
                _ctx(), url='https://docs.aws.amazon.com/t.pdf', max_length=1000, start_index=0
            )

    @pytest.mark.asyncio
    async def test_read_sections_rejects_empty_section_titles(self):
        """An empty section_titles list cannot be served."""
        with pytest.raises(ToolError, match='section_titles parameter cannot be empty'):
            await read_sections(
                _ctx(), url='https://docs.aws.amazon.com/t.html', section_titles=[]
            )

    @pytest.mark.asyncio
    async def test_search_table_rejects_empty_query(self):
        """An empty query cannot be served."""
        with pytest.raises(ToolError, match='query parameter cannot be empty'):
            await search_table(
                _ctx(),
                url='https://docs.aws.amazon.com/t.html',
                query='',
                section_title=None,
                max_rows=10,
            )

    @pytest.mark.asyncio
    async def test_validation_failures_are_still_value_errors(self):
        """Backwards compatibility: these raised ValueError before and callers may rely on it."""
        with pytest.raises(ValueError, match='must end with .html'):
            await read_documentation(
                _ctx(), url='https://docs.aws.amazon.com/t.pdf', max_length=1000, start_index=0
            )


class TestFetchFailures:
    """Failures after the request goes out. These are the ones a moved page produces."""

    @pytest.mark.asyncio
    async def test_transport_failure(self):
        """The request never completed, so say so rather than failing bare."""
        patcher = _client_for(side_effect=httpx.ConnectError('connection refused'))
        try:
            with pytest.raises(ToolError, match='Failed to fetch'):
                await read_documentation_impl(
                    _ctx(), 'https://docs.aws.amazon.com/t.html', 1000, 0, 'uuid'
                )
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_http_error_status(self):
        """The origin answered 4xx or 5xx."""
        patcher = _client_for(_response(status=404))
        try:
            with pytest.raises(ToolError, match='status code 404'):
                await read_documentation_impl(
                    _ctx(), 'https://docs.aws.amazon.com/t.html', 1000, 0, 'uuid'
                )
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_unreadable_page_names_the_served_url(self):
        """A renamed guide page redirects to an index shell with nothing to convert.

        The server builds "Requested <A>; served <B>." for this case, which is the message the
        caller needs in order to retry, so it has to survive as a ToolError.
        """
        patcher = _client_for(
            _response(
                text='<html><body></body></html>',
                url='https://docs.aws.amazon.com/service-authorization/latest/reference/',
            )
        )
        try:
            with pytest.raises(ToolError, match='served ') as excinfo:
                await read_documentation_impl(
                    _ctx(),
                    'https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonbedrockagentcore.html',
                    1000,
                    0,
                    'uuid',
                )
        finally:
            patcher.stop()
        assert 'could not be read' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_read_sections_non_html_content(self):
        """Sections cannot be extracted from a non-HTML response."""
        patcher = _client_for(_response(text='plain text', ctype='text/plain'))
        try:
            with pytest.raises(ToolError, match='Cannot extract sections from non-HTML'):
                await read_sections_impl(
                    _ctx(), 'https://docs.aws.amazon.com/t.html', ['Overview'], 'uuid'
                )
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_read_sections_missing_section(self):
        """The page was readable but held none of the requested sections."""
        patcher = _client_for(
            _response(text='<html><body><h2>Other</h2><p>body</p></body></html>')
        )
        try:
            with pytest.raises(ToolError, match='No matching sections were found'):
                await read_sections_impl(
                    _ctx(), 'https://docs.aws.amazon.com/t.html', ['Overview'], 'uuid'
                )
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_search_table_non_html_content(self):
        """Tables cannot be parsed from a non-HTML response."""
        patcher = _client_for(_response(text='plain text', ctype='text/plain'))
        try:
            with pytest.raises(ToolError, match='not HTML'):
                await search_table_impl(
                    _ctx(), 'https://docs.aws.amazon.com/t.html', None, 'q', 10, 'uuid'
                )
        finally:
            patcher.stop()


class TestUnexpectedFailuresStayGeneric:
    """A crash is not an anticipated failure and its text must not be forwarded."""

    @pytest.mark.asyncio
    async def test_a_crash_is_not_converted_to_a_tool_error(self):
        """Converting these too would undo what python-sdk#3314 set out to do.

        read_sections_impl catches unexpected exceptions only to log them, then re-raises
        unchanged, so the SDK still replaces the text with a generic message.
        """
        patcher = _client_for(
            _response(text='<html><body><h2>Overview</h2><p>body</p></body></html>')
        )
        try:
            with patch(
                'awslabs.aws_documentation_mcp_server.server_utils.truncate_large_tables',
                side_effect=TypeError('internal detail that must not leak'),
            ):
                with pytest.raises(TypeError, match='internal detail'):
                    await read_sections_impl(
                        _ctx(), 'https://docs.aws.amazon.com/t.html', ['Overview'], 'uuid'
                    )
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_a_crash_is_not_a_documentation_tool_error(self):
        """Stated as its own assertion because it is the property that keeps crashes off the wire."""
        patcher = _client_for(
            _response(text='<html><body><h2>Overview</h2><p>body</p></body></html>')
        )
        try:
            with patch(
                'awslabs.aws_documentation_mcp_server.server_utils.truncate_large_tables',
                side_effect=TypeError('internal detail that must not leak'),
            ):
                with pytest.raises(Exception) as excinfo:
                    await read_sections_impl(
                        _ctx(), 'https://docs.aws.amazon.com/t.html', ['Overview'], 'uuid'
                    )
        finally:
            patcher.stop()
        assert not isinstance(excinfo.value, DocumentationToolError)
        assert not isinstance(excinfo.value, ToolError)
