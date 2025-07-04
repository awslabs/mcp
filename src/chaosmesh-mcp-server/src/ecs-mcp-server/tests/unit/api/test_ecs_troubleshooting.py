from unittest.mock import Mock, patch

import pytest

from awslabs.ecs_mcp_server.api.ecs_troubleshooting import (
    ACTIONS,
    TROUBLESHOOTING_DOCS,
    _validate_action,
    _validate_parameters,
    ecs_troubleshooting_tool,
    generate_troubleshooting_docs,
)


class TestEcsTroubleshootingTool:
    def test_valid_action_validation(self):
        for action in ACTIONS.keys():
            _validate_action(action)

    def test_invalid_action_validation(self):
        with pytest.raises(ValueError, match="Invalid action 'invalid_action'"):
            _validate_action("invalid_action")

    def test_parameter_validation_with_app_name_required(self):
        with pytest.raises(ValueError, match="app_name is required"):
            _validate_parameters("get_ecs_troubleshooting_guidance", None, {})

        _validate_parameters("get_ecs_troubleshooting_guidance", "test-app", {})

    def test_parameter_validation_with_missing_required_params(self):
        with pytest.raises(ValueError, match="Missing required parameter 'cluster_name'"):
            _validate_parameters(
                "fetch_service_events", "test-app", {"service_name": "test-service"}
            )

    def test_parameter_validation_success(self):
        _validate_parameters(
            "fetch_service_events",
            "test-app",
            {"cluster_name": "test-cluster", "service_name": "test-service"},
        )

    def test_transformer_functions_exist(self):
        for action, config in ACTIONS.items():
            assert "transformer" in config, f"Missing transformer for action: {action}"
            assert callable(config["transformer"]), f"Transformer for {action} is not callable"

    def test_guidance_transformer(self):
        config = ACTIONS["get_ecs_troubleshooting_guidance"]
        result = config["transformer"]("test-app", {"symptoms_description": "ALB issues"})
        expected = {"app_name": "test-app", "symptoms_description": "ALB issues"}
        assert result == expected

    def test_cloudformation_transformer(self):
        config = ACTIONS["fetch_cloudformation_status"]

        result = config["transformer"]("test-app", {"stack_id": "custom-stack"})
        expected = {"stack_id": "custom-stack"}
        assert result == expected

        result = config["transformer"]("test-app", {})
        expected = {"stack_id": "test-app"}
        assert result == expected

    def test_service_events_transformer(self):
        config = ACTIONS["fetch_service_events"]
        result = config["transformer"](
            "test-app",
            {
                "cluster_name": "test-cluster",
                "service_name": "test-service",
                "time_window": 7200,
                "start_time": "2023-01-01T12:00:00Z",
            },
        )
        assert result["app_name"] == "test-app"
        assert result["cluster_name"] == "test-cluster"
        assert result["service_name"] == "test-service"
        assert result["time_window"] == 7200
        assert result["start_time"] == "2023-01-01T12:00:00Z"

    def test_task_failures_transformer(self):
        config = ACTIONS["fetch_task_failures"]
        result = config["transformer"]("test-app", {"cluster_name": "test-cluster"})
        expected = {
            "app_name": "test-app",
            "cluster_name": "test-cluster",
            "time_window": 3600,
            "start_time": None,
            "end_time": None,
        }
        assert result == expected

    def test_image_pull_transformer(self):
        config = ACTIONS["detect_image_pull_failures"]
        result = config["transformer"]("test-app", {})
        expected = {"app_name": "test-app"}
        assert result == expected

    @pytest.mark.anyio
    async def test_ecs_troubleshooting_tool_success(self):
        mock_guidance = Mock(return_value={"status": "success", "guidance": "test guidance"})

        original_func = ACTIONS["get_ecs_troubleshooting_guidance"]["func"]
        ACTIONS["get_ecs_troubleshooting_guidance"]["func"] = mock_guidance

        try:
            result = await ecs_troubleshooting_tool(
                app_name="test-app",
                action="get_ecs_troubleshooting_guidance",
                parameters={"symptoms_description": "ALB issues"},
            )

            assert result == {"status": "success", "guidance": "test guidance"}
            mock_guidance.assert_called_once_with(
                app_name="test-app", symptoms_description="ALB issues"
            )
        finally:
            ACTIONS["get_ecs_troubleshooting_guidance"]["func"] = original_func

    @pytest.mark.anyio
    async def test_ecs_troubleshooting_tool_cloudformation(self):
        mock_cf_status = Mock(return_value={"status": "success", "stack_status": "CREATE_COMPLETE"})

        original_func = ACTIONS["fetch_cloudformation_status"]["func"]
        ACTIONS["fetch_cloudformation_status"]["func"] = mock_cf_status

        try:
            result = await ecs_troubleshooting_tool(
                app_name="test-app",
                action="fetch_cloudformation_status",
                parameters={"stack_id": "test-stack"},
            )

            assert result == {"status": "success", "stack_status": "CREATE_COMPLETE"}
            mock_cf_status.assert_called_once_with(stack_id="test-stack")
        finally:
            ACTIONS["fetch_cloudformation_status"]["func"] = original_func

    @pytest.mark.anyio
    async def test_ecs_troubleshooting_tool_invalid_action(self):
        result = await ecs_troubleshooting_tool(
            app_name="test-app", action="invalid_action", parameters={}
        )

        assert result["status"] == "error"
        assert "Invalid action" in result["error"]

    @pytest.mark.anyio
    async def test_ecs_troubleshooting_tool_missing_parameters(self):
        result = await ecs_troubleshooting_tool(
            app_name=None, action="get_ecs_troubleshooting_guidance", parameters={}
        )

        assert result["status"] == "error"
        assert "app_name is required" in result["error"]

    @pytest.mark.anyio
    async def test_ecs_troubleshooting_tool_function_exception(self):
        mock_guidance = Mock(side_effect=Exception("Test exception"))

        original_func = ACTIONS["get_ecs_troubleshooting_guidance"]["func"]
        ACTIONS["get_ecs_troubleshooting_guidance"]["func"] = mock_guidance

        try:
            result = await ecs_troubleshooting_tool(
                app_name="test-app", action="get_ecs_troubleshooting_guidance", parameters={}
            )

            assert result["status"] == "error"
            assert "Internal error" in result["error"]
        finally:
            ACTIONS["get_ecs_troubleshooting_guidance"]["func"] = original_func

    @pytest.mark.anyio
    async def test_ecs_troubleshooting_tool_none_parameters(self):
        mock_guidance = Mock(return_value={"status": "success"})

        original_func = ACTIONS["get_ecs_troubleshooting_guidance"]["func"]
        ACTIONS["get_ecs_troubleshooting_guidance"]["func"] = mock_guidance

        try:
            result = await ecs_troubleshooting_tool(
                app_name="test-app", action="get_ecs_troubleshooting_guidance", parameters=None
            )

            assert result == {"status": "success"}
            mock_guidance.assert_called_once_with(app_name="test-app", symptoms_description=None)
        finally:
            ACTIONS["get_ecs_troubleshooting_guidance"]["func"] = original_func

    def test_actions_structure_completeness(self):
        expected_actions = [
            "get_ecs_troubleshooting_guidance",
            "fetch_cloudformation_status",
            "fetch_service_events",
            "fetch_task_failures",
            "fetch_task_logs",
            "detect_image_pull_failures",
            "fetch_network_configuration",
        ]

        for action in expected_actions:
            assert action in ACTIONS, f"Missing action in ACTIONS: {action}"
            assert "func" in ACTIONS[action], f"Missing func for action: {action}"
            assert "required_params" in ACTIONS[action], (
                f"Missing required_params for action: {action}"
            )
            assert "transformer" in ACTIONS[action], f"Missing transformer for action: {action}"

        assert len(ACTIONS) == len(expected_actions), "ACTIONS has unexpected actions"

    def test_required_params_mapping(self):
        for action, config in ACTIONS.items():
            assert "required_params" in config, f"Missing required_params for action: {action}"
            assert isinstance(config["required_params"], list), (
                f"required_params must be a list for action: {action}"
            )


