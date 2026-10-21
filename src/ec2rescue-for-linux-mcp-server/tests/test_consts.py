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

"""Tests for the consts module."""

from awslabs.ec2rescue_for_linux_mcp_server.consts import (
    SERVER_NAME,
    SSM_DELIVERY_TIMEOUT_SECONDS,
    SSM_DOCUMENT_NAME,
    SSM_EXECUTION_TIMEOUT_SECONDS,
    SSM_POLL_DEADLINE_SECONDS,
    SSM_POLL_INTERVAL_SECONDS,
)


class TestSsmConstants:
    """Tests for SSM configuration constants."""

    def test_document_name(self):
        """Document name is AWS-RunShellScript."""
        assert SSM_DOCUMENT_NAME == 'AWS-RunShellScript'

    def test_timeouts_are_positive(self):
        """SSM delivery/execution/poll timeouts are positive."""
        assert SSM_DELIVERY_TIMEOUT_SECONDS > 0
        assert SSM_EXECUTION_TIMEOUT_SECONDS > 0
        assert SSM_POLL_DEADLINE_SECONDS > 0

    def test_poll_interval_is_positive(self):
        """Poll interval is positive."""
        assert SSM_POLL_INTERVAL_SECONDS > 0


class TestServerMetadata:
    """Tests for server metadata constants."""

    def test_server_name(self):
        """Server name matches expected value."""
        assert SERVER_NAME == 'awslabs.ec2rescue-for-linux-mcp-server'
