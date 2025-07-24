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

"""Unit tests for the resources/__init__.py module."""

import pytest
import unittest
from awslabs.aws_msk_mcp_server.resources import register_resources
from unittest.mock import AsyncMock, MagicMock, patch


class TestResourcesInit(unittest.TestCase):
    """Tests for the resources/__init__.py module."""

    @pytest.mark.asyncio
    async def test_register_resources(self):
        """Test that register_resources calls the appropriate registration functions."""
        # Create a mock MCP instance
        mock_mcp = MagicMock()

        # Create mock registration functions
        with (
            patch(
                'awslabs.aws_msk_mcp_server.resources.register_dev_guide', new_callable=AsyncMock
            ) as mock_register_dev_guide,
            patch(
                'awslabs.aws_msk_mcp_server.resources.register_best_practices',
                new_callable=AsyncMock,
            ) as mock_register_best_practices,
        ):
            # Call the function under test
            await register_resources(mock_mcp)

            # Verify that both registration functions were called with the mock MCP instance
            mock_register_dev_guide.assert_called_once_with(mock_mcp)
            mock_register_best_practices.assert_called_once_with(mock_mcp)


if __name__ == '__main__':
    unittest.main()