class TestTransformerFunctions:
    def test_service_events_transformer_with_time_parameters(self):
        config = ACTIONS["fetch_service_events"]
        result = config["transformer"](
            "test-app",
            {
                "cluster_name": "test-cluster",
                "service_name": "test-service",
                "time_window": 1800,
                "start_time": "2023-01-01T10:00:00Z",
                "end_time": "2023-01-01T11:00:00Z",
            },
        )

        assert result["time_window"] == 1800
        assert result["start_time"] == "2023-01-01T10:00:00Z"
        assert result["end_time"] == "2023-01-01T11:00:00Z"

    def test_task_logs_transformer_with_all_parameters(self):
        config = ACTIONS["fetch_task_logs"]
        result = config["transformer"](
            "test-app",
            {
                "cluster_name": "test-cluster",
                "task_id": "task-abc123",
                "time_window": 1200,
                "filter_pattern": '[timestamp, request_id, level="ERROR"]',
                "start_time": "2023-01-01T10:00:00Z",
            },
        )

        assert result["task_id"] == "task-abc123"
        assert result["time_window"] == 1200
        assert result["filter_pattern"] == '[timestamp, request_id, level="ERROR"]'
        assert result["start_time"] == "2023-01-01T10:00:00Z"
        assert result["end_time"] is None


