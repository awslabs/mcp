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

"""Unit tests for the LazyServer shim."""

import asyncio
import inspect
import pytest
from awslabs.mcp_common import Field, LazyServer
from awslabs.mcp_common.lazy_server import _FieldSpec


def test_field_returns_field_spec():
    """Field(...) should produce a _FieldSpec holding the kwargs."""
    spec = Field(description='hello', default=5, gt=0)
    assert isinstance(spec, _FieldSpec)
    assert spec.kwargs == {'description': 'hello', 'default': 5, 'gt': 0}


def test_tool_decorator_returns_function_unchanged():
    """@mcp.tool() must return the original function so authors can call it directly."""
    srv = LazyServer('x')

    @srv.tool()
    async def my_tool(ctx, x: int = Field(default=1)) -> int:
        return x

    assert inspect.iscoroutinefunction(my_tool)
    assert my_tool.__name__ == 'my_tool'
    assert asyncio.run(my_tool(ctx=None, x=7)) == 7


def test_accessing_mcp_before_run_raises():
    """LazyServer.<attr> before run()/build() raises RuntimeError for unknown names."""
    srv = LazyServer('x')
    with pytest.raises(RuntimeError, match='not initialized'):
        srv.nonexistent_attr


def test_build_registers_tool_and_resolves_field():
    """build() materializes a FastMCP server, registers tools, and resolves _FieldSpec defaults."""
    srv = LazyServer('x', instructions='hi', dependencies=['pydantic'])

    @srv.tool()
    async def greet(
        ctx,
        name: str = Field(description='who to greet'),
        times: int = Field(default=1, gt=0),
    ) -> str:
        return f'hello {name}' * times

    server = srv.build()
    tool = server._tool_manager._tools['greet']
    sig = inspect.signature(tool.fn)

    for pname, param in sig.parameters.items():
        assert not isinstance(param.default, _FieldSpec), (
            f'{pname} default was not resolved: {param.default!r}'
        )


def test_tool_description_defaults_to_docstring():
    """With no explicit description, the tool's description should come from the docstring."""
    srv = LazyServer('x')

    @srv.tool()
    async def greet(ctx) -> str:
        """Friendly greeting."""
        return 'hi'

    server = srv.build()
    assert server._tool_manager._tools['greet'].description == 'Friendly greeting.'


def test_tool_explicit_name_and_description_override():
    """Explicit name/description on @tool(...) should override defaults."""
    srv = LazyServer('x')

    @srv.tool(name='hello', description='override')
    async def greet_fn(ctx) -> str:
        """Docstring (ignored)."""
        return 'hi'

    server = srv.build()
    assert 'hello' in server._tool_manager._tools
    assert server._tool_manager._tools['hello'].description == 'override'


def test_delegation_after_build():
    """After build(), attribute access on the LazyServer delegates to FastMCP."""
    srv = LazyServer('x')
    srv.build()
    # FastMCP exposes a `name` attribute
    assert srv.name == 'x'


def test_ctx_is_recognized_by_fastmcp_as_context_kwarg():
    """Wrapper must expose `ctx: Context` in `__annotations__`, not only on `__signature__`.

    FastMCP's `find_context_parameter` uses `typing.get_type_hints`, which
    reads `__annotations__`. If the annotation is only on the signature,
    `context_kwarg` comes back as None — which leaks `ctx` into the tool's
    input schema as a required argument and disables runtime Context injection.
    """
    srv = LazyServer('x')

    @srv.tool()
    async def greet(ctx, name: str = Field(description='who to greet')) -> str:
        return f'hello {name}'

    server = srv.build()
    tool = server._tool_manager._tools['greet']

    assert tool.context_kwarg == 'ctx', (
        f'FastMCP did not recognize ctx as the context parameter; '
        f'context_kwarg={tool.context_kwarg!r}. The tool schema will require '
        f'ctx as an argument and Context injection at call time will fail.'
    )
    assert 'ctx' not in tool.parameters.get('required', []), (
        'ctx leaked into the tool input schema as a required argument'
    )
    assert 'ctx' not in tool.parameters.get('properties', {}), (
        'ctx leaked into the tool input schema as a property'
    )


def test_forward_ref_return_type_is_resolved():
    """String return annotations must be resolved against the outer module's globals.

    FastMCP reads the signature's `return_annotation` directly; an unresolved
    string produces PydanticUserError and disables the tool's output schema.
    """
    from pydantic import BaseModel

    class Payload(BaseModel):
        value: int

    srv = LazyServer('x')

    # Use a string annotation to simulate what happens with
    # `from __future__ import annotations` or TYPE_CHECKING-guarded imports.
    @srv.tool()
    async def make_payload(ctx) -> 'Payload':
        return Payload(value=1)

    # Put the name in the function's resolution scope (its __globals__).
    make_payload.__globals__['Payload'] = Payload

    server = srv.build()
    tool = server._tool_manager._tools['make_payload']

    sig = inspect.signature(tool.fn)
    assert sig.return_annotation is Payload, (
        f'return annotation was not resolved: {sig.return_annotation!r}'
    )
    assert tool.fn.__annotations__.get('return') is Payload
    assert tool.output_schema is not None, (
        'output schema was not generated for a forward-referenced return type'
    )
