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

"""Test cases for the detect_cloudwan_inspection tool."""

import pytest
from awslabs.aws_network_mcp_server.tools.cloud_wan.detect_cloudwan_inspection import (
    detect_cloudwan_inspection,
)
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


class TestDetectCloudwanInspection:
    """Test cases for detect_cloudwan_inspection function."""

    @patch(
        'awslabs.aws_network_mcp_server.tools.cloud_wan.detect_cloudwan_inspection.get_aws_client'
    )
    async def test_detect_cloudwan_inspection_aws_error(self, mock_get_client):
        """Test AWS API error handling."""
        mock_nm_client = MagicMock()
        mock_get_client.return_value = mock_nm_client
        mock_nm_client.get_core_network.side_effect = Exception('AccessDenied')

        with pytest.raises(ToolError):
            await detect_cloudwan_inspection(
                core_network_id='core-network-12345678', region='us-east-1'
            )
