"""
Comprehensive unit tests for aws_knowledge_proxy module.
"""

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from awslabs.ecs_mcp_server.modules.aws_knowledge_proxy import (
    DESIRED_KNOWLEDGE_PROXY_TOOLS,
    ECS_TOOL_GUIDANCE,
    _add_ecs_guidance_to_knowledge_tools,
    _filter_knowledge_proxy_tools,
    apply_tool_transformations,
    register_ecs_prompts,
    register_proxy,
)

# Test Constants
EXPECTED_PROXY_URL = "https://knowledge-mcp.global.api.aws"
EXPECTED_PROXY_NAME = "AWS-Knowledge-Bridge"

EXPECTED_KNOWLEDGE_TOOLS = [
    "aws_knowledge_aws___search_documentation",
    "aws_knowledge_aws___read_documentation",
    "aws_knowledge_aws___recommend",
]

EXPECTED_ECS_PATTERNS = [
    "what are blue green deployments",
    "what are b/g deployments",
    "native ecs blue green",
    "native ecs b/g",
    "ecs native blue green deployments",
    "difference between codedeploy and native blue green",
    "how to setup blue green",
    "setup ecs blue green",
    "configure ecs blue green deployments",
    "configure blue green",
    "configure b/g",
    "create blue green deployment",
    "ecs best practices",
    "ecs implementation guide",
    "ecs guidance",
    "ecs recommendations",
    "how to use ecs effectively",
    "new ecs feature",
    "latest ecs feature",
    "what are ecs managed instances",
    "how to setup ecs managed instances",
    "ecs managed instances",
    "ecs MI",
    "managed instances ecs",
    "ecs specialized instance types",
    "ecs custom instance types",
    "ecs instance type selection",
    "What alternatives do I have for Fargate?",
    "How do I migrate from Fargate to Managed Instances",
    "what is ecs express mode",
    "what are express gateway services",
    "ecs express mode",
    "simplified ecs deployment",
    "how to setup express mode",
    "setup ecs express mode",
    "configure ecs express mode",
    "when to use express mode",
]


def _make_mock_tool(name: str, description: str = None) -> MagicMock:
    """Create a mock Tool object with name and description attributes."""
    tool = MagicMock()
    tool.name = name
    tool.description = description
    return tool


def _generate_prompt_test_data():
    """Generate test data for prompt response testing from EXPECTED_ECS_PATTERNS."""
    expected_response = {"name": "aws_knowledge_aws___search_documentation"}
    return [(pattern, expected_response) for pattern in EXPECTED_ECS_PATTERNS]


# Test Data for Parameterized Tests
PROMPT_PATTERN_TEST_DATA = _generate_prompt_test_data()

REGISTER_PROXY_ERROR_TEST_DATA = [
    (
        "create_proxy failed",
        "create_proxy",
        "Failed to setup AWS Knowledge MCP Server proxy: create_proxy failed",
    ),
    ("Mount failed", "mount", "Failed to setup AWS Knowledge MCP Server proxy: Mount failed"),
]


# Test Fixtures
@pytest.fixture
def mock_mcp() -> MagicMock:
    """Create a mock FastMCP instance."""
    return MagicMock()


@pytest.fixture
def mock_async_mcp() -> AsyncMock:
    """Create an async mock FastMCP instance."""
    mcp = AsyncMock()
    # Make add_tool_transformation and disable synchronous as they are in the real implementation
    mcp.add_tool_transformation = MagicMock()
    mcp.disable = MagicMock()
    return mcp


@pytest.fixture
def sample_tools_list() -> List[MagicMock]:
    """Create sample tool objects as a list (FastMCP 3.0 list_tools return type)."""
    return [
        _make_mock_tool(name, f"Original description for {name}")
        for name in EXPECTED_KNOWLEDGE_TOOLS
    ]


@pytest.fixture
def sample_tools_list_with_none_description() -> List[MagicMock]:
    """Create sample tool objects with None descriptions as a list."""
    return [_make_mock_tool(name, None) for name in EXPECTED_KNOWLEDGE_TOOLS]


@pytest.fixture
def mock_transform_configs() -> List[MagicMock]:
    """Create mock ToolTransformConfig instances."""
    return [MagicMock(), MagicMock(), MagicMock()]


