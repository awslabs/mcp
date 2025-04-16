# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the {{cookiecutter.project_domain}} MCP Server."""

import pytest
from awslabs.{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-') | replace('-', '_')}}_mcp_server.server import example_tool
from awslabs.{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-') | replace('-', '_')}}_mcp_server.server import math_tool

@pytest.mark.asyncio
async def test_example_tool():
    # Arrange
    test_query = "test query"
    expected_project_name = "awslabs {{cookiecutter.project_domain}} MCP Server"
    expected_response = f"Hello from {expected_project_name}! Your query was {test_query}. Replace this with your tool's logic"

    # Act
    result = await example_tool(test_query)

    # Assert
    assert result == expected_response

@pytest.mark.asyncio
async def test_example_tool_failure():
    # Arrange
    test_query = "test query"
    expected_project_name = "awslabs {{cookiecutter.project_domain}} MCP Server"
    expected_response = f"Hello from {expected_project_name}! Your query was {test_query}. Replace this your tool's new logic"

    # Act
    result = await example_tool(test_query)

    # Assert
    assert result != expected_response

@pytest.mark.asyncio
class TestMathTool:
    async def test_addition(self):
        # Test integer addition
        assert await math_tool('add', 2, 3) == 5
        # Test float addition
        assert await math_tool('add', 2.5, 3.5) == 6.0

    async def test_subtraction(self):
        # Test integer subtraction
        assert await math_tool('subtract', 5, 3) == 2
        # Test float subtraction
        assert await math_tool('subtract', 5.5, 2.5) == 3.0

    async def test_multiplication(self):
        # Test integer multiplication
        assert await math_tool('multiply', 4, 3) == 12
        # Test float multiplication
        assert await math_tool('multiply', 2.5, 2) == 5.0

    async def test_division(self):
        # Test integer division
        assert await math_tool('divide', 6, 2) == 3.0
        # Test float division
        assert await math_tool('divide', 5.0, 2.0) == 2.5

    async def test_division_by_zero(self):
        # Test division by zero raises ValueError
        with pytest.raises(ValueError) as exc_info:
            await math_tool('divide', 5, 0)
        assert str(exc_info.value) == 'The denominator 0 cannot be zero.'

    async def test_invalid_operation(self):
        # Test invalid operation raises ValueError
        with pytest.raises(ValueError) as exc_info:
            await math_tool('power', 2, 3)
        assert 'Invalid operation: power' in str(exc_info.value)
