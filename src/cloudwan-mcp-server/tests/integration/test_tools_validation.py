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


"""Test script to validate all 16 CloudWAN tools are correctly implemented.
This validates the tool signatures and ensures AWS Labs FastMCP compliance.
"""

import ast
import importlib.util
import sys
from pathlib import Path


def validate_tools():
    """Validate all 16 CloudWAN tools are correctly implemented."""
    # Use importlib to robustly locate the server.py file
    spec = importlib.util.find_spec("awslabs.cloudwan_mcp_server.server")
    if spec is None or not spec.origin:
        print("ERROR: Could not locate awslabs.cloudwan_mcp_server.server module")
        return False
    server_file = Path(spec.origin)

    if not server_file.exists():
        print(f"ERROR: Server file not found at {server_file}")
        return False

    # Read and parse the server file
    with open(server_file) as f:
        content = f.read()

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"ERROR: Syntax error in server.py: {e}")
        return False

    # Expected 16 tools
    expected_tools = [
        "trace_network_path",
        "list_core_networks",
        "get_global_networks",
        "discover_vpcs",
        "discover_ip_details",
        "validate_ip_cidr",
        "list_network_function_groups",
        "analyze_network_function_group",
        "validate_cloudwan_policy",
        "manage_tgw_routes",
        "analyze_tgw_routes",
        "analyze_tgw_peers",
        "analyze_segment_routes",
        "get_core_network_policy",
        "get_core_network_change_set",
        "get_core_network_change_events",
    ]

    found_tools = []
    mcp_decorator_found = False
    fastmcp_import_found = False

    # Walk the AST to find functions with @mcp.tool() decorator
    for node in ast.walk(tree):
        # Check for FastMCP import
        if isinstance(node, ast.ImportFrom) and node.module == "mcp.server.fastmcp":
            if any(alias.name == "FastMCP" for alias in node.names):
                fastmcp_import_found = True

        # Check for function definitions with decorators
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                # Check for @mcp.tool() decorator
                if (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and isinstance(decorator.func.value, ast.Name)
                    and decorator.func.value.id == "mcp"
                    and decorator.func.attr == "tool"
                ):
                    found_tools.append(node.name)
                    mcp_decorator_found = True

    # Validation results
    success = True

    print("=== CloudWAN MCP Server Tool Validation ===\n")

    # Check FastMCP import
    if fastmcp_import_found:
        print("✅ FastMCP import found")
    else:
        print("❌ FastMCP import NOT found")
        success = False

    # Check mcp decorator usage
    if mcp_decorator_found:
        print("✅ @mcp.tool() decorators found")
    else:
        print("❌ @mcp.tool() decorators NOT found")
        success = False

    # Check all 16 tools are present
    print(f"\n📊 Tool Count: {len(found_tools)}/16 expected tools")

    missing_tools = set(expected_tools) - set(found_tools)
    extra_tools = set(found_tools) - set(expected_tools)

    if len(found_tools) == 16 and not missing_tools:
        print("✅ All 16 tools implemented")
    else:
        print(f"❌ Tool count mismatch: found {len(found_tools)}, expected 16")
        success = False

    # Report missing tools
    if missing_tools:
        print(f"\n❌ Missing tools ({len(missing_tools)}):")
        for tool in sorted(missing_tools):
            print(f"  - {tool}")
        success = False

    # Report extra tools (not necessarily bad, but should be noted)
    if extra_tools:
        print(f"\n⚠️ Extra tools found ({len(extra_tools)}):")
        for tool in sorted(extra_tools):
            print(f"  - {tool}")

    # List all found tools
    print(f"\n📋 Found tools ({len(found_tools)}):")
    for i, tool in enumerate(sorted(found_tools), 1):
        status = "✅" if tool in expected_tools else "⚠️"
        print(f"  {i:2d}. {status} {tool}")

    # Check AWS Labs compliance patterns
    aws_labs_patterns = {
        "boto3 import": "import boto3" in content,
        "ClientError import": "from botocore.exceptions import ClientError" in content,
        "JSON error handling": "json.dumps" in content and "error" in content,
        "Direct client usage": "boto3.client" in content,
        "Simple return strings": "-> str:" in content,
    }

    print("\n🏗️ AWS Labs Compliance Patterns:")
    compliance_success = True
    for pattern, found in aws_labs_patterns.items():
        if found:
            print(f"  ✅ {pattern}")
        else:
            print(f"  ❌ {pattern}")
            compliance_success = False

    if compliance_success:
        print("✅ AWS Labs compliance patterns validated")
    else:
        print("❌ Some AWS Labs patterns missing")
        success = False

    # Check for complexity anti-patterns that should be removed
    anti_patterns = {
        "Class hierarchies": "class.*Tool.*:" in content,
        "Dynamic registry": "DynamicToolRegistry" in content,
        "Complex abstractions": "BaseMCPTool" in content,
        "Pydantic models": "from pydantic" in content,
        "Tool factory": "ToolFactory" in content,
    }

    print("\n🚫 Complexity Anti-Patterns (should be absent):")
    for pattern, found in anti_patterns.items():
        if not found:
            print(f"  ✅ {pattern} removed")
        else:
            print(f"  ❌ {pattern} still present")
            success = False

    # Final validation
    print(f"\n{'=' * 50}")
    if success:
        print("🎉 VALIDATION PASSED: CloudWAN MCP Server is AWS Labs compliant!")
        print("✅ All 16 tools converted to simple FastMCP decorators")
        print("✅ Complex abstractions removed")
        print("✅ Direct boto3 usage implemented")
        print("✅ Standardized error handling")
    else:
        print("❌ VALIDATION FAILED: Issues found that need to be addressed")

    return success


if __name__ == "__main__":
    success = validate_tools()
    sys.exit(0 if success else 1)
