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

"""Tests that LazyServer produces FastMCP tools with the expected schema.

The shim is responsible for turning `_FieldSpec` placeholders in tool
signatures into real `pydantic.Field(...)` defaults, and for auto-annotating
the `ctx` parameter with `Context`. These tests guard that contract.
"""

import inspect
import pytest
from awslabs.aws_documentation_mcp_server import server_aws, server_aws_cn
from awslabs.mcp_common.lazy_server import _FieldSpec


SERVER_AWS_TOOLS = ['read_documentation', 'read_sections', 'search_documentation', 'recommend']
SERVER_AWS_CN_TOOLS = ['read_documentation', 'get_available_services']


def _non_ctx_params(func) -> list[str]:
    return [p for p in inspect.signature(func).parameters if p not in ('ctx', 'self')]


@pytest.mark.parametrize('tool_name', SERVER_AWS_TOOLS)
def test_server_aws_tool_registered(tool_name):
    """Each expected tool is registered on the built FastMCP server."""
    server = server_aws.mcp.build()
    assert tool_name in server._tool_manager._tools, (
        f'{tool_name} not registered; available: {list(server._tool_manager._tools)}'
    )


@pytest.mark.parametrize('tool_name', SERVER_AWS_CN_TOOLS)
def test_server_aws_cn_tool_registered(tool_name):
    """Each expected tool is registered on the built FastMCP CN server."""
    server = server_aws_cn.mcp.build()
    assert tool_name in server._tool_manager._tools, (
        f'{tool_name} not registered; available: {list(server._tool_manager._tools)}'
    )


@pytest.mark.parametrize('tool_name', SERVER_AWS_TOOLS)
def test_server_aws_field_defaults_resolved(tool_name):
    """After build(), no parameter default is still a `_FieldSpec` placeholder."""
    server = server_aws.mcp.build()
    wrapper = server._tool_manager._tools[tool_name].fn
    sig = inspect.signature(wrapper)
    for name, param in sig.parameters.items():
        assert not isinstance(param.default, _FieldSpec), (
            f'{tool_name}.{name} still has an unresolved _FieldSpec default'
        )


@pytest.mark.parametrize('tool_name', SERVER_AWS_TOOLS)
def test_server_aws_ctx_is_annotated(tool_name):
    """The `ctx` parameter must carry a real Context annotation after build()."""
    from mcp.server.fastmcp import Context

    server = server_aws.mcp.build()
    wrapper = server._tool_manager._tools[tool_name].fn
    sig = inspect.signature(wrapper)
    assert sig.parameters['ctx'].annotation is Context


@pytest.mark.parametrize('tool_name', SERVER_AWS_TOOLS)
def test_server_aws_wrapper_params_match_outer(tool_name):
    """Wrapper's non-ctx params match the outer function's non-ctx params."""
    server = server_aws.mcp.build()
    wrapper = server._tool_manager._tools[tool_name].fn
    outer = getattr(server_aws, tool_name)
    assert _non_ctx_params(wrapper) == _non_ctx_params(outer)


@pytest.mark.parametrize('tool_name', SERVER_AWS_CN_TOOLS)
def test_server_aws_cn_wrapper_params_match_outer(tool_name):
    """Wrapper's non-ctx params match the outer function's non-ctx params (CN)."""
    server = server_aws_cn.mcp.build()
    wrapper = server._tool_manager._tools[tool_name].fn
    outer = getattr(server_aws_cn, tool_name)
    assert _non_ctx_params(wrapper) == _non_ctx_params(outer)
