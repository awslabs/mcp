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

"""Tests for the main entry point."""

from unittest.mock import patch


def test_main_calls_mcp_run():
    """Verify main() calls mcp.run()."""
    with patch('awslabs.security_agent_mcp_server.server.mcp') as mock_mcp:
        from awslabs.security_agent_mcp_server.server import main

        main()
        mock_mcp.run.assert_called_once()
