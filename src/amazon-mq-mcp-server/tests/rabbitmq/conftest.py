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
# This file is part of the awslabs namespace.
# It is intentionally minimal to support PEP 420 namespace packages.

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_rabbitmq_connection():
    """Fixture for mocked RabbitMQ connection."""
    mock_conn = MagicMock()
    mock_channel = MagicMock()
    mock_conn.get_channel.return_value = (mock_conn, mock_channel)
    return mock_conn


@pytest.fixture
def mock_rabbitmq_admin():
    """Fixture for mocked RabbitMQ admin."""
    return MagicMock()


@pytest.fixture
def mock_mcp_server():
    """Fixture for mocked MCP server."""
    return MagicMock()
