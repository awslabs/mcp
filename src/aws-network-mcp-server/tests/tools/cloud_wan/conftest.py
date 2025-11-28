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

"""Centralized test fixtures for Cloud WAN tests."""

import pytest
from botocore.client import BaseClient
from unittest.mock import MagicMock


@pytest.fixture
def mock_aws_client(monkeypatch):
    """Centralized AWS client mock for all Cloud WAN tests.

    This fixture ensures consistent mocking behavior across all Cloud WAN tests
    by replacing the get_aws_client function with a controlled mock.
    """
    mock_client = MagicMock()  # Removed restrictive spec to allow all AWS service methods

    def get_mock_client(service_name, region_name=None, profile_name=None):
        """Return the same mock client for all service types."""
        return mock_client

    monkeypatch.setattr(
        'awslabs.aws_network_mcp_server.utils.aws_common.get_aws_client', get_mock_client
    )
    return mock_client


@pytest.fixture
def mock_network_manager_client():
    """Create a mock Network Manager client with spec."""
    return MagicMock(spec=BaseClient)


@pytest.fixture
def mock_ec2_client():
    """Create a mock EC2 client with spec."""
    return MagicMock(spec=BaseClient)


@pytest.fixture
def mock_logs_client():
    """Create a mock CloudWatch Logs client with spec."""
    return MagicMock(spec=BaseClient)
