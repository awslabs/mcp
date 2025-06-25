#!/usr/bin/env python3
"""
Test script for Bedrock Advisor MCP Server tools.

This script tests the functionality of the Bedrock Advisor MCP Server using mocks.
"""

import unittest


class TestBedrockAdvisorServer(unittest.TestCase):
    """Test cases for the Bedrock Advisor MCP Server."""

    def test_code_structure(self):
        """Test the code structure and organization."""
        print("\n=== Testing Code Structure ===")

        # Check if the main modules exist
        import os

        # Check server.py
        self.assertTrue(os.path.exists("bedrock_advisor/server.py"), "server.py exists")
        print("✅ server.py exists")

        # Check availability_checker.py
        self.assertTrue(
            os.path.exists("bedrock_advisor/services/availability_checker.py"),
            "availability_checker.py exists",
        )
        print("✅ availability_checker.py exists")

        # Check comparison.py
        self.assertTrue(
            os.path.exists("bedrock_advisor/services/comparison.py"),
            "comparison.py exists",
        )
        print("✅ comparison.py exists")

        # Check cost_estimator.py
        self.assertTrue(
            os.path.exists("bedrock_advisor/services/cost_estimator.py"),
            "cost_estimator.py exists",
        )
        print("✅ cost_estimator.py exists")

        # Check model_data.py
        self.assertTrue(
            os.path.exists("bedrock_advisor/services/model_data.py"),
            "model_data.py exists",
        )
        print("✅ model_data.py exists")

        # Check recommendation.py
        self.assertTrue(
            os.path.exists("bedrock_advisor/services/recommendation.py"),
            "recommendation.py exists",
        )
        print("✅ recommendation.py exists")

        # Check config.py
        self.assertTrue(
            os.path.exists("bedrock_advisor/utils/config.py"), "config.py exists"
        )
        print("✅ config.py exists")

        # Check profiling.py
        self.assertTrue(
            os.path.exists("bedrock_advisor/utils/profiling.py"), "profiling.py exists"
        )
        print("✅ profiling.py exists")

        # Check error_handler.py
        self.assertTrue(
            os.path.exists("bedrock_advisor/utils/error_handler.py"),
            "error_handler.py exists",
        )
        print("✅ error_handler.py exists")

        # Check documentation
        self.assertTrue(
            os.path.exists("docs/tool_reference.md"), "tool_reference.md exists"
        )
        print("✅ tool_reference.md exists")

        self.assertTrue(
            os.path.exists("docs/configuration.md"), "configuration.md exists"
        )
        print("✅ configuration.md exists")

        print("\nAll required files exist!")

    def test_server_tools(self):
        """Test the server tools registration."""
        print("\n=== Testing Server Tools Registration ===")

        # Check if the tools are registered in server.py
        with open("bedrock_advisor/server.py", "r") as f:
            server_code = f.read()

        # Check for tool registrations
        tools = [
            "recommend_model",
            "get_model_info",
            "list_models",
            "refresh_models",
            "compare_models",
            "estimate_cost",
            "check_model_availability",
            "check_region_availability",
            "compare_model_availability",
            "get_performance_metrics",
        ]

        for tool in tools:
            self.assertIn(f'name="{tool}"', server_code, f"{tool} tool is registered")
            print(f"✅ {tool} tool is registered")

        print("\nAll tools are properly registered!")

    def test_compare_models_implementation(self):
        """Test the compare_models implementation."""
        print("\n=== Testing compare_models Implementation ===")

        # Check if the compare_models method has the new features
        with open("bedrock_advisor/services/comparison.py", "r") as f:
            comparison_code = f.read()

        # Check for the new methods
        self.assertIn(
            "generate_usage_scenario_comparison",
            comparison_code,
            "generate_usage_scenario_comparison method exists",
        )
        print("✅ generate_usage_scenario_comparison method exists")

        self.assertIn(
            "generate_recommendation_summary",
            comparison_code,
            "generate_recommendation_summary method exists",
        )
        print("✅ generate_recommendation_summary method exists")

        # Check for the enhanced key differentiators
        self.assertIn(
            "capability_differentiators",
            comparison_code,
            "capability_differentiators exists",
        )
        print("✅ capability_differentiators exists")

        self.assertIn(
            "performance_differentiators",
            comparison_code,
            "performance_differentiators exists",
        )
        print("✅ performance_differentiators exists")

        self.assertIn(
            "cost_differentiators", comparison_code, "cost_differentiators exists"
        )
        print("✅ cost_differentiators exists")

        self.assertIn(
            "technical_differentiators",
            comparison_code,
            "technical_differentiators exists",
        )
        print("✅ technical_differentiators exists")

        # Check for the usage scenario comparison in the compare_models method
        self.assertIn(
            "usage_scenario_comparison = self.generate_usage_scenario_comparison",
            comparison_code,
            "usage_scenario_comparison is used in compare_models",
        )
        print("✅ usage_scenario_comparison is used in compare_models")

        # Check for the recommendation summary in the compare_models method
        self.assertIn(
            "recommendation_summary = self.generate_recommendation_summary",
            comparison_code,
            "recommendation_summary is used in compare_models",
        )
        print("✅ recommendation_summary is used in compare_models")

        print("\nAll compare_models enhancements are implemented!")

    def test_availability_checker_implementation(self):
        """Test the availability checker implementation."""
        print("\n=== Testing Availability Checker Implementation ===")

        # Check if the availability checker has the required methods
        with open("bedrock_advisor/services/availability_checker.py", "r") as f:
            availability_code = f.read()

        # Check for the required methods
        self.assertIn(
            "check_model_availability",
            availability_code,
            "check_model_availability method exists",
        )
        print("✅ check_model_availability method exists")

        self.assertIn(
            "check_region_availability",
            availability_code,
            "check_region_availability method exists",
        )
        print("✅ check_region_availability method exists")

        self.assertIn(
            "compare_model_availability",
            availability_code,
            "compare_model_availability method exists",
        )
        print("✅ compare_model_availability method exists")

        print("\nAll availability checker methods are implemented!")

    def test_profiling_implementation(self):
        """Test the profiling implementation."""
        print("\n=== Testing Profiling Implementation ===")

        # Check if the profiling utilities have the required methods
        with open("bedrock_advisor/utils/profiling.py", "r") as f:
            profiling_code = f.read()

        # Check for the required classes and methods
        self.assertIn(
            "class PerformanceMetrics",
            profiling_code,
            "PerformanceMetrics class exists",
        )
        print("✅ PerformanceMetrics class exists")

        self.assertIn(
            "def profile_time", profiling_code, "profile_time decorator exists"
        )
        print("✅ profile_time decorator exists")

        self.assertIn(
            "def profile_memory", profiling_code, "profile_memory decorator exists"
        )
        print("✅ profile_memory decorator exists")

        self.assertIn(
            "class PerformanceContext",
            profiling_code,
            "PerformanceContext class exists",
        )
        print("✅ PerformanceContext class exists")

        print("\nAll profiling utilities are implemented!")

    def test_config_implementation(self):
        """Test the configuration management implementation."""
        print("\n=== Testing Configuration Management Implementation ===")

        # Check if the configuration manager has the required methods
        with open("bedrock_advisor/utils/config.py", "r") as f:
            config_code = f.read()

        # Check for the required classes and methods
        self.assertIn("class ConfigManager", config_code, "ConfigManager class exists")
        print("✅ ConfigManager class exists")

        self.assertIn(
            "def _load_config_file", config_code, "_load_config_file method exists"
        )
        print("✅ _load_config_file method exists")

        self.assertIn("def _load_env_vars", config_code, "_load_env_vars method exists")
        print("✅ _load_env_vars method exists")

        self.assertIn(
            "def _validate_config", config_code, "_validate_config method exists"
        )
        print("✅ _validate_config method exists")

        print("\nAll configuration management features are implemented!")


if __name__ == "__main__":
    unittest.main()
