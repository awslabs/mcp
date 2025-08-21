"""
Lightweight MCP Inspector Integration Test Framework.

This module provides a framework for testing MCP servers using the MCP inspector CLI tool.
It includes utilities for running inspector commands, parsing results, and making assertions.
"""

import json
import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MCPInspectorResult:
    """Result from an MCP inspector command."""

    success: bool
    stdout: str
    stderr: str
    return_code: int
    parsed_json: Optional[Dict[str, Any]] = None
    execution_time: float = 0.0


class MCPInspectorError(Exception):
    """Exception raised when MCP inspector command fails."""

    def __init__(self, message: str, result: MCPInspectorResult):
        super().__init__(message)
        self.result = result


class MCPInspectorFramework:
    """Framework for testing MCP servers using the MCP inspector CLI."""

    def __init__(
        self,
        server_path: str,
        server_args: Optional[List[str]] = None,
        timeout: int = 30,
        uv_path: str = "/opt/homebrew/bin/uv",
        inspector_package: str = "@modelcontextprotocol/inspector",
        use_config_file: bool = True,
    ):
        """
        Initialize the MCP Inspector Framework.

        Args:
            server_path: Path to the MCP server main.py file
            server_args: Additional arguments for the server
            timeout: Timeout for inspector commands in seconds
            uv_path: Path to the uv binary
            inspector_package: NPM package for the MCP inspector
            use_config_file: Whether to use config file approach (recommended)
        """
        self.server_path = Path(server_path)
        self.server_args = server_args or []
        self.timeout = timeout
        self.uv_path = uv_path
        self.inspector_package = inspector_package
        self.use_config_file = use_config_file

        # Validate paths
        if not self.server_path.exists():
            raise FileNotFoundError(f"Server path does not exist: {self.server_path}")

        # Get the server directory for --directory flag
        self.server_directory = self.server_path.parent.parent.parent

        # Create config file if using config file approach
        if self.use_config_file:
            self._create_config_file()

    def _create_config_file(self):
        """Create a temporary config file for the MCP inspector."""
        import json
        import tempfile

        # Create logs directory if it doesn't exist
        logs_dir = self.server_directory / "logs"
        logs_dir.mkdir(exist_ok=True)

        config = {
            "mcpServers": {
                "test-server": {
                    "command": self.uv_path,
                    "args": [
                        "--directory",
                        str(self.server_directory),
                        "run",
                        str(self.server_path),
                    ]
                    + self.server_args,
                    "env": {
                        "FASTMCP_LOG_LEVEL": "DEBUG",
                        "FASTMCP_LOG_FILE": str(logs_dir / "debug.log"),
                        "AWS_REGION": "us-west-2",
                    },
                }
            }
        }

        # Create temporary config file
        self.config_fd, self.config_path = tempfile.mkstemp(suffix=".json", prefix="mcp-config-")
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)

    def _update_config_for_write_operations(self):
        """Update the config to enable write operations for CRUD tests."""
        if self.use_config_file and hasattr(self, "config_path"):
            import json

            # Read current config
            with open(self.config_path, "r") as f:
                config = json.load(f)

            # Enable write operations
            config["mcpServers"]["test-server"]["env"]["ALLOW_WRITE"] = "true"
            config["mcpServers"]["test-server"]["env"]["ALLOW_SENSITIVE_DATA"] = "true"

            # Write updated config
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=2)

    def __del__(self):
        """Clean up temporary config file."""
        if hasattr(self, "config_fd") and hasattr(self, "config_path"):
            try:
                import os

                os.close(self.config_fd)
                os.unlink(self.config_path)
            except Exception:
                pass

    def _build_inspector_command(
        self, method: str, additional_args: Optional[List[str]] = None
    ) -> List[str]:
        """Build the MCP inspector command."""
        if self.use_config_file:
            # Use config file approach (works around --arguments bug)
            cmd = [
                "mcp-inspector",
                "--config",
                self.config_path,
                "--server",
                "test-server",
                "--cli",
                "--method",
                method,
            ]

            if additional_args:
                cmd.extend(additional_args)

            return cmd
        else:
            # Use direct command approach (has --arguments bug)
            cmd = ["npx", self.inspector_package, "--cli", "--method", method]

            if additional_args:
                cmd.extend(additional_args)

            # Add separator and server command
            cmd.extend(
                [
                    "--",
                    self.uv_path,
                    "--directory",
                    str(self.server_directory),
                    "run",
                    str(self.server_path),
                ]
            )

            # Add server arguments
            cmd.extend(self.server_args)

            return cmd

    def run_inspector_command(
        self, method: str, additional_args: Optional[List[str]] = None, expect_success: bool = True
    ) -> MCPInspectorResult:
        """
        Run an MCP inspector command.

        Args:
            method: MCP method to call (e.g., 'tools/list', 'tools/call')
            additional_args: Additional arguments for the inspector
            expect_success: Whether to expect the command to succeed

        Returns:
            MCPInspectorResult with command output and parsed JSON

        Raises:
            MCPInspectorError: If command fails and expect_success is True
        """
        cmd = self._build_inspector_command(method, additional_args)

        logger.info(f"Running MCP inspector command: {' '.join(cmd)}")

        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            execution_time = time.time() - start_time

            # Try to parse JSON from stdout
            parsed_json = None
            if result.stdout.strip():
                try:
                    parsed_json = json.loads(result.stdout)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON output: {e}")
                    logger.debug(f"Raw stdout: {result.stdout}")

            inspector_result = MCPInspectorResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                parsed_json=parsed_json,
                execution_time=execution_time,
            )

            if expect_success and not inspector_result.success:
                raise MCPInspectorError(
                    f"MCP inspector command failed: {result.stderr}", inspector_result
                )

            return inspector_result

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            error_result = MCPInspectorResult(
                success=False,
                stdout="",
                stderr=f"Command timed out after {self.timeout} seconds",
                return_code=-1,
                execution_time=execution_time,
            )

            if expect_success:
                raise MCPInspectorError("MCP inspector command timed out", error_result) from None

            return error_result

    def list_tools(self) -> MCPInspectorResult:
        """List all available tools from the MCP server."""
        return self.run_inspector_command("tools/list")

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPInspectorResult:
        """
        Call a specific tool with arguments.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            MCPInspectorResult with tool execution result
        """
        # Convert arguments to --tool-arg key=value format
        tool_args = []
        for key, value in arguments.items():
            tool_args.extend(["--tool-arg", f"{key}={value}"])

        additional_args = ["--tool-name", tool_name] + tool_args
        return self.run_inspector_command("tools/call", additional_args)

    def list_resources(self) -> MCPInspectorResult:
        """List all available resources from the MCP server."""
        return self.run_inspector_command("resources/list")

    def get_resource(self, resource_uri: str) -> MCPInspectorResult:
        """
        Get a specific resource.

        Args:
            resource_uri: URI of the resource to get

        Returns:
            MCPInspectorResult with resource content
        """
        return self.run_inspector_command("resources/read", ["--uri", resource_uri])


