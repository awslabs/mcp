"""
Integration tests for ECS Resource Management tool using MCP Inspector CLI.

This module specifically tests the ecs_resource_management tool with various
ECS operations, starting with ListClusters functionality.
"""

import logging
from pathlib import Path

import pytest

from .mcp_inspector_framework import MCPInspectorFramework, MCPTestAssertions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestECSResourceManagement:
    """Integration tests for ECS Resource Management tool."""

    @classmethod
    def setup_class(cls):
        """Set up the test class with MCP Inspector framework."""
        # Path to the ECS MCP server main.py
        server_path = Path(__file__).parent.parent.parent / "awslabs" / "ecs_mcp_server" / "main.py"

        # Initialize the framework with config file approach
        cls.framework = MCPInspectorFramework(
            server_path=str(server_path),
            timeout=60,  # Longer timeout for AWS API calls
            use_config_file=True,
        )

        # Create assertions helper
        cls.assertions = MCPTestAssertions()

    def setup_method(self):
        """Setup before each test method."""
        logger.info(f"Starting test: {self._get_test_name()}")

    def teardown_method(self):
        """Cleanup after each test method."""
        logger.info(f"Completed test: {self._get_test_name()}")

    def _get_test_name(self):
        """Get the current test method name."""
        import inspect

        return inspect.stack()[2].function

    def test_list_clusters_basic(self):
        """Test basic ListClusters functionality."""
        logger.info("Testing ecs_resource_management with ListClusters")

        # Arguments for listing clusters (correct format for ecs_resource_management tool)
        arguments = {"api_operation": "ListClusters"}

        # Call the tool
        result = TestECSResourceManagement.framework.call_tool("ecs_resource_management", arguments)

        # The tool call should now work with the corrected framework
        logger.info(f"Tool call result: {result.success}")
        logger.info(f"Tool call output: {result.stdout}")

        # Basic assertions
        assert result.success, f"ecs_resource_management call failed: {result.stderr}"
        assert result.parsed_json is not None, "No JSON response received"

        # Check that we got content back
        content = result.parsed_json.get("content", [])
        assert len(content) > 0, "Tool returned empty content"

        # The first content item should be text with cluster information
        first_content = content[0]
        assert "type" in first_content, "Content missing type field"
        assert first_content["type"] == "text", "Expected text content type"
        assert "text" in first_content, "Content missing text field"

        # Log the response for debugging
        response_text = first_content["text"]
        logger.info(f"ListClusters response: {response_text[:200]}...")  # First 200 chars

        # Parse the JSON response from the tool
        import json

        try:
            ecs_response = json.loads(response_text)
            assert "clusterArns" in ecs_response, "Response should contain clusterArns"
            assert "ResponseMetadata" in ecs_response, "Response should contain ResponseMetadata"

            # Check that we got a successful HTTP response
            metadata = ecs_response["ResponseMetadata"]
            assert metadata.get("HTTPStatusCode") == 200, (
                f"Expected HTTP 200, got {metadata.get('HTTPStatusCode')}"
            )

            logger.info(f"Found {len(ecs_response['clusterArns'])} ECS clusters")

        except json.JSONDecodeError as e:
            pytest.fail(f"Failed to parse ECS response as JSON: {e}")

        logger.info("✅ ListClusters test completed successfully")

    def test_list_clusters_with_filters(self):
        """Test ListClusters with filters (if any clusters exist)."""
        logger.info("Testing ecs_resource_management with ListClusters and filters")

        # First, get basic cluster list to see if we have any clusters
        basic_args = {"action": "list", "resource_type": "cluster"}

        basic_result = TestECSResourceManagement.framework.call_tool(
            "ecs_resource_management", basic_args
        )

        assert basic_result.success, "Basic cluster list failed"

        # Now test with filters (empty filters should still work)
        filtered_args = {"action": "list", "resource_type": "cluster", "filters": {}}

        filtered_result = TestECSResourceManagement.framework.call_tool(
            "ecs_resource_management", filtered_args
        )

        assert filtered_result.success, f"Filtered cluster list failed: {filtered_result.stderr}"
        assert filtered_result.parsed_json is not None, "No JSON response received"

        content = filtered_result.parsed_json.get("content", [])
        assert len(content) > 0, "Filtered tool returned empty content"

        logger.info("ListClusters with filters test completed successfully")

    def test_describe_cluster_nonexistent(self):
        """Test describing a non-existent cluster (should handle gracefully)."""
        logger.info("Testing ecs_resource_management with describe non-existent cluster")

        # Try to describe a cluster that doesn't exist
        arguments = {
            "action": "describe",
            "resource_type": "cluster",
            "identifier": "non-existent-cluster-12345",
        }

        # This should not crash, but may return an error message
        result = TestECSResourceManagement.framework.call_tool("ecs_resource_management", arguments)

        # The tool should handle this gracefully - either succeed with an error message
        # or fail with a meaningful error
        if result.success:
            # If it succeeds, it should have content explaining the cluster doesn't exist
            content = result.parsed_json.get("content", [])
            assert len(content) > 0, "Tool should return content even for non-existent cluster"

            response_text = content[0].get("text", "").lower()
            # Should mention that cluster doesn't exist or similar
            assert any(
                word in response_text
                for word in ["not found", "does not exist", "error", "invalid"]
            ), f"Response should indicate cluster doesn't exist: {response_text}"
        else:
            # If it fails, should have meaningful error message
            assert result.stderr, "Should have error message for non-existent cluster"
            logger.info(f"Expected error for non-existent cluster: {result.stderr}")

        logger.info("Describe non-existent cluster test completed successfully")

    def test_invalid_action(self):
        """Test ecs_resource_management with invalid action."""
        logger.info("Testing ecs_resource_management with invalid action")

        arguments = {"action": "invalid_action", "resource_type": "cluster"}

        result = TestECSResourceManagement.framework.call_tool("ecs_resource_management", arguments)

        # This should fail or return an error message
        if result.success:
            # If it succeeds, should have error content
            content = result.parsed_json.get("content", [])
            assert len(content) > 0, "Should return error content for invalid action"

            response_text = content[0].get("text", "").lower()
            assert any(
                word in response_text for word in ["invalid", "error", "not supported", "unknown"]
            ), f"Should indicate invalid action: {response_text}"
        else:
            # If it fails, should have error message
            assert result.stderr, "Should have error message for invalid action"

        logger.info("Invalid action test completed successfully")

    def test_invalid_resource_type(self):
        """Test ecs_resource_management with invalid resource type."""
        logger.info("Testing ecs_resource_management with invalid resource type")

        arguments = {"action": "list", "resource_type": "invalid_resource"}

        result = TestECSResourceManagement.framework.call_tool("ecs_resource_management", arguments)

        # This should fail or return an error message
        if result.success:
            # If it succeeds, should have error content
            content = result.parsed_json.get("content", [])
            assert len(content) > 0, "Should return error content for invalid resource type"

            response_text = content[0].get("text", "").lower()
            assert any(
                word in response_text for word in ["invalid", "error", "not supported", "unknown"]
            ), f"Should indicate invalid resource type: {response_text}"
        else:
            # If it fails, should have error message
            assert result.stderr, "Should have error message for invalid resource type"

        logger.info("Invalid resource type test completed successfully")

    def test_tool_execution_time(self):
        """Test that the resource management tool executes within reasonable time."""
        logger.info("Testing ecs_resource_management execution time")

        arguments = {"action": "list", "resource_type": "cluster"}

        result = TestECSResourceManagement.framework.call_tool("ecs_resource_management", arguments)

        assert result.success, "Tool execution failed"

        # AWS API calls can be slower, but should complete within 30 seconds
        TestECSResourceManagement.assertions.assert_execution_time_under(result, 30.0)

        logger.info(f"Tool execution time: {result.execution_time:.2f}s")

    @pytest.mark.requires_aws
    def test_list_services_requires_cluster(self):
        """Test listing services (requires cluster parameter)."""
        logger.info("Testing ecs_resource_management with ListServices")

        # First get clusters to see if we have any
        cluster_args = {"action": "list", "resource_type": "cluster"}

        cluster_result = TestECSResourceManagement.framework.call_tool(
            "ecs_resource_management", cluster_args
        )

        assert cluster_result.success, "Failed to list clusters"

        # Try to list services without specifying a cluster (should fail or require cluster)
        service_args = {"action": "list", "resource_type": "service"}

        service_result = TestECSResourceManagement.framework.call_tool(
            "ecs_resource_management", service_args
        )

        # This might succeed with empty results or fail requiring cluster
        if service_result.success:
            content = service_result.parsed_json.get("content", [])
            if content:
                response_text = content[0].get("text", "").lower()
                logger.info(f"Service list response: {response_text[:200]}...")
        else:
            logger.info(f"Service list failed as expected: {service_result.stderr}")

        logger.info("ListServices test completed")

    @pytest.mark.requires_aws
    def test_list_task_definitions(self):
        """Test listing task definitions."""
        logger.info("Testing ecs_resource_management with ListTaskDefinitions")

        arguments = {"action": "list", "resource_type": "task_definition"}

        result = TestECSResourceManagement.framework.call_tool("ecs_resource_management", arguments)

        assert result.success, f"ListTaskDefinitions failed: {result.stderr}"
        assert result.parsed_json is not None, "No JSON response received"

        content = result.parsed_json.get("content", [])
        assert len(content) > 0, "Tool returned empty content"

        response_text = content[0].get("text", "")
        logger.info(f"TaskDefinitions response: {response_text[:200]}...")

        # Should mention task definitions even if empty
        assert "task" in response_text.lower(), "Response should mention tasks"

        logger.info("ListTaskDefinitions test completed successfully")