class TestEdgeCases:
    def test_empty_app_name(self):
        with pytest.raises(ValueError, match="app_name is required"):
            _validate_parameters("get_ecs_troubleshooting_guidance", "", {})

    def test_whitespace_app_name(self):
        with pytest.raises(ValueError, match="app_name is required"):
            _validate_parameters("get_ecs_troubleshooting_guidance", "   ", {})

    def test_case_sensitive_action(self):
        with pytest.raises(ValueError, match="Invalid action"):
            _validate_action("GET_ECS_TROUBLESHOOTING_GUIDANCE")

    def test_transformer_extra_parameters_ignored(self):
        config = ACTIONS["detect_image_pull_failures"]
        result = config["transformer"]("test-app", {"extra_param": "ignored", "another_extra": 123})

        assert result == {"app_name": "test-app"}
        assert "extra_param" not in result
        assert "another_extra" not in result


class TestGenerateTroubleshootingDocs:
    """Test cases for the generate_troubleshooting_docs function."""

    def test_docs_not_empty(self):
        """Test that generated docs are not empty."""
        docs = generate_troubleshooting_docs()
        assert docs
        assert isinstance(docs, str)
        assert len(docs) > 100  # Reasonable assumption that docs should be substantial

    def test_docs_contains_all_actions(self):
        """Test that the documentation contains information about all actions."""
        docs = generate_troubleshooting_docs()
        for action_name in ACTIONS.keys():
            assert action_name in docs, f"Documentation should mention action: {action_name}"

    def test_docs_contains_examples(self):
        """Test that the documentation contains examples for each action."""
        docs = generate_troubleshooting_docs()
        assert "Example:" in docs, "Documentation should contain examples"

        # Check for quick usage examples section
        assert "Quick Usage Examples" in docs, (
            "Documentation should have a Quick Usage Examples section"
        )

    def test_docs_formatting(self):
        """Test that the documentation has correct formatting."""
        docs = generate_troubleshooting_docs()
        assert "## Available Actions and Parameters:" in docs, "Missing section header for actions"
        assert "Parameters:" in docs, "Missing parameters section"
        assert "Returns:" in docs, "Missing returns section"

    def test_docs_with_mocked_action(self):
        """Test documentation generation with a mocked action."""
        # Create a copy of ACTIONS to avoid modifying the global dictionary
        test_actions = dict(ACTIONS)
        test_actions["test_action"] = {
            "func": lambda x: x,
            "required_params": ["param1"],
            "optional_params": ["param2"],
            "transformer": lambda app_name, params: params,
            "description": "Test action description",
            "param_descriptions": {"param1": "First param", "param2": "Second param"},
            "example": 'action="test_action", parameters={"param1": "value1"}',
        }

        # Use patch context manager to temporarily replace ACTIONS
        with patch("awslabs.ecs_mcp_server.api.ecs_troubleshooting.ACTIONS", test_actions):
            # Now generate docs with our modified ACTIONS dictionary
            docs = generate_troubleshooting_docs()

            # Basic checks for added action
            assert "test_action" in docs, "Added action should appear in docs"
            assert "Test action description" in docs, "Action description should be included"

            # Check that our action appears in the quick usage examples
            assert 'action: "test_action"' in docs
            assert 'parameters: {"param1": "value1"}' in docs

            # Make sure the required parameters are listed
            assert "- Required: param1" in docs
            # Check for optional parameters section with param2
            assert "- Optional: param2" in docs

    def test_troubleshooting_docs_constant(self):
        """Test that the TROUBLESHOOTING_DOCS constant is set."""
        assert TROUBLESHOOTING_DOCS
        assert isinstance(TROUBLESHOOTING_DOCS, str)
        assert TROUBLESHOOTING_DOCS == generate_troubleshooting_docs()


