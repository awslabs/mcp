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

"""Tests for the CUSTOM_TAGS environment variable functionality."""

import os
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.consts import (
    CUSTOM_TAGS_ENV_VAR,
    MCP_MANAGED_TAG_KEY,
    MCP_MANAGED_TAG_VALUE,
    MCP_RESOURCE_TYPE_TAG_KEY,
)
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestCustomTags:
    """Tests for the CUSTOM_TAGS environment variable functionality."""

    def test_is_custom_tags_enabled_true(self):
        """Test that is_custom_tags_enabled returns True when CUSTOM_TAGS is set to 'true'."""
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            assert AwsHelper.is_custom_tags_enabled() is True

    def test_is_custom_tags_enabled_false(self):
        """Test that is_custom_tags_enabled returns False when CUSTOM_TAGS is not set to 'true'."""
        # Test with CUSTOM_TAGS set to something other than 'true'
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'false'}):
            assert AwsHelper.is_custom_tags_enabled() is False

        # Test with CUSTOM_TAGS not set
        with patch.dict(os.environ, {}, clear=True):
            assert AwsHelper.is_custom_tags_enabled() is False

    def test_prepare_resource_tags_with_custom_tags_enabled(self):
        """Test that prepare_resource_tags respects CUSTOM_TAGS when enabled."""
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Test with no additional tags
            tags = AwsHelper.prepare_resource_tags('TestResource')
            assert tags == {}
            assert MCP_MANAGED_TAG_KEY not in tags
            assert MCP_RESOURCE_TYPE_TAG_KEY not in tags

            # Test with additional tags
            additional_tags = {'tag1': 'value1', 'tag2': 'value2'}
            tags = AwsHelper.prepare_resource_tags('TestResource', additional_tags)
            assert tags == additional_tags
            assert MCP_MANAGED_TAG_KEY not in tags
            assert MCP_RESOURCE_TYPE_TAG_KEY not in tags

    def test_prepare_resource_tags_with_custom_tags_disabled(self):
        """Test that prepare_resource_tags adds MCP tags when CUSTOM_TAGS is disabled."""
        with patch.dict(os.environ, {}, clear=True):
            # Mock datetime.utcnow to return a fixed time
            mock_now = datetime(2023, 1, 1, 0, 0, 0)
            with patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.datetime'
            ) as mock_datetime:
                mock_datetime.utcnow.return_value = mock_now

                # Test with no additional tags
                tags = AwsHelper.prepare_resource_tags('TestResource')
                assert tags[MCP_MANAGED_TAG_KEY] == MCP_MANAGED_TAG_VALUE
                assert tags[MCP_RESOURCE_TYPE_TAG_KEY] == 'TestResource'

                # Test with additional tags
                additional_tags = {'tag1': 'value1', 'tag2': 'value2'}
                tags = AwsHelper.prepare_resource_tags('TestResource', additional_tags)
                assert tags[MCP_MANAGED_TAG_KEY] == MCP_MANAGED_TAG_VALUE
                assert tags[MCP_RESOURCE_TYPE_TAG_KEY] == 'TestResource'
                assert tags['tag1'] == 'value1'
                assert tags['tag2'] == 'value2'

    def test_verify_resource_managed_by_mcp_with_custom_tags_enabled(self):
        """Test that verify_resource_managed_by_mcp returns True when CUSTOM_TAGS is enabled."""
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Test with empty tags
            assert AwsHelper.verify_resource_managed_by_mcp([]) is True

            # Test with tags that don't include the MCP managed tag
            tags = [{'Key': 'tag1', 'Value': 'value1'}, {'Key': 'tag2', 'Value': 'value2'}]
            assert AwsHelper.verify_resource_managed_by_mcp(tags) is True

    def test_is_resource_mcp_managed_with_custom_tags_enabled(self):
        """Test that is_resource_mcp_managed returns True when CUSTOM_TAGS is enabled."""
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Mock the Glue client
            mock_glue_client = MagicMock()

            # Test with no parameters
            assert (
                AwsHelper.is_resource_mcp_managed(
                    mock_glue_client, 'arn:aws:glue:us-west-2:123456789012:database/test-db'
                )
                is True
            )
            mock_glue_client.get_tags.assert_not_called()

            # Test with parameters
            parameters = {'some_key': 'some_value'}
            assert (
                AwsHelper.is_resource_mcp_managed(
                    mock_glue_client,
                    'arn:aws:glue:us-west-2:123456789012:database/test-db',
                    parameters=parameters,
                )
                is True
            )
            mock_glue_client.get_tags.assert_not_called()

    def test_verify_emr_cluster_managed_by_mcp_with_custom_tags_enabled(self):
        """Test that verify_emr_cluster_managed_by_mcp returns valid when CUSTOM_TAGS is enabled."""
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Mock the EMR client
            mock_emr_client = MagicMock()

            # Test with any cluster ID
            result = AwsHelper.verify_emr_cluster_managed_by_mcp(
                mock_emr_client, 'j-12345ABCDEF', 'EMRCluster'
            )

            # Verify the result
            assert result['is_valid'] is True
            assert result['error_message'] is None
            mock_emr_client.describe_cluster.assert_not_called()

    def test_verify_athena_data_catalog_managed_by_mcp_with_custom_tags_enabled(self):
        """Test that verify_athena_data_catalog_managed_by_mcp returns valid when CUSTOM_TAGS is enabled."""
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Mock the Athena client
            mock_athena_client = MagicMock()

            # Test with any data catalog name
            result = AwsHelper.verify_athena_data_catalog_managed_by_mcp(
                mock_athena_client, 'test-catalog'
            )

            # Verify the result
            assert result['is_valid'] is True
            assert result['error_message'] is None
            mock_athena_client.get_data_catalog.assert_not_called()
            mock_athena_client.list_tags_for_resource.assert_not_called()
