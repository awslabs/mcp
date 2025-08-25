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

"""Tests for the config module."""

import os
from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config import (
    AppConfig,
    AWSConfig,
    LoggingConfig,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.consts import (
    AWS_REGION,
    DEFAULT_LOG_LEVEL,
    ENV_ROLE_ARN,
    ENV_S3_BUCKET,
)
from unittest.mock import patch


class TestAWSConfig:
    """Tests for the AWSConfig class."""

    def test_from_env_with_defaults(self):
        """Test creating AWSConfig from environment with defaults."""
        # Execute
        config = AWSConfig.from_env()

        # Verify
        assert config.region == AWS_REGION
        assert config.s3_bucket is None
        assert config.role_arn is None
        assert config.profile is None

    def test_from_env_with_custom_values(self):
        """Test creating AWSConfig from environment with custom values."""
        # Setup
        env_vars = {
            'AWS_REGION': 'us-west-2',
            ENV_S3_BUCKET: 'test-bucket',
            ENV_ROLE_ARN: 'test-role-arn',
            'AWS_PROFILE': 'test-profile',
        }

        # Execute
        with (
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config.AWS_REGION',
                'us-west-2',
            ),
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config.S3_BUCKET_NAME',
                'test-bucket',
            ),
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config.ROLE_ARN',
                'test-role-arn',
            ),
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config.AWS_PROFILE',
                'test-profile',
            ),
        ):
            with patch.dict('os.environ', env_vars):
                config = AWSConfig.from_env()

        # Verify
        assert config.region == 'us-west-2'
        assert config.s3_bucket == 'test-bucket'
        assert config.role_arn == 'test-role-arn'
        assert config.profile == 'test-profile'


class TestLoggingConfig:
    """Tests for the LoggingConfig class."""

    def test_from_env_with_defaults(self):
        """Test creating LoggingConfig from environment with defaults."""
        # Execute
        config = LoggingConfig.from_env()

        # Verify
        assert config.level == DEFAULT_LOG_LEVEL

    def test_from_env_with_custom_values(self):
        """Test creating LoggingConfig from environment with custom values."""
        # Setup
        env_vars = {
            'FASTMCP_LOG_LEVEL': 'DEBUG',
        }

        # Execute
        with (
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config.LOG_LEVEL',
                'DEBUG',
            ),
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config.LOG_FORMAT',
                'abcd',
            ),
        ):
            with patch.dict(os.environ, env_vars, clear=True):
                config = LoggingConfig.from_env()

        # Verify
        assert config.level == 'DEBUG'
        assert config.format == 'abcd'


class TestAppConfig:
    """Tests for the AppConfig class."""

    def test_from_env_with_defaults(self):
        """Test creating AppConfig from environment with defaults."""
        # Setup
        env_vars = {}

        # Execute
        with patch.dict(os.environ, env_vars, clear=True):
            config = AppConfig.from_env()

        # Verify
        assert config.aws_config.region == AWS_REGION
        assert config.aws_config.s3_bucket is None
        assert config.aws_config.role_arn is None
        assert config.aws_config.profile is None
        assert config.logging_config.level == DEFAULT_LOG_LEVEL
        assert config.allow_write is False

    def test_from_env_with_custom_values(self):
        """Test creating AppConfig from environment with custom values."""
        # Setup
        with (
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config.AWS_REGION',
                'us-west-2',
            ),
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config.S3_BUCKET_NAME',
                'test-bucket',
            ),
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config.ROLE_ARN',
                'test-role-arn',
            ),
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config.AWS_PROFILE',
                'test-profile',
            ),
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config.LOG_LEVEL',
                'DEBUG',
            ),
        ):
            # Execute
            config = AppConfig.from_env(allow_write=True)

            # Verify
            assert config.aws_config.region == 'us-west-2'
            assert config.aws_config.s3_bucket == 'test-bucket'
            assert config.aws_config.role_arn == 'test-role-arn'
            assert config.aws_config.profile == 'test-profile'
            assert config.logging_config.level == 'DEBUG'
            assert config.allow_write is True
