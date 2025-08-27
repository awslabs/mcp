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

"""Unit tests for constants module."""

import os
from unittest.mock import patch


class TestConstants:
    """Test cases for constants configuration."""

    @patch.dict(os.environ, {'HEALTHOMICS_DEFAULT_MAX_RESULTS': '25'})
    def test_default_max_results_from_environment(self):
        """Test DEFAULT_MAX_RESULTS uses value from environment variable."""
        # Need to reload the module to pick up the environment variable
        import importlib
        from awslabs.aws_healthomics_mcp_server import consts

        importlib.reload(consts)

        assert consts.DEFAULT_MAX_RESULTS == 25

    @patch.dict(os.environ, {}, clear=True)
    def test_default_max_results_default_value(self):
        """Test DEFAULT_MAX_RESULTS uses default value when no environment variable."""
        # Need to reload the module to pick up the cleared environment
        import importlib
        from awslabs.aws_healthomics_mcp_server import consts

        importlib.reload(consts)

        assert consts.DEFAULT_MAX_RESULTS == 10

    @patch.dict(os.environ, {'HEALTHOMICS_DEFAULT_MAX_RESULTS': '100'})
    def test_default_max_results_custom_value(self):
        """Test DEFAULT_MAX_RESULTS uses custom value from environment."""
        # Need to reload the module to pick up the environment variable
        import importlib
        from awslabs.aws_healthomics_mcp_server import consts

        importlib.reload(consts)

        assert consts.DEFAULT_MAX_RESULTS == 100

    @patch.dict(os.environ, {'HEALTHOMICS_DEFAULT_MAX_RESULTS': 'invalid'})
    def test_default_max_results_invalid_value(self):
        """Test DEFAULT_MAX_RESULTS handles invalid environment variable value."""
        # Should fall back to default value of 10 when invalid value is provided
        import importlib
        from awslabs.aws_healthomics_mcp_server import consts

        importlib.reload(consts)

        assert consts.DEFAULT_MAX_RESULTS == 10
