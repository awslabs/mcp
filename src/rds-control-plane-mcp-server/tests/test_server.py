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

"""Tests for the rds-control-plane MCP Server."""

import pytest
from awslabs.rds_control_plane_mcp_server.server import example_tool, math_tool


@pytest.mark.asyncio
async def test_example_tool():
    """Test that example_tool returns the expected response for a given query.

    Verifies that the function correctly formats the project name and query
    in its response message.
    """
    # Arrange
    test_query = 'test query'
    expected_project_name = 'awslabs rds-control-plane MCP Server'
    expected_response = f"Hello from {expected_project_name}! Your query was {test_query}. Replace this with your tool's logic"

    # Act
    result = await example_tool(test_query)

    # Assert
    assert result == expected_response


@pytest.mark.asyncio
async def test_example_tool_failure():
    """Test that example_tool does not return an incorrect response.

    Ensures the function's output doesn't match an intentionally wrong
    expected response, verifying it returns the correct content.
    """
    # Arrange
    test_query = 'test query'
    expected_project_name = 'awslabs rds-control-plane MCP Server'
    expected_response = f"Hello from {expected_project_name}! Your query was {test_query}. Replace this your tool's new logic"

    # Act
    result = await example_tool(test_query)

    # Assert
    assert result != expected_response


@pytest.mark.asyncio
class TestMathTool:
    """Test suite for the math_tool function.

    Contains tests for various mathematical operations supported by the math_tool
    including addition, subtraction, multiplication, division, and error handling.
    """

    async def test_addition(self):
        """Test the addition operation of math_tool.

        Verifies that both integer and float addition work correctly.
        """
        # Test integer addition
        assert await math_tool('add', 2, 3) == 5
        # Test float addition
        assert await math_tool('add', 2.5, 3.5) == 6.0

    async def test_subtraction(self):
        """Test the subtraction operation of math_tool.

        Verifies that both integer and float subtraction work correctly.
        """
        # Test integer subtraction
        assert await math_tool('subtract', 5, 3) == 2
        # Test float subtraction
        assert await math_tool('subtract', 5.5, 2.5) == 3.0

    async def test_multiplication(self):
        """Test the multiplication operation of math_tool.

        Verifies that both integer and float multiplication work correctly.
        """
        # Test integer multiplication
        assert await math_tool('multiply', 4, 3) == 12
        # Test float multiplication
        assert await math_tool('multiply', 2.5, 2) == 5.0

    async def test_division(self):
        """Test the division operation of math_tool.

        Verifies that both integer and float division work correctly,
        confirming that division always returns a float.
        """
        # Test integer division
        assert await math_tool('divide', 6, 2) == 3.0
        # Test float division
        assert await math_tool('divide', 5.0, 2.0) == 2.5

    async def test_division_by_zero(self):
        """Test that division by zero raises a ValueError.

        Verifies that math_tool properly handles division by zero by
        raising a ValueError with an appropriate error message.
        """
        # Test division by zero raises ValueError
        with pytest.raises(ValueError) as exc_info:
            await math_tool('divide', 5, 0)
        assert str(exc_info.value) == 'The denominator 0 cannot be zero.'

    async def test_invalid_operation(self):
        """Test that an invalid operation raises a ValueError.

        Verifies that math_tool raises a ValueError with an appropriate
        error message when given an unsupported operation.
        """
        # Test invalid operation raises ValueError
        with pytest.raises(ValueError) as exc_info:
            await math_tool('power', 2, 3)
        assert 'Invalid operation: power' in str(exc_info.value)