class TestECSToolGuidance:
    """Test the ECS_TOOL_GUIDANCE constant."""

    def test_ecs_tool_guidance_content(self) -> None:
        """Test that ECS_TOOL_GUIDANCE contains expected content."""
        expected_content = [
            "ECS DOCUMENTATION GUIDANCE",
            "up-to-date ECS documentation",
            "new ECS features",
            "ECS Native Blue-Green Deployments",
            "ECS Managed Instances",
            "ECS Express Mode",
            "launched 2025",
        ]

        for content in expected_content:
            assert content in ECS_TOOL_GUIDANCE, (
                f"Expected content '{content}' not found in ECS_TOOL_GUIDANCE"
            )

    def test_ecs_tool_guidance_structure(self) -> None:
        """Test that ECS_TOOL_GUIDANCE has proper structure."""
        assert ECS_TOOL_GUIDANCE.startswith("\n\n    ## ECS DOCUMENTATION GUIDANCE")
        assert "New ECS features include:" in ECS_TOOL_GUIDANCE
        assert ECS_TOOL_GUIDANCE.strip().endswith("launched 2025)")

    def test_ecs_tool_guidance_is_multiline(self) -> None:
        """Test that ECS_TOOL_GUIDANCE is properly formatted as multiline string."""
        lines = ECS_TOOL_GUIDANCE.strip().split("\n")
        assert len(lines) >= 3, "ECS_TOOL_GUIDANCE should have multiple lines"


class TestRegisterProxy:
    """Test the register_proxy function."""

    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.logger")
    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.register_ecs_prompts")
    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.create_proxy")
    def test_register_proxy_success(
        self,
        mock_create_proxy: MagicMock,
        mock_register_ecs: MagicMock,
        mock_logger: MagicMock,
        mock_mcp: MagicMock,
    ) -> None:
        """Test successful proxy registration."""
        # Setup mocks
        mock_aws_knowledge_proxy = MagicMock()
        mock_create_proxy.return_value = mock_aws_knowledge_proxy

        # Call the function
        result = register_proxy(mock_mcp)

        # Verify success
        assert result is True

        # Verify proxy creation
        mock_create_proxy.assert_called_once_with(EXPECTED_PROXY_URL, name=EXPECTED_PROXY_NAME)

        # Verify mounting with namespace
        mock_mcp.mount.assert_called_once_with(mock_aws_knowledge_proxy, namespace="aws_knowledge")

        # Verify ECS prompts registration
        mock_register_ecs.assert_called_once_with(mock_mcp)

        # Verify logging
        expected_log_calls = [
            call("Setting up AWS Knowledge MCP Server proxy"),
            call("Successfully mounted AWS Knowledge MCP Server"),
        ]
        mock_logger.info.assert_has_calls(expected_log_calls)

    @pytest.mark.parametrize(
        "error_message,error_component,expected_log", REGISTER_PROXY_ERROR_TEST_DATA
    )
    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.logger")
    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.create_proxy")
    def test_register_proxy_exceptions(
        self,
        mock_create_proxy: MagicMock,
        mock_logger: MagicMock,
        error_message: str,
        error_component: str,
        expected_log: str,
        mock_mcp: MagicMock,
    ) -> None:
        """Test proxy registration with various exceptions."""
        # Setup mocks
        mock_create_proxy.side_effect = Exception(error_message)

        # Call the function
        result = register_proxy(mock_mcp)

        # Verify failure
        assert result is False

        # Verify error logging
        mock_logger.error.assert_called_once_with(expected_log)

    def test_register_proxy_with_none_mcp(self) -> None:
        """Test register_proxy with None MCP instance."""
        result = register_proxy(None)
        assert result is False


