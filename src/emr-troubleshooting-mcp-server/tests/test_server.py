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

"""Tests for the server module of the emr-troubleshooting-mcp-server."""

import pytest

from awslabs.emr_troubleshooting_mcp_server.server import main


class TestServerMain:
    """Test server main function."""

    def test_server_module_exists(self):
        """Test that server module can be imported."""
        assert callable(main)


if __name__ == '__main__':
    pytest.main([__file__])
