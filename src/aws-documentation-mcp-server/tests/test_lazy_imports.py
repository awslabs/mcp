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

"""Tests verifying that heavy imports are deferred in server modules.

Uses subprocess-based isolation to ensure a clean sys.modules state.
"""

import pytest
import subprocess
import sys
import textwrap


def _run_isolated(code: str) -> subprocess.CompletedProcess:
    """Run *code* in a fresh Python subprocess and return the result."""
    return subprocess.run(
        [sys.executable, '-c', textwrap.dedent(code)],
        capture_output=True,
        text=True,
        timeout=30,
    )


HEAVY_MODULES = ['httpx', 'markdownify', 'pydantic', 'mcp.server.fastmcp']


@pytest.mark.parametrize('server_module', ['server_aws', 'server_aws_cn'])
@pytest.mark.parametrize('heavy_module', HEAVY_MODULES)
def test_heavy_module_not_loaded_on_import(server_module, heavy_module):
    """Heavy modules must not appear in sys.modules after importing a server module."""
    result = _run_isolated(
        f"""\
        import sys
        from awslabs.aws_documentation_mcp_server import {server_module}
        print({heavy_module!r} not in sys.modules)
        """
    )
    assert result.returncode == 0, f'subprocess failed: {result.stderr}'
    assert result.stdout.strip() == 'True', (
        f'{heavy_module} was loaded into sys.modules on import of {server_module}'
    )


@pytest.mark.parametrize('server_module', ['server_aws', 'server_aws_cn'])
def test_all_heavy_modules_absent(server_module):
    """Combined check: none of the heavy modules are in sys.modules."""
    modules_csv = ','.join(HEAVY_MODULES)
    result = _run_isolated(
        f"""\
        import sys
        from awslabs.aws_documentation_mcp_server import {server_module}
        heavy = [m for m in "{modules_csv}".split(",") if m in sys.modules]
        print(",".join(heavy) if heavy else "NONE")
        """
    )
    assert result.returncode == 0, f'subprocess failed: {result.stderr}'
    assert result.stdout.strip() == 'NONE', (
        f'Heavy modules loaded on import of {server_module}: {result.stdout.strip()}'
    )


@pytest.mark.parametrize('server_module', ['server_aws', 'server_aws_cn'])
def test_mcp_is_lazy_server_after_import(server_module):
    """server_module.mcp should be a LazyServer instance, with FastMCP un-imported."""
    result = _run_isolated(
        f"""\
        import sys
        from awslabs.aws_documentation_mcp_server import {server_module}
        print(type({server_module}.mcp).__name__)
        print("mcp.server.fastmcp" not in sys.modules)
        """
    )
    assert result.returncode == 0, f'subprocess failed: {result.stderr}'
    out = result.stdout.strip().splitlines()
    assert out[0] == 'LazyServer', (
        f'{server_module}.mcp is not a LazyServer after import: {out[0]}'
    )
    assert out[1] == 'True', f'mcp.server.fastmcp was imported by importing {server_module}'


@pytest.mark.parametrize('server_module', ['server_aws', 'server_aws_cn'])
def test_lazy_server_undefined_attr_raises(server_module):
    """Accessing an unknown attribute before run()/build() should raise RuntimeError."""
    result = _run_isolated(
        f"""\
        from awslabs.aws_documentation_mcp_server import {server_module}
        try:
            {server_module}.mcp.does_not_exist
            print("NO_ERROR")
        except RuntimeError:
            print("RuntimeError")
        except AttributeError:
            print("AttributeError")
        """
    )
    assert result.returncode == 0, f'subprocess failed: {result.stderr}'
    assert result.stdout.strip() == 'RuntimeError', (
        'Expected RuntimeError from uninitialized LazyServer, got: ' + result.stdout.strip()
    )