# Standalone test function for quick testing
def test_ecs_resource_management_list_clusters():
    """Standalone test function for ListClusters."""
    server_path = Path(__file__).parent.parent.parent / "awslabs" / "ecs_mcp_server" / "main.py"
    framework = MCPInspectorFramework(
        server_path=str(server_path),
        timeout=60,
        use_config_file=True,  # Use config file approach with --tool-arg format
    )

    arguments = {
        "api_operation": "ListClusters"  # Correct format for ecs_resource_management tool
    }

    result = framework.call_tool("ecs_resource_management", arguments)

    print(f"Tool call success: {result.success}")
    print(f"Tool call output: {result.stdout}")

    if result.success and result.parsed_json:
        content = result.parsed_json.get("content", [])
        if content:
            response_text = content[0].get("text", "")
            print("✅ ListClusters succeeded!")
            print(f"📋 ECS Response:\n{response_text}")

            # Parse and display cluster count
            import json

            try:
                ecs_response = json.loads(response_text)
                cluster_count = len(ecs_response.get("clusterArns", []))
                print(f"📊 Found {cluster_count} ECS clusters")
            except json.JSONDecodeError:
                print("⚠️  Could not parse ECS response as JSON")

            print(
                "📋 Server logs at: "
                "/Users/mtgoo/dev/ecs-mcp-server/mcp/src/ecs-mcp-server/logs/debug.log"
            )
            return result

    # If it failed
    print(f"❌ ListClusters failed: {result.stderr}")
    return result


if __name__ == "__main__":
    # Allow running this file directly for quick testing
    test_ecs_resource_management_list_clusters()
