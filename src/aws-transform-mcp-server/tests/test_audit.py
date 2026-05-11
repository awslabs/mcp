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

"""Tests for audit module: _safe_args, audited_tool wrapper, _extract_error."""
# ruff: noqa: D101, D102, D103

import json
import pytest
from unittest.mock import MagicMock, patch


_MOD = 'awslabs.aws_transform_mcp_server.audit'


class TestSafeArgs:
    """Tests for _safe_args: sensitive-parameter redaction."""

    def test_filters_sensitive_params(self):
        from awslabs.aws_transform_mcp_server.audit import _safe_args

        def my_func(workspaceId, token, content, jobId):
            pass

        result = _safe_args(
            my_func,
            (),
            {'workspaceId': 'ws-1', 'token': 'secret', 'content': 'data', 'jobId': 'j-1'},
        )
        assert result == {'workspaceId': 'ws-1', 'jobId': 'j-1'}

    def test_filters_self_and_ctx(self):
        from awslabs.aws_transform_mcp_server.audit import _safe_args

        def my_func(self, ctx, workspaceId):
            pass

        result = _safe_args(my_func, ('self-val', 'ctx-val'), {'workspaceId': 'ws-1'})
        assert result == {'workspaceId': 'ws-1'}

    def test_filters_none_values(self):
        from awslabs.aws_transform_mcp_server.audit import _safe_args

        def my_func(workspaceId, description=None):
            pass

        result = _safe_args(my_func, (), {'workspaceId': 'ws-1'})
        assert result == {'workspaceId': 'ws-1'}
        assert 'description' not in result

    def test_positional_args(self):
        from awslabs.aws_transform_mcp_server.audit import _safe_args

        def my_func(workspaceId, jobId):
            pass

        result = _safe_args(my_func, ('ws-1', 'j-1'), {})
        assert result == {'workspaceId': 'ws-1', 'jobId': 'j-1'}


class TestExtractError:
    """Tests for _extract_error: best-effort error text extraction."""

    def test_extracts_code_and_message(self):
        from awslabs.aws_transform_mcp_server.audit import _extract_error

        result = {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps(
                        {
                            'error': {'code': 'NOT_FOUND', 'message': 'Job not found'},
                        }
                    ),
                }
            ]
        }
        text = _extract_error(result)
        assert 'NOT_FOUND' in text
        assert 'Job not found' in text

    def test_extracts_suggested_action(self):
        from awslabs.aws_transform_mcp_server.audit import _extract_error

        result = {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps(
                        {
                            'error': {
                                'code': 'NOT_CONFIGURED',
                                'message': 'Not configured',
                                'suggestedAction': 'Call configure first',
                            },
                        }
                    ),
                }
            ]
        }
        text = _extract_error(result)
        assert 'Call configure first' in text

    def test_malformed_result_returns_fallback(self):
        from awslabs.aws_transform_mcp_server.audit import _extract_error

        text = _extract_error({'content': []})
        assert text == '(could not extract error)'

    def test_non_json_text_returns_fallback(self):
        from awslabs.aws_transform_mcp_server.audit import _extract_error

        result = {'content': [{'type': 'text', 'text': 'not json'}]}
        text = _extract_error(result)
        assert text == '(could not extract error)'


class TestAuditedTool:
    """Tests for audited_tool decorator wrapper."""

    async def test_logs_invocation_and_returns_result(self):
        from awslabs.aws_transform_mcp_server.audit import audited_tool

        mcp = MagicMock()
        mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)

        async def my_tool(workspaceId):
            return {'content': [{'type': 'text', 'text': '{}'}], 'isError': False}

        with patch(f'{_MOD}.logger') as mock_logger:
            wrapped = audited_tool(mcp, 'test_tool')(my_tool)
            result = await wrapped(workspaceId='ws-1')

        assert result['isError'] is False
        mock_logger.info.assert_called_once()

    async def test_logs_error_response(self):
        from awslabs.aws_transform_mcp_server.audit import audited_tool

        mcp = MagicMock()
        mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)

        error_payload = json.dumps(
            {
                'error': {'code': 'BAD_REQUEST', 'message': 'Invalid input'},
            }
        )

        async def my_tool(workspaceId):
            return {
                'content': [{'type': 'text', 'text': error_payload}],
                'isError': True,
            }

        with patch(f'{_MOD}.logger') as mock_logger:
            wrapped = audited_tool(mcp, 'test_tool')(my_tool)
            result = await wrapped(workspaceId='ws-1')

        assert result['isError'] is True
        mock_logger.info.assert_called_once()
        mock_logger.warning.assert_called_once()

    async def test_logs_exception_and_reraises(self):
        from awslabs.aws_transform_mcp_server.audit import audited_tool

        mcp = MagicMock()
        mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)

        async def my_tool(workspaceId):
            raise RuntimeError('boom')

        with patch(f'{_MOD}.logger') as mock_logger:
            wrapped = audited_tool(mcp, 'test_tool')(my_tool)
            with pytest.raises(RuntimeError, match='boom'):
                await wrapped(workspaceId='ws-1')

        mock_logger.info.assert_called_once()
        mock_logger.opt.assert_called_once()

    async def test_audit_args_failure_still_executes(self):
        from awslabs.aws_transform_mcp_server.audit import audited_tool

        mcp = MagicMock()
        mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)

        async def my_tool(*args, **kwargs):
            return {'content': [{'type': 'text', 'text': '{}'}], 'isError': False}

        with (
            patch(f'{_MOD}._safe_args', side_effect=Exception('bind failed')),
            patch(f'{_MOD}.logger') as mock_logger,
        ):
            wrapped = audited_tool(mcp, 'test_tool')(my_tool)
            result = await wrapped(workspaceId='ws-1')

        assert result['isError'] is False
        mock_logger.warning.assert_called_once()
