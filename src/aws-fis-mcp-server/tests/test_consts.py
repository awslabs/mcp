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


"""Tests for constants in the AWS FIS MCP server."""

from awslabs.aws_fis_mcp_server import consts


class TestConstants:
    """Test cases for constants in the AWS FIS MCP server."""

    def test_default_values(self):
        """Test default value constants."""
        assert consts.DEFAULT_AWS_REGION == 'us-east-1'
        assert consts.DEFAULT_MAX_RESOURCES == 100

    def test_experiment_states(self):
        """Test experiment state constants."""
        assert consts.EXPERIMENT_STATE_PENDING == 'pending'
        assert consts.EXPERIMENT_STATE_INITIATING == 'initiating'
        assert consts.EXPERIMENT_STATE_RUNNING == 'running'
        assert consts.EXPERIMENT_STATE_COMPLETED == 'completed'
        assert consts.EXPERIMENT_STATE_STOPPED == 'stopped'
        assert consts.EXPERIMENT_STATE_FAILED == 'failed'

    def test_experiment_actions_mode(self):
        """Test experiment actions mode constants."""
        assert consts.EXPERIMENT_ACTION_RUN_ALL == 'run-all'

    def test_environment_variables(self):
        """Test environment variable names."""
        assert consts.ENV_AWS_REGION == 'AWS_REGION'
        assert consts.ENV_AWS_ACCESS_KEY_ID == 'AWS_ACCESS_KEY_ID'
        assert (
            consts.ENV_AWS_SECRET_ACCESS_KEY == 'AWS_SECRET_ACCESS_KEY'  # pragma: allowlist secret
        )
        assert consts.ENV_AWS_SESSION_TOKEN == 'AWS_SESSION_TOKEN'
        assert consts.ENV_FASTMCP_LOG_LEVEL == 'FASTMCP_LOG_LEVEL'

    def test_aws_service_names(self):
        """Test AWS service name constants."""
        assert consts.SERVICE_FIS == 'fis'
        assert consts.SERVICE_S3 == 's3'
        assert consts.SERVICE_RESOURCE_EXPLORER == 'resource-explorer-2'
        assert consts.SERVICE_CLOUDFORMATION == 'cloudformation'

    def test_aws_config_settings(self):
        """Test AWS configuration settings."""
        assert consts.AWS_CONFIG_SIGNATURE_VERSION == 'v4'
        assert consts.AWS_CONFIG_MAX_ATTEMPTS == 10
        assert consts.AWS_CONFIG_RETRY_MODE == 'standard'
