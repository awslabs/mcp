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

"""Tests that MCP tool wrapper signatures stay in sync with outer function signatures.

The _create_mcp() factories in server_aws.py and server_aws_cn.py register thin
wrapper functions whose Field-annotated parameters must match the outer function
parameters (minus 'ctx'). This test catches drift between the two.
"""

import inspect

from awslabs.aws_documentation_mcp_server import server_aws, server_aws_cn


def _non_ctx_params(func) -> list[str]:
    """Return parameter names of *func*, excluding 'ctx' and 'self'."""
    sig = inspect.signature(func)
    return [
        name
        for name, p in sig.parameters.items()
        if name not in ('ctx', 'self')
    ]


def _wrapper_params(wrapper_func) -> list[str]:
    """Return parameter names of a wrapper, excluding 'ctx' and 'self'."""
    return _non_ctx_params(wrapper_func)


class TestServerAwsWrapperSync:
    """Verify server_aws.py wrapper signatures match outer functions."""

    def test_read_documentation_wrapper_params(self):
        """read_documentation_tool wrapper params must match read_documentation."""
        mcp = server_aws._create_mcp()
        # FastMCP stores tools in a dict keyed by tool name
        tool = mcp._tool_manager._tools['read_documentation']
        wrapper_fn = tool.fn
        outer_params = _non_ctx_params(server_aws.read_documentation)
        inner_params = _non_ctx_params(wrapper_fn)
        assert outer_params == inner_params, (
            f'Wrapper/outer param mismatch for read_documentation:\n'
            f'  outer: {outer_params}\n'
            f'  wrapper: {inner_params}'
        )

    def test_search_documentation_wrapper_params(self):
        """search_documentation_tool wrapper params must match search_documentation."""
        mcp = server_aws._create_mcp()
        tool = mcp._tool_manager._tools['search_documentation']
        wrapper_fn = tool.fn
        outer_params = _non_ctx_params(server_aws.search_documentation)
        inner_params = _non_ctx_params(wrapper_fn)
        assert outer_params == inner_params, (
            f'Wrapper/outer param mismatch for search_documentation:\n'
            f'  outer: {outer_params}\n'
            f'  wrapper: {inner_params}'
        )

    def test_recommend_wrapper_params(self):
        """recommend_tool wrapper params must match recommend."""
        mcp = server_aws._create_mcp()
        tool = mcp._tool_manager._tools['recommend']
        wrapper_fn = tool.fn
        outer_params = _non_ctx_params(server_aws.recommend)
        inner_params = _non_ctx_params(wrapper_fn)
        assert outer_params == inner_params, (
            f'Wrapper/outer param mismatch for recommend:\n'
            f'  outer: {outer_params}\n'
            f'  wrapper: {inner_params}'
        )


class TestServerAwsCnWrapperSync:
    """Verify server_aws_cn.py wrapper signatures match outer functions."""

    def test_read_documentation_wrapper_params(self):
        """read_documentation_tool wrapper params must match read_documentation."""
        mcp = server_aws_cn._create_mcp()
        tool = mcp._tool_manager._tools['read_documentation']
        wrapper_fn = tool.fn
        outer_params = _non_ctx_params(server_aws_cn.read_documentation)
        inner_params = _non_ctx_params(wrapper_fn)
        assert outer_params == inner_params, (
            f'Wrapper/outer param mismatch for read_documentation (CN):\n'
            f'  outer: {outer_params}\n'
            f'  wrapper: {inner_params}'
        )

    def test_get_available_services_wrapper_params(self):
        """get_available_services_tool wrapper params must match get_available_services."""
        mcp = server_aws_cn._create_mcp()
        tool = mcp._tool_manager._tools['get_available_services']
        wrapper_fn = tool.fn
        outer_params = _non_ctx_params(server_aws_cn.get_available_services)
        inner_params = _non_ctx_params(wrapper_fn)
        assert outer_params == inner_params, (
            f'Wrapper/outer param mismatch for get_available_services (CN):\n'
            f'  outer: {outer_params}\n'
            f'  wrapper: {inner_params}'
        )