class TestApplyToolTransformations:
    """Test the apply_tool_transformations function."""

    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.logger")
    @patch(
        "awslabs.ecs_mcp_server.modules.aws_knowledge_proxy._add_ecs_guidance_to_knowledge_tools"
    )
    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy._filter_knowledge_proxy_tools")
    @pytest.mark.asyncio
    async def test_apply_tool_transformations_success(
        self,
        mock_filter_tools: AsyncMock,
        mock_add_guidance: AsyncMock,
        mock_logger: MagicMock,
        mock_mcp: MagicMock,
    ) -> None:
        """Test successful tool transformations application."""
        # Setup mocks
        mock_filter_tools.return_value = None
        mock_add_guidance.return_value = None

        # Call the function
        await apply_tool_transformations(mock_mcp)

        # Verify calls
        mock_logger.info.assert_called_once_with("Applying tool transformations...")
        mock_filter_tools.assert_called_once_with(mock_mcp)
        mock_add_guidance.assert_called_once_with(mock_mcp)

    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.logger")
    @patch(
        "awslabs.ecs_mcp_server.modules.aws_knowledge_proxy._add_ecs_guidance_to_knowledge_tools"
    )
    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy._filter_knowledge_proxy_tools")
    @pytest.mark.asyncio
    async def test_apply_tool_transformations_exception(
        self,
        mock_filter_tools: AsyncMock,
        mock_add_guidance: AsyncMock,
        mock_logger: MagicMock,
        mock_mcp: MagicMock,
    ) -> None:
        """Test tool transformations application with exception."""
        # Setup mocks
        mock_filter_tools.return_value = None
        error_message = "Guidance addition failed"
        mock_add_guidance.side_effect = Exception(error_message)

        # Call the function and expect exception to propagate
        with pytest.raises(Exception, match=error_message):
            await apply_tool_transformations(mock_mcp)

        # Verify calls
        mock_logger.info.assert_called_once_with("Applying tool transformations...")
        mock_filter_tools.assert_called_once_with(mock_mcp)
        mock_add_guidance.assert_called_once_with(mock_mcp)

    @pytest.mark.asyncio
    async def test_apply_tool_transformations_with_none_mcp(self) -> None:
        """Test apply_tool_transformations with None MCP instance."""
        with pytest.raises(AttributeError):
            await apply_tool_transformations(None)


class TestAddEcsGuidanceToKnowledgeTools:
    """Test the _add_ecs_guidance_to_knowledge_tools function."""

    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.logger")
    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.ToolTransformConfig")
    @pytest.mark.asyncio
    async def test_add_ecs_guidance_success(
        self,
        mock_transform_config: MagicMock,
        mock_logger: MagicMock,
        mock_async_mcp: AsyncMock,
        sample_tools_list: List[MagicMock],
        mock_transform_configs: List[MagicMock],
    ) -> None:
        """Test successful ECS guidance addition to tools."""
        # Setup mocks - list_tools returns a list of Tool objects
        mock_async_mcp.list_tools.return_value = sample_tools_list
        mock_transform_config.side_effect = mock_transform_configs

        # Call the function
        await _add_ecs_guidance_to_knowledge_tools(mock_async_mcp)

        # Verify tool retrieval
        mock_async_mcp.list_tools.assert_called_once()

        # Verify ToolTransformConfig creation
        expected_calls = [
            call(
                name=tool_name,
                description=f"Original description for {tool_name}" + ECS_TOOL_GUIDANCE,
            )
            for tool_name in EXPECTED_KNOWLEDGE_TOOLS
        ]
        mock_transform_config.assert_has_calls(expected_calls)

        # Verify transformations were added
        expected_transform_calls = [
            call(tool_name, config)
            for tool_name, config in zip(
                EXPECTED_KNOWLEDGE_TOOLS, mock_transform_configs, strict=False
            )
        ]
        mock_async_mcp.add_tool_transformation.assert_has_calls(expected_transform_calls)

        # Verify logging
        mock_logger.debug.assert_called_once_with("Added ECS guidance to AWS Knowledge tools")

    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.logger")
    @pytest.mark.asyncio
    async def test_add_ecs_guidance_missing_tools(
        self, mock_logger: MagicMock, mock_async_mcp: AsyncMock
    ) -> None:
        """Test ECS guidance addition with missing tools."""
        # Setup mocks - only include one tool as a list
        mock_async_mcp.list_tools.return_value = [
            _make_mock_tool("aws_knowledge_aws___search_documentation", "Test description"),
        ]

        # Call the function
        await _add_ecs_guidance_to_knowledge_tools(mock_async_mcp)

        # Verify warnings for missing tools
        expected_warnings = [
            call("Tool aws_knowledge_aws___read_documentation not found in MCP tools"),
            call("Tool aws_knowledge_aws___recommend not found in MCP tools"),
        ]
        mock_logger.warning.assert_has_calls(expected_warnings, any_order=True)

    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.logger")
    @pytest.mark.asyncio
    async def test_add_ecs_guidance_list_tools_exception(
        self, mock_logger: MagicMock, mock_async_mcp: AsyncMock
    ) -> None:
        """Test ECS guidance addition with list_tools exception."""
        # Setup mocks
        error_message = "Failed to list tools"
        mock_async_mcp.list_tools.side_effect = Exception(error_message)

        # Call the function and expect exception to propagate
        with pytest.raises(Exception, match=error_message):
            await _add_ecs_guidance_to_knowledge_tools(mock_async_mcp)

        # Verify error logging
        mock_logger.error.assert_called_once_with(
            f"Error applying tool transformations: {error_message}"
        )

    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.logger")
    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.ToolTransformConfig")
    @pytest.mark.asyncio
    async def test_add_ecs_guidance_transform_exception(
        self, mock_transform_config: MagicMock, mock_logger: MagicMock, mock_async_mcp: AsyncMock
    ) -> None:
        """Test ECS guidance addition with transformation exception."""
        # Setup mocks - list_tools returns a list
        mock_async_mcp.list_tools.return_value = [
            _make_mock_tool("aws_knowledge_aws___search_documentation", "Test description"),
        ]

        # Make add_tool_transformation a regular synchronous mock that raises exception
        error_message = "Transform failed"
        mock_async_mcp.add_tool_transformation = MagicMock(side_effect=Exception(error_message))

        # Call the function and expect exception to propagate
        with pytest.raises(Exception, match=error_message):
            await _add_ecs_guidance_to_knowledge_tools(mock_async_mcp)

        # Verify error logging
        mock_logger.error.assert_called_once_with(
            f"Error applying tool transformations: {error_message}"
        )


