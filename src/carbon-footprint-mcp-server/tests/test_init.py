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

"""Tests for package initialization."""

import awslabs.carbon_footprint_mcp_server
import importlib


class TestInit:
    """Test package initialization."""

    def test_version(self):
        """Test that version is defined."""
        assert hasattr(awslabs.carbon_footprint_mcp_server, '__version__')
        assert awslabs.carbon_footprint_mcp_server.__version__ == '0.1.0'

    def test_module_reload(self):
        """Test that module can be reloaded."""
        importlib.reload(awslabs.carbon_footprint_mcp_server)
        assert awslabs.carbon_footprint_mcp_server.__version__ == '0.1.0'