class TestGuardrails:
    """Guardrail tests that will fail if actions change without updating the tests."""

    def test_actions_count_unchanged(self):
        """Fail if new actions are added/removed without updating this test."""
        assert len(ACTIONS) == 7, (
            f"Expected 7 actions, got {len(ACTIONS)}. Update test if this is intentional."
        )

    def test_expected_actions_exist(self):
        """Fail if action names change or new ones are added."""
        expected_actions = {
            "get_ecs_troubleshooting_guidance",
            "fetch_cloudformation_status",
            "fetch_service_events",
            "fetch_task_failures",
            "fetch_task_logs",
            "detect_image_pull_failures",
            "fetch_network_configuration",
        }
        actual_actions = set(ACTIONS.keys())
        assert actual_actions == expected_actions, (
            f"Actions changed! Expected: {expected_actions}, Got: {actual_actions}"
        )

    def test_parameter_counts_unchanged(self):
        """Fail if parameter counts change without updating test."""
        expected_param_counts = {
            "get_ecs_troubleshooting_guidance": {"required": 1, "optional": 1},
            "fetch_cloudformation_status": {"required": 1, "optional": 0},
            "fetch_service_events": {"required": 3, "optional": 3},
            "fetch_task_failures": {"required": 2, "optional": 3},
            "fetch_task_logs": {"required": 2, "optional": 5},
            "detect_image_pull_failures": {"required": 1, "optional": 0},
            "fetch_network_configuration": {"required": 1, "optional": 2},
        }

        for action_name, expected_counts in expected_param_counts.items():
            config = ACTIONS[action_name]
            required_count = len(config["required_params"])
            optional_count = len(config.get("optional_params", []))

            assert required_count == expected_counts["required"], (
                f"{action_name}: Expected {expected_counts['required']} required params, "
                f"got {required_count}"
            )
            assert optional_count == expected_counts["optional"], (
                f"{action_name}: Expected {expected_counts['optional']} optional params, "
                f"got {optional_count}"
            )

    def test_documentation_contains_expected_content(self):
        """Fail if generated docs are missing expected action descriptions."""
        docs = generate_troubleshooting_docs()
        expected_in_docs = [
            "get_ecs_troubleshooting_guidance",
            "fetch_cloudformation_status",
            "Initial assessment and data collection",
            "Infrastructure-level diagnostics",
            "Service-level diagnostics",
            "Task-level diagnostics",
            "Application-level diagnostics",
            "Specialized tool for detecting container image",
        ]

        for expected in expected_in_docs:
            assert expected in docs, f"Documentation missing expected content: '{expected}'"

    def test_actions_have_required_fields(self):
        """Fail if any action is missing required configuration fields."""
        required_fields = [
            "func",
            "required_params",
            "optional_params",
            "transformer",
            "description",
            "param_descriptions",
            "example",
        ]

        for action_name, config in ACTIONS.items():
            for field in required_fields:
                assert field in config, f"Action '{action_name}' missing required field: '{field}'"

            # Verify field types
            assert callable(config["func"]), f"Action '{action_name}' func must be callable"
            assert callable(config["transformer"]), (
                f"Action '{action_name}' transformer must be callable"
            )
            assert isinstance(config["required_params"], list), (
                f"Action '{action_name}' required_params must be list"
            )
            assert isinstance(config["optional_params"], list), (
                f"Action '{action_name}' optional_params must be list"
            )
            assert isinstance(config["description"], str), (
                f"Action '{action_name}' description must be string"
            )
            assert isinstance(config["param_descriptions"], dict), (
                f"Action '{action_name}' param_descriptions must be dict"
            )
            assert isinstance(config["example"], str), (
                f"Action '{action_name}' example must be string"
            )