class MCPTestAssertions:
    """Custom assertions for MCP testing."""

    @staticmethod
    def assert_tools_exist(result: MCPInspectorResult, expected_tools: List[str]):
        """Assert that specific tools exist in the tools list result."""
        assert result.success, f"Tools list command failed: {result.stderr}"
        assert result.parsed_json is not None, "No JSON response received"

        tools = result.parsed_json.get("tools", [])
        tool_names = [tool.get("name") for tool in tools]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Tool '{expected_tool}' not found in {tool_names}"

    @staticmethod
    def assert_tool_has_schema(result: MCPInspectorResult, tool_name: str):
        """Assert that a tool has a proper input schema."""
        assert result.success, f"Tools list command failed: {result.stderr}"
        assert result.parsed_json is not None, "No JSON response received"

        tools = result.parsed_json.get("tools", [])
        tool = next((t for t in tools if t.get("name") == tool_name), None)

        assert tool is not None, f"Tool '{tool_name}' not found"
        assert "inputSchema" in tool, f"Tool '{tool_name}' missing input schema"

        schema = tool["inputSchema"]
        assert "type" in schema, f"Tool '{tool_name}' schema missing type"
        assert schema["type"] == "object", f"Tool '{tool_name}' schema should be object type"

    @staticmethod
    def assert_execution_time_under(result: MCPInspectorResult, max_seconds: float):
        """Assert that command execution time is under the specified limit."""
        assert result.execution_time < max_seconds, (
            f"Execution time {result.execution_time:.2f}s exceeded limit of {max_seconds}s"
        )

    @staticmethod
    def assert_tool_call_success(result: MCPInspectorResult, tool_name: str):
        """Assert that a tool call was successful."""
        assert result.success, f"Tool call to '{tool_name}' failed: {result.stderr}"
        assert result.parsed_json is not None, "No JSON response received"

        # Check for common success indicators
        content = result.parsed_json.get("content", [])
        assert len(content) > 0, f"Tool '{tool_name}' returned empty content"

    @staticmethod
    def assert_error_contains(result: MCPInspectorResult, error_message: str):
        """Assert that an error result contains a specific message."""
        assert not result.success, "Expected command to fail but it succeeded"
        error_text = result.stderr.lower()
        assert error_message.lower() in error_text, (
            f"Expected error message '{error_message}' not found in: {result.stderr}"
        )


class MCPTestBase:
    """Base class for MCP integration tests."""

    def __init__(self, framework: MCPInspectorFramework):
        self.framework = framework
        self.assertions = MCPTestAssertions()

    def setup_method(self):
        """Setup method called before each test."""
        pass

    def teardown_method(self):
        """Teardown method called after each test."""
        pass
