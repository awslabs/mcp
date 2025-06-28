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

from awslabs.prometheus_mcp_server.consts import (
    API_VERSION_PATH,
    DEFAULT_AWS_REGION,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    DEFAULT_SERVICE_NAME,
    ENV_AWS_PROFILE,
    ENV_AWS_REGION,
    ENV_LOG_LEVEL,
    SERVER_INSTRUCTIONS,
)


class TestConsts:
    """Tests for the constants defined in the consts module."""

    def test_api_version_path(self):
        """Test that API_VERSION_PATH is correctly defined."""
        assert API_VERSION_PATH == '/api/v1'
        assert isinstance(API_VERSION_PATH, str)

    def test_default_aws_region(self):
        """Test that DEFAULT_AWS_REGION is correctly defined."""
        assert DEFAULT_AWS_REGION == 'us-east-1'
        assert isinstance(DEFAULT_AWS_REGION, str)

    def test_default_max_retries(self):
        """Test that DEFAULT_MAX_RETRIES is correctly defined."""
        assert DEFAULT_MAX_RETRIES == 3
        assert isinstance(DEFAULT_MAX_RETRIES, int)
        assert DEFAULT_MAX_RETRIES > 0

    def test_default_retry_delay(self):
        """Test that DEFAULT_RETRY_DELAY is correctly defined."""
        assert DEFAULT_RETRY_DELAY == 1
        assert isinstance(DEFAULT_RETRY_DELAY, int)
        assert DEFAULT_RETRY_DELAY > 0

    def test_default_service_name(self):
        """Test that DEFAULT_SERVICE_NAME is correctly defined."""
        assert DEFAULT_SERVICE_NAME == 'aps'
        assert isinstance(DEFAULT_SERVICE_NAME, str)

    def test_env_aws_profile(self):
        """Test that ENV_AWS_PROFILE is correctly defined."""
        assert ENV_AWS_PROFILE == 'AWS_PROFILE'
        assert isinstance(ENV_AWS_PROFILE, str)

    def test_env_aws_region(self):
        """Test that ENV_AWS_REGION is correctly defined."""
        assert ENV_AWS_REGION == 'AWS_REGION'
        assert isinstance(ENV_AWS_REGION, str)

    def test_env_log_level(self):
        """Test that ENV_LOG_LEVEL is correctly defined."""
        assert ENV_LOG_LEVEL == 'FASTMCP_LOG_LEVEL'
        assert isinstance(ENV_LOG_LEVEL, str)

    def test_server_instructions(self):
        """Test that SERVER_INSTRUCTIONS is correctly defined."""
        assert isinstance(SERVER_INSTRUCTIONS, str)
        assert len(SERVER_INSTRUCTIONS) > 0
