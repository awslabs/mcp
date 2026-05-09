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

"""LazyServer: a FastMCP wrapper that defers heavy imports until run().

Consolidates the init-time optimization pattern so each AWS Labs MCP server
avoids paying for `mcp.server.fastmcp`, `pydantic`, and `FastMCP` construction
at module load.

Authors register tools at module level with no FastMCP/pydantic imports:

    from awslabs.mcp_common import Field, LazyServer

    mcp = LazyServer('my-server', instructions='...', dependencies=[...])

    @mcp.tool()
    async def my_tool(
        ctx,
        url: str = Field(description='...'),
        max_length: int = Field(default=5000, gt=0, lt=1_000_000),
    ) -> str:
        import httpx  # deferred here by the author
        ...

    def main():
        mcp.run()

At `run()` time the shim imports FastMCP, builds a wrapper with `ctx: Context`
and real `pydantic.Field(...)` defaults substituted in, registers each tool,
and delegates to `FastMCP.run`.
"""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, Optional


__all__ = ['Field', 'LazyServer']


class _FieldSpec:
    """Captured kwargs for a pydantic Field, resolved at run() time."""

    __slots__ = ('kwargs',)

    def __init__(self, kwargs: dict) -> None:
        self.kwargs = kwargs


def Field(**kwargs: Any) -> Any:
    """Lazy stand-in for `pydantic.Field` used in tool signatures.

    Returns a sentinel that LazyServer resolves to a real `pydantic.Field(...)`
    at `run()` time. No pydantic import at module load.

    Return type is `Any` so authors can use this as a parameter default without
    type-checker noise.
    """
    return _FieldSpec(kwargs)


class _RegisteredTool:
    """A tool function captured at module load, replayed at run time."""

    __slots__ = ('func', 'name', 'description')

    def __init__(
        self,
        func: Callable,
        name: Optional[str],
        description: Optional[str],
    ) -> None:
        self.func = func
        self.name = name or func.__name__
        self.description = description or (func.__doc__ or '').strip() or None


class LazyServer:
    """Defers FastMCP construction and heavy imports until `run()`.

    Parameters mirror FastMCP's kwargs that are commonly used at server
    construction; additional kwargs are forwarded verbatim to `FastMCP(...)`.
    """

    def __init__(
        self,
        name: str,
        instructions: Optional[str] = None,
        dependencies: Optional[list[str]] = None,
        **fastmcp_kwargs: Any,
    ) -> None:
        """Capture FastMCP construction args; construction is deferred to run()."""
        self._name = name
        self._instructions = instructions
        self._dependencies = dependencies
        self._fastmcp_kwargs = fastmcp_kwargs
        self._tools: list[_RegisteredTool] = []
        self._server: Any = None  # set in _materialize()

    def tool(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Callable[[Callable], Callable]:
        """Register a function as an MCP tool. Returns the function unchanged.

        The shim records `(func, name, description)` now and builds the real
        FastMCP tool wrapper inside `run()`.
        """

        def decorator(func: Callable) -> Callable:
            self._tools.append(_RegisteredTool(func, name, description))
            return func

        return decorator

    def _materialize(self) -> Any:
        """Import FastMCP, build wrappers for every registered tool, return the server."""
        from mcp.server.fastmcp import Context, FastMCP
        from pydantic import Field as RealField

        kwargs = dict(self._fastmcp_kwargs)
        if self._instructions is not None:
            kwargs['instructions'] = self._instructions
        if self._dependencies is not None:
            kwargs['dependencies'] = self._dependencies

        server = FastMCP(self._name, **kwargs)

        for tool in self._tools:
            wrapper = _build_wrapper(tool.func, Context, RealField)
            server.tool(name=tool.name, description=tool.description)(wrapper)

        self._server = server
        return server

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Materialize the real FastMCP server and delegate `run`."""
        server = self._materialize()
        return server.run(*args, **kwargs)

    def build(self) -> Any:
        """Materialize and return the underlying FastMCP server.

        Exposed primarily for tests. Calling `build()` is idempotent — subsequent
        calls return a fresh server rebuilt from the registered tools.
        """
        return self._materialize()

    def __getattr__(self, name: str) -> Any:
        """Delegate to the materialized FastMCP server, or raise if uninitialized."""
        server = self.__dict__.get('_server')
        if server is not None:
            return getattr(server, name)
        raise RuntimeError(
            f'MCP server not initialized. Call mcp.run() or mcp.build() before accessing {name!r}.'
        )


def _build_wrapper(func: Callable, Context: type, RealField: Callable) -> Callable:
    """Construct a FastMCP-compatible wrapper for *func*.

    The wrapper:
    - Auto-annotates a `ctx` parameter with the real `Context` class (so authors
      don't import `mcp.server.fastmcp.Context` at module level).
    - Replaces `_FieldSpec` defaults with real `pydantic.Field(...)` defaults.
    - Preserves docstring and name via `functools.wraps`.
    - Exposes the transformed signature via `__signature__` so FastMCP's schema
      builder reads the right metadata.
    """
    sig = inspect.signature(func)
    new_params: list[inspect.Parameter] = []
    for name, param in sig.parameters.items():
        annotation = param.annotation
        default = param.default

        if name == 'ctx' and annotation is inspect.Parameter.empty:
            annotation = Context

        if isinstance(default, _FieldSpec):
            default = RealField(**default.kwargs)

        new_params.append(param.replace(annotation=annotation, default=default))

    new_sig = sig.replace(parameters=new_params)

    wrapper: Callable
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        wrapper = async_wrapper
    else:

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        wrapper = sync_wrapper

    wrapper.__signature__ = new_sig  # type: ignore[attr-defined]
    return wrapper