class TestFilterKnowledgeProxyTools:
    """Test the _filter_knowledge_proxy_tools function."""

    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.logger")
    @pytest.mark.asyncio
    async def test_filter_tools_success(
        self,
        mock_logger: MagicMock,
        mock_async_mcp: AsyncMock,
    ) -> None:
        """Test successful filtering of non-allowlisted tools."""
        # Setup mocks - list_tools returns a list of Tool objects
        all_tools = [
            _make_mock_tool("aws_knowledge_aws___search_documentation"),
            _make_mock_tool("aws_knowledge_aws___read_documentation"),
            _make_mock_tool("aws_knowledge_aws___recommend"),
            _make_mock_tool("aws_knowledge_aws___list_regions"),  # Should be disabled
            _make_mock_tool("aws_knowledge_aws___get_regional_availability"),  # Should be disabled
            _make_mock_tool("other_tool"),  # Should not be touched
        ]
        mock_async_mcp.list_tools.return_value = all_tools

        # Call the function
        await _filter_knowledge_proxy_tools(mock_async_mcp)

        # Verify tool retrieval
        mock_async_mcp.list_tools.assert_called_once()

        # Verify only non-allowlisted aws_knowledge tools were disabled via disable()
        disabled_tools = [
            "aws_knowledge_aws___list_regions",
            "aws_knowledge_aws___get_regional_availability",
        ]

        assert mock_async_mcp.disable.call_count == len(disabled_tools)

        # Verify each disabled tool
        for tool_name in disabled_tools:
            mock_async_mcp.disable.assert_any_call(names={tool_name})

        # Verify logging - should have one debug call per disabled tool plus one summary call
        expected_debug_calls = len(disabled_tools) + 1  # 2 disabled + 1 summary = 3
        assert mock_logger.debug.call_count == expected_debug_calls

        # Verify the summary log message
        final_call = mock_logger.debug.call_args_list[-1]
        assert "Filtered AWS Knowledge tools to allowlist" in str(final_call)

    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.logger")
    @pytest.mark.asyncio
    async def test_filter_tools_only_allowlisted_present(
        self, mock_logger: MagicMock, mock_async_mcp: AsyncMock
    ) -> None:
        """Test filtering when only allowlisted tools are present."""
        # Setup mocks - only allowlisted tools as a list
        allowlisted_tools = [
            _make_mock_tool("aws_knowledge_aws___search_documentation"),
            _make_mock_tool("aws_knowledge_aws___read_documentation"),
            _make_mock_tool("aws_knowledge_aws___recommend"),
        ]
        mock_async_mcp.list_tools.return_value = allowlisted_tools

        # Call the function
        await _filter_knowledge_proxy_tools(mock_async_mcp)

        # Verify no tools were disabled
        mock_async_mcp.disable.assert_not_called()

        # Verify logging
        mock_logger.debug.assert_called_once()


