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


#!/usr/bin/env python3
"""Test script to diagnose MCP response format issues"""

import json

from mcp.types import CallToolResult, TextContent


def test_basic_response() -> bool | None:
    """Test creating a basic MCP response"""
    try:
        # Create TextContent
        text_content = TextContent(type="text", text="Hello World")
        print(f"TextContent created successfully: {text_content}")

        # Create CallToolResult
        result = CallToolResult(content=[text_content])
        print(f"CallToolResult created successfully: {result}")

        # Try to serialize to JSON
        json_str = result.model_dump_json(indent=2)
        print(f"JSON serialization successful:\n{json_str}")

        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_global_networks_response() -> bool | None:
    """Test creating a global networks response like our tool does"""
    try:
        response_data = {
            "timestamp": "2025-01-01T00:00:00",
            "status": "success",
            "global_networks": [
                {"global_network_id": "global-network-test123", "description": "Test Network", "state": "AVAILABLE"}
            ],
            "total_count": 1,
        }

        # Create TextContent exactly like our tool
        text_content = TextContent(type="text", text=json.dumps(response_data, indent=2))
        print(f"TextContent created: {type(text_content)}")

        # Create CallToolResult exactly like our tool
        result = CallToolResult(content=[text_content])
        print(f"CallToolResult created: {type(result)}")

        # Check the content
        print(f"Content length: {len(result.content)}")
        print(f"Content[0] type: {type(result.content[0])}")
        print(f"Content[0]: {result.content[0]}")

        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing basic MCP response creation...")
    test_basic_response()

    print("\nTesting global networks response...")
    test_global_networks_response()
