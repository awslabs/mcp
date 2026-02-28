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

"""Tests verifying that heavy imports are deferred in server_aws.

Uses subprocess-based isolation to ensure a clean sys.modules state.

Validates: Requirements 3.1, 3.2
"""

import subprocess
import sys
import textwrap


def _run_isolated(code: str) -> subprocess.CompletedProcess:
    """Run *code* in a fresh Python subprocess and return the result."""
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestHeavyModulesNotLoadedOnImport:
    """Importing server_aws must NOT pull in heavy dependencies."""

    HEAVY_MODULES = ["httpx", "markdownify", "pydantic", "mcp.server.fastmcp"]

    def test_httpx_not_in_sys_modules(self):
        """httpx must not be loaded after importing server_aws."""
        result = _run_isolated(
            """\
            import sys
            from awslabs.aws_documentation_mcp_server import server_aws
            print("httpx" not in sys.modules)
            """
        )
        assert result.returncode == 0, f"subprocess failed: {result.stderr}"
        assert result.stdout.strip() == "True", (
            "httpx was loaded into sys.modules on import of server_aws"
        )

    def test_markdownify_not_in_sys_modules(self):
        """markdownify must not be loaded after importing server_aws."""
        result = _run_isolated(
            """\
            import sys
            from awslabs.aws_documentation_mcp_server import server_aws
            print("markdownify" not in sys.modules)
            """
        )
        assert result.returncode == 0, f"subprocess failed: {result.stderr}"
        assert result.stdout.strip() == "True", (
            "markdownify was loaded into sys.modules on import of server_aws"
        )

    def test_pydantic_not_in_sys_modules(self):
        """pydantic must not be loaded after importing server_aws."""
        result = _run_isolated(
            """\
            import sys
            from awslabs.aws_documentation_mcp_server import server_aws
            print("pydantic" not in sys.modules)
            """
        )
        assert result.returncode == 0, f"subprocess failed: {result.stderr}"
        assert result.stdout.strip() == "True", (
            "pydantic was loaded into sys.modules on import of server_aws"
        )

    def test_mcp_fastmcp_not_in_sys_modules(self):
        """mcp.server.fastmcp must not be loaded after importing server_aws."""
        result = _run_isolated(
            """\
            import sys
            from awslabs.aws_documentation_mcp_server import server_aws
            print("mcp.server.fastmcp" not in sys.modules)
            """
        )
        assert result.returncode == 0, f"subprocess failed: {result.stderr}"
        assert result.stdout.strip() == "True", (
            "mcp.server.fastmcp was loaded into sys.modules on import of server_aws"
        )

    def test_all_heavy_modules_absent(self):
        """Combined check: none of the heavy modules are in sys.modules."""
        modules_csv = ",".join(self.HEAVY_MODULES)
        result = _run_isolated(
            f"""\
            import sys
            from awslabs.aws_documentation_mcp_server import server_aws
            heavy = [m for m in "{modules_csv}".split(",") if m in sys.modules]
            print(",".join(heavy) if heavy else "NONE")
            """
        )
        assert result.returncode == 0, f"subprocess failed: {result.stderr}"
        assert result.stdout.strip() == "NONE", (
            f"Heavy modules loaded on import: {result.stdout.strip()}"
        )


class TestFastMCPNotCreatedOnImport:
    """FastMCP instance must not exist until main() is called."""

    def test_mcp_is_none_after_import(self):
        """server_aws.mcp should be None immediately after import."""
        result = _run_isolated(
            """\
            from awslabs.aws_documentation_mcp_server import server_aws
            print(server_aws.mcp is None)
            """
        )
        assert result.returncode == 0, f"subprocess failed: {result.stderr}"
        assert result.stdout.strip() == "True", (
            "server_aws.mcp is not None after import — FastMCP was created eagerly"
        )