class TestRegisterEcsPrompts:
    """Test the register_ecs_prompts function."""

    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.logger")
    def test_register_ecs_prompts_registration(
        self, mock_logger: MagicMock, mock_mcp: MagicMock
    ) -> None:
        """Test that all ECS prompt patterns are registered."""
        # Setup mock MCP
        registered_prompts = {}

        def mock_prompt_decorator(pattern: str):
            def decorator(func):
                registered_prompts[pattern] = func
                return func

            return decorator

        mock_mcp.prompt = mock_prompt_decorator

        # Call the function
        register_ecs_prompts(mock_mcp)

        # Verify all expected prompt patterns were registered
        expected_count = len(EXPECTED_ECS_PATTERNS)
        assert len(registered_prompts) == expected_count, (
            f"Expected {expected_count} patterns, got {len(registered_prompts)}"
        )

        for expected_pattern in EXPECTED_ECS_PATTERNS:
            assert expected_pattern in registered_prompts, (
                f"Pattern '{expected_pattern}' not registered"
            )

        # Verify logging
        expected_count = len(EXPECTED_ECS_PATTERNS)
        mock_logger.info.assert_called_once_with(
            f"Registered {expected_count} ECS-related prompt patterns "
            f"with AWS Knowledge proxy tools"
        )

    @pytest.mark.parametrize("pattern,expected_response", PROMPT_PATTERN_TEST_DATA)
    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.logger")
    def test_register_ecs_prompts_responses(
        self,
        mock_logger: MagicMock,
        pattern: str,
        expected_response: Dict[str, Any],
        mock_mcp: MagicMock,
    ) -> None:
        """Test that prompt functions return correct responses."""
        # Setup mock MCP
        registered_prompts = {}

        def mock_prompt_decorator(pattern_name: str):
            def decorator(func):
                registered_prompts[pattern_name] = func
                return func

            return decorator

        mock_mcp.prompt = mock_prompt_decorator

        # Call the function
        register_ecs_prompts(mock_mcp)

        # Test the specific pattern
        if pattern in registered_prompts:
            response = registered_prompts[pattern]()
            assert len(response) == 1, f"Expected single response for pattern '{pattern}'"
            assert response[0] == expected_response, f"Incorrect response for pattern '{pattern}'"


class TestUpstreamToolDetection:
    """Test detection of expected upstream AWS Knowledge tools."""

    def test_expected_knowledge_tool_names_referenced(self) -> None:
        """Test that expected AWS Knowledge tool names are properly referenced."""
        for tool_name in EXPECTED_KNOWLEDGE_TOOLS:
            assert tool_name in DESIRED_KNOWLEDGE_PROXY_TOOLS, (
                f"Expected tool {tool_name} not found in DESIRED_KNOWLEDGE_PROXY_TOOLS"
            )

    def test_prompt_responses_reference_correct_tools(self, mock_mcp: MagicMock) -> None:
        """Test that prompt responses reference the correct AWS Knowledge tools."""
        registered_prompts = {}

        def mock_prompt_decorator(pattern: str):
            def decorator(func):
                registered_prompts[pattern] = func
                return func

            return decorator

        mock_mcp.prompt = mock_prompt_decorator

        register_ecs_prompts(mock_mcp)

        for pattern, func in registered_prompts.items():
            response = func()
            assert len(response) == 1, f"Expected single response for pattern '{pattern}'"
            assert response[0]["name"] == "aws_knowledge_aws___search_documentation", (
                f"Incorrect tool reference in pattern '{pattern}'"
            )


