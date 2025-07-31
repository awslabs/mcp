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

"""Tests for RDSContext class."""

from awslabs.rds_control_plane_mcp_server.common.context import RDSContext


class TestRDSContext:
    """Test cases for RDSContext class."""

    def test_initialize_default_values(self):
        """Test initialize with default values."""
        RDSContext.initialize()
        assert RDSContext.readonly_mode() is True
        assert RDSContext.max_items() == 100

    def test_initialize_custom_values(self):
        """Test initialize with custom values."""
        RDSContext.initialize(readonly=False, max_items=50)
        assert RDSContext.readonly_mode() is False
        assert RDSContext.max_items() == 50

    def test_get_pagination_config(self):
        """Test get_pagination_config returns correct format."""
        RDSContext.initialize(max_items=200)
        config = RDSContext.get_pagination_config()
        assert config == {'MaxItems': 200}
