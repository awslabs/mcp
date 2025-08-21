#!/usr/bin/env python3
"""
Simple test runner for ECS MCP Server integration tests.

This script can be used to run integration tests independently of pytest,
useful for debugging and development.
"""

import logging
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.integ_tests.test_ecs_mcp_inspector import TestECSMCPInspector  # noqa: E402


def main():
    """Run integration tests manually."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("Starting ECS MCP Server integration tests")

    try:
        # Initialize the test class
        TestECSMCPInspector.setup_class()
        test_instance = TestECSMCPInspector()

        # Run individual tests
        tests_to_run = [
            ("Basic Tools List", test_instance.test_list_tools_basic),
            ("Expected Tools Exist", test_instance.test_expected_ecs_tools_exist),
            ("Tools Have Descriptions", test_instance.test_tools_have_descriptions),
            ("Server Startup Time", test_instance.test_server_startup_time),
            ("Invalid Method Handling", test_instance.test_invalid_method_handling),
            ("Resources List", test_instance.test_resources_list),
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests_to_run:
            logger.info(f"\n{'=' * 50}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'=' * 50}")

            try:
                test_instance.setup_method()
                test_func()
                test_instance.teardown_method()
                logger.info(f"✅ PASSED: {test_name}")
                passed += 1
            except Exception as e:
                logger.error(f"❌ FAILED: {test_name}")
                logger.error(f"Error: {e}")
                failed += 1

        # Summary
        logger.info(f"\n{'=' * 50}")
        logger.info("TEST SUMMARY")
        logger.info(f"{'=' * 50}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Total:  {passed + failed}")

        if failed > 0:
            logger.error("Some tests failed!")
            sys.exit(1)
        else:
            logger.info("All tests passed!")

    except Exception as e:
        logger.error(f"Failed to run tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