class TestLoggingFunctionality:
    """Test logging functionality across all functions."""

    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.logger")
    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.create_proxy")
    def test_register_proxy_logging_levels(
        self, mock_create_proxy: MagicMock, mock_logger: MagicMock, mock_mcp: MagicMock
    ) -> None:
        """Test different logging levels in register_proxy."""
        error_message = "Test error"
        mock_create_proxy.side_effect = Exception(error_message)

        # Call function
        result = register_proxy(mock_mcp)

        # Verify info and error logging
        assert result is False
        mock_logger.info.assert_called_with("Setting up AWS Knowledge MCP Server proxy")
        mock_logger.error.assert_called_with(
            f"Failed to setup AWS Knowledge MCP Server proxy: {error_message}"
        )

    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.logger")
    @pytest.mark.asyncio
    async def test_add_ecs_guidance_logging_levels(
        self, mock_logger: MagicMock, mock_async_mcp: AsyncMock
    ) -> None:
        """Test different logging levels in _add_ecs_guidance_to_knowledge_tools."""
        # Test warning logging for missing tools - list_tools returns empty list
        mock_async_mcp.list_tools.return_value = []

        await _add_ecs_guidance_to_knowledge_tools(mock_async_mcp)

        # Verify warning calls for all missing tools
        expected_warnings = [
            call(f"Tool {tool_name} not found in MCP tools")
            for tool_name in EXPECTED_KNOWLEDGE_TOOLS
        ]
        mock_logger.warning.assert_has_calls(expected_warnings, any_order=True)


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.logger")
    @pytest.mark.asyncio
    async def test_empty_tools_list(
        self, mock_logger: MagicMock, mock_async_mcp: AsyncMock
    ) -> None:
        """Test handling of empty tools list."""
        mock_async_mcp.list_tools.return_value = []

        # Should not raise exception
        await _add_ecs_guidance_to_knowledge_tools(mock_async_mcp)

        # Should log warnings for all missing tools
        assert mock_logger.warning.call_count == len(EXPECTED_KNOWLEDGE_TOOLS)

    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.logger")
    @pytest.mark.asyncio
    async def test_none_description_handling(
        self,
        mock_logger: MagicMock,
        mock_async_mcp: AsyncMock,
        sample_tools_list_with_none_description: List[MagicMock],
    ) -> None:
        """Test handling of tools with None description."""
        # Use only one tool for this test
        mock_async_mcp.list_tools.return_value = [
            sample_tools_list_with_none_description[0],  # search_documentation with None desc
        ]

        with patch(
            "awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.ToolTransformConfig"
        ) as mock_config:
            await _add_ecs_guidance_to_knowledge_tools(mock_async_mcp)

            # Should handle None description by using empty string
            mock_config.assert_called_once_with(
                name="aws_knowledge_aws___search_documentation", description="" + ECS_TOOL_GUIDANCE
            )


class TestModuleIntegration:
    """Test module-level integration scenarios."""

    def test_constant_used_in_functions(self) -> None:
        """Test that ECS_TOOL_GUIDANCE constant is used in the right places."""
        import awslabs.ecs_mcp_server.modules.aws_knowledge_proxy as module

        assert hasattr(module, "ECS_TOOL_GUIDANCE")
        assert module.ECS_TOOL_GUIDANCE == ECS_TOOL_GUIDANCE

    def test_all_functions_importable(self) -> None:
        """Test that all functions can be imported successfully."""
        from awslabs.ecs_mcp_server.modules.aws_knowledge_proxy import (
            apply_tool_transformations,
            register_ecs_prompts,
            register_proxy,
        )

        assert callable(register_proxy)
        assert callable(apply_tool_transformations)
        assert callable(register_ecs_prompts)

    def test_module_has_expected_exports(self) -> None:
        """Test that module exports expected functions and constants."""
        import awslabs.ecs_mcp_server.modules.aws_knowledge_proxy as module

        expected_exports = [
            "ECS_TOOL_GUIDANCE",
            "register_proxy",
            "apply_tool_transformations",
            "register_ecs_prompts",
        ]

        for export in expected_exports:
            assert hasattr(module, export), f"Module missing expected export: {export}"

    def test_constants_are_immutable_types(self) -> None:
        """Test that constants use immutable types."""
        assert isinstance(ECS_TOOL_GUIDANCE, str)

        for tool_name in EXPECTED_KNOWLEDGE_TOOLS:
            assert isinstance(tool_name, str)
