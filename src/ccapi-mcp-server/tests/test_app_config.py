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
"""Tests for app config."""

import os
import pytest
from awslabs.ccapi_mcp_server.config import AppConfig
from pydantic import ValidationError
from unittest.mock import patch


class TestAppConfig:
    """Test AppConfig settings."""

    @patch.dict(
        os.environ,
        {
            'HOST': '0.0.0.0',
            'PORT': '9000',
            'TRANSPORT': 'streamable-http',
            'FASTMCP_LOG_LEVEL': 'DEBUG',
        },
        clear=True,
    )
    def test_env_var_overrides(self):
        """Ensure environment variables override default values."""
        config = AppConfig()
        assert config.HOST == '0.0.0.0'
        assert config.PORT == 9000
        assert config.TRANSPORT == 'streamable-http'
        assert config.FASTMCP_LOG_LEVEL == 'DEBUG'

    @patch.dict(os.environ, {'TRANSPORT': 'invalid-transport'}, clear=True)
    def test_invalid_transport(self):
        """Ensure invalid transport raises a validation error."""
        with pytest.raises(ValidationError):
            AppConfig()

    @patch.dict(os.environ, {'FASTMCP_LOG_LEVEL': 'VERBOSE'}, clear=True)
    def test_invalid_log_level(self):
        """Ensure invalid log level raises a validation error."""
        with pytest.raises(ValidationError):
            AppConfig()
