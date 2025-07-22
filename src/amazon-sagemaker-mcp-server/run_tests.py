#!/usr/bin/env python3
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

"""Test runner script for Amazon SageMaker MCP Server."""

import argparse
import subprocess
import sys
from pathlib import Path


def run_tests(test_type="all", verbose=False, coverage=False):
    """Run tests with specified options."""
    # Get the project root directory
    project_root = Path(__file__).parent
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test directory
    if test_type == "all":
        cmd.append("tests/")
    elif test_type == "server":
        cmd.append("tests/test_server.py")
    elif test_type == "aws_client":
        cmd.append("tests/test_aws_client.py")
    elif test_type == "permissions":
        cmd.append("tests/test_permissions.py")
    elif test_type == "utils":
        cmd.append("tests/test_utils.py")
    else:
        print(f"Unknown test type: {test_type}")
        return 1
    
    # Add verbose flag
    if verbose:
        cmd.append("-v")
    
    # Add coverage
    if coverage:
        cmd.extend([
            "--cov=awslabs.amazon_sagemaker_mcp_server",
            "--cov-report=term-missing",
            "--cov-report=html"
        ])
    
    # Add other useful flags
    cmd.extend([
        "--tb=short",  # Shorter traceback format
        "-x",          # Stop on first failure
    ])
    
    print(f"Running command: {' '.join(cmd)}")
    print(f"Working directory: {project_root}")
    
    # Run the tests
    try:
        result = subprocess.run(cmd, cwd=project_root, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run tests for Amazon SageMaker MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --type server      # Run only server tests
  python run_tests.py --verbose          # Run with verbose output
  python run_tests.py --coverage         # Run with coverage report
  python run_tests.py --type utils -v    # Run utils tests with verbose output
        """
    )
    
    parser.add_argument(
        "--type", "-t",
        choices=["all", "server", "aws_client", "permissions", "utils"],
        default="all",
        help="Type of tests to run (default: all)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Run tests with verbose output"
    )
    
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run tests with coverage report"
    )
    
    args = parser.parse_args()
    
    # Run the tests
    exit_code = run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
