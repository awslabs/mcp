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

"""Tests for the AwsHelper class."""

import os
from awslabs.aws_dataprocessing_mcp_server import __version__
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.consts import (
    MCP_CREATION_TIME_TAG_KEY,
    MCP_MANAGED_TAG_KEY,
    MCP_MANAGED_TAG_VALUE,
    MCP_RESOURCE_TYPE_TAG_KEY,
)
from botocore.config import Config
from botocore.exceptions import ClientError
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestAwsHelper:
    """Tests for the AwsHelper class."""

    def setup_method(self):
        """Reset the cached AWS account ID and partition before each test."""
        # Reset the cached AWS account ID and partition
        AwsHelper._aws_account_id = None
        AwsHelper._aws_partition = None

    def test_get_aws_region_with_env_var(self):
        """Test that get_aws_region returns the region from the environment variable."""
        with patch.dict(os.environ, {'AWS_REGION': 'us-west-2'}):
            assert AwsHelper.get_aws_region() == 'us-west-2'

    def test_get_aws_region_without_env_var(self):
        """Test that get_aws_region returns None when the environment variable is not set."""
        with patch.dict(os.environ, {}, clear=True):
            assert AwsHelper.get_aws_region() == 'us-east-1'

    def test_get_aws_profile_with_env_var(self):
        """Test that get_aws_profile returns the profile from the environment variable."""
        with patch.dict(os.environ, {'AWS_PROFILE': 'test-profile'}):
            assert AwsHelper.get_aws_profile() == 'test-profile'

    def test_get_aws_profile_without_env_var(self):
        """Test that get_aws_profile returns None when the environment variable is not set."""
        with patch.dict(os.environ, {}, clear=True):
            assert AwsHelper.get_aws_profile() is None

    def test_get_aws_account_id_cached(self):
        """Test that get_aws_account_id returns the cached account ID if available."""
        # Set the cached account ID
        AwsHelper._aws_account_id = '123456789012'

        # Verify that the cached account ID is returned without calling STS
        with patch('boto3.client') as mock_boto3_client:
            account_id = AwsHelper.get_aws_account_id()
            assert account_id == '123456789012'
            mock_boto3_client.assert_not_called()

    def test_get_aws_account_id_uncached(self):
        """Test that get_aws_account_id calls STS when the account ID is not cached."""
        # Mock the STS client
        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.return_value = {'Account': '123456789012'}

        # Mock boto3.client to return our mock STS client
        with patch('boto3.client', return_value=mock_sts_client) as mock_boto3_client:
            account_id = AwsHelper.get_aws_account_id()
            assert account_id == '123456789012'
            mock_boto3_client.assert_called_once_with('sts')
            mock_sts_client.get_caller_identity.assert_called_once()

        # Verify that the account ID is now cached
        assert AwsHelper._aws_account_id == '123456789012'

    def test_get_aws_account_id_exception(self):
        """Test that get_aws_account_id returns a placeholder when STS call fails."""
        # Mock the STS client to raise an exception
        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.side_effect = Exception('STS error')

        # Mock boto3.client to return our mock STS client
        with patch('boto3.client', return_value=mock_sts_client) as mock_boto3_client:
            account_id = AwsHelper.get_aws_account_id()
            assert account_id == 'current-account'
            mock_boto3_client.assert_called_once_with('sts')
            mock_sts_client.get_caller_identity.assert_called_once()

        # Verify that the account ID is not cached
        assert AwsHelper._aws_account_id is None

    def test_get_aws_partition_cached(self):
        """Test that get_aws_partition returns the cached partition if available."""
        # Set the cached partition
        AwsHelper._aws_partition = 'aws'

        # Verify that the cached partition is returned without calling STS
        with patch('boto3.client') as mock_boto3_client:
            partition = AwsHelper.get_aws_partition()
            assert partition == 'aws'
            mock_boto3_client.assert_not_called()

    def test_get_aws_partition_uncached(self):
        """Test that get_aws_partition calls STS when the partition is not cached."""
        # Mock the STS client
        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.return_value = {
            'Arn': 'arn:aws:sts::123456789012:assumed-role/role-name/session-name'
        }

        # Mock boto3.client to return our mock STS client
        with patch('boto3.client', return_value=mock_sts_client) as mock_boto3_client:
            partition = AwsHelper.get_aws_partition()
            assert partition == 'aws'
            mock_boto3_client.assert_called_once_with('sts')
            mock_sts_client.get_caller_identity.assert_called_once()

        # Verify that the partition is now cached
        assert AwsHelper._aws_partition == 'aws'

    def test_get_aws_partition_exception(self):
        """Test that get_aws_partition returns the default partition when STS call fails."""
        # Mock the STS client to raise an exception
        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.side_effect = Exception('STS error')

        # Mock boto3.client to return our mock STS client
        with patch('boto3.client', return_value=mock_sts_client) as mock_boto3_client:
            partition = AwsHelper.get_aws_partition()
            assert partition == 'aws'
            mock_boto3_client.assert_called_once_with('sts')
            mock_sts_client.get_caller_identity.assert_called_once()

        # Verify that the partition is not cached
        assert AwsHelper._aws_partition is None

    def test_create_boto3_client_with_region(self):
        """Test that create_boto3_client creates a client with the specified region."""
        # Mock boto3.client
        mock_client = MagicMock()
        with patch('boto3.client', return_value=mock_client) as mock_boto3_client:
            client = AwsHelper.create_boto3_client('s3', region_name='us-west-2')
            assert client == mock_client
            mock_boto3_client.assert_called_once()
            # Verify that the region was passed
            args, kwargs = mock_boto3_client.call_args
            assert kwargs['region_name'] == 'us-west-2'
            # Verify that the config was passed with the user agent suffix
            assert isinstance(kwargs['config'], Config)
            assert (
                kwargs['config'].user_agent_extra
                == f'awslabs/mcp/aws-dataprocessing-mcp-server/{__version__}'
            )

    def test_create_boto3_client_with_env_region(self):
        """Test that create_boto3_client uses the region from the environment if not specified."""
        # Mock boto3.client
        mock_client = MagicMock()
        with patch('boto3.client', return_value=mock_client) as mock_boto3_client:
            with patch.dict(os.environ, {'AWS_REGION': 'us-east-1'}):
                client = AwsHelper.create_boto3_client('s3')
                assert client == mock_client
                mock_boto3_client.assert_called_once()
                # Verify that the region was passed from the environment
                args, kwargs = mock_boto3_client.call_args
                assert kwargs['region_name'] == 'us-east-1'

    def test_create_boto3_client_with_profile(self):
        """Test that create_boto3_client creates a client with the specified profile."""
        # Mock boto3.Session
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        with patch('boto3.Session', return_value=mock_session) as mock_boto3_session:
            with patch.dict(os.environ, {'AWS_PROFILE': 'test-profile'}):
                client = AwsHelper.create_boto3_client('s3')
                assert client == mock_client
                mock_boto3_session.assert_called_once_with(profile_name='test-profile')
                mock_session.client.assert_called_once()
                # Verify that the config was passed with the user agent suffix
                args, kwargs = mock_session.client.call_args
                assert isinstance(kwargs['config'], Config)
                assert (
                    kwargs['config'].user_agent_extra
                    == f'awslabs/mcp/aws-dataprocessing-mcp-server/{__version__}'
                )

    def test_create_boto3_client_with_profile_and_region(self):
        """Test that create_boto3_client creates a client with both profile and region."""
        # Mock boto3.Session
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        with patch('boto3.Session', return_value=mock_session) as mock_boto3_session:
            with patch.dict(os.environ, {'AWS_PROFILE': 'test-profile'}):
                client = AwsHelper.create_boto3_client('s3', region_name='us-west-2')
                assert client == mock_client
                mock_boto3_session.assert_called_once_with(profile_name='test-profile')
                mock_session.client.assert_called_once()
                # Verify that the region was passed
                args, kwargs = mock_session.client.call_args
                assert kwargs['region_name'] == 'us-west-2'

    def test_create_boto3_client_without_region(self):
        """Test that create_boto3_client works when no region is specified or in environment."""
        # Mock boto3.client
        mock_client = MagicMock()
        with patch('boto3.client', return_value=mock_client) as mock_boto3_client:
            with patch.dict(os.environ, {}, clear=True):
                with patch.object(AwsHelper, 'get_aws_region', return_value=None):
                    client = AwsHelper.create_boto3_client('s3')
                    assert client == mock_client
                    mock_boto3_client.assert_called_once()
                    # Verify that no region was passed
                    args, kwargs = mock_boto3_client.call_args
                    assert 'region_name' not in kwargs or kwargs['region_name'] is None

    def test_create_boto3_client_with_profile_without_region(self):
        """Test that create_boto3_client works with profile but no region."""
        # Mock boto3.Session
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        with patch('boto3.Session', return_value=mock_session) as mock_boto3_session:
            with patch.dict(os.environ, {'AWS_PROFILE': 'test-profile'}, clear=True):
                with patch.object(AwsHelper, 'get_aws_region', return_value=None):
                    client = AwsHelper.create_boto3_client('s3')
                    assert client == mock_client
                    mock_boto3_session.assert_called_once_with(profile_name='test-profile')
                    mock_session.client.assert_called_once()
                    # Verify that no region was passed
                    args, kwargs = mock_session.client.call_args
                    assert 'region_name' not in kwargs

    def test_prepare_resource_tags(self):
        """Test that prepare_resource_tags returns the correct tags."""
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
            assert tags[MCP_CREATION_TIME_TAG_KEY] == '2023-01-01T00:00:00'

            # Test with additional tags
            additional_tags = {'tag1': 'value1', 'tag2': 'value2'}
            tags = AwsHelper.prepare_resource_tags('TestResource', additional_tags)
            assert tags[MCP_MANAGED_TAG_KEY] == MCP_MANAGED_TAG_VALUE
            assert tags[MCP_RESOURCE_TYPE_TAG_KEY] == 'TestResource'
            assert tags[MCP_CREATION_TIME_TAG_KEY] == '2023-01-01T00:00:00'
            assert tags['tag1'] == 'value1'
            assert tags['tag2'] == 'value2'

    def test_convert_tags_to_aws_format_key_value(self):
        """Test that convert_tags_to_aws_format correctly formats tags in key_value format."""
        # Test with key_value format (default)
        tags = {'tag1': 'value1', 'tag2': 'value2'}
        formatted_tags = AwsHelper.convert_tags_to_aws_format(tags)

        # Verify the format
        assert len(formatted_tags) == 2
        assert {'Key': 'tag1', 'Value': 'value1'} in formatted_tags
        assert {'Key': 'tag2', 'Value': 'value2'} in formatted_tags

    def test_convert_tags_to_aws_format_tag_key_value(self):
        """Test that convert_tags_to_aws_format correctly formats tags in tag_key_value format."""
        # Test with tag_key_value format
        tags = {'tag1': 'value1', 'tag2': 'value2'}
        formatted_tags = AwsHelper.convert_tags_to_aws_format(tags, format_type='tag_key_value')

        # Verify the format
        assert len(formatted_tags) == 2
        assert {'TagKey': 'tag1', 'TagValue': 'value1'} in formatted_tags
        assert {'TagKey': 'tag2', 'TagValue': 'value2'} in formatted_tags

    def test_get_resource_tags_athena_workgroup_success(self):
        """Test that get_resource_tags_athena_workgroup returns tags when successful."""
        # Mock the Athena client
        mock_athena_client = MagicMock()
        mock_athena_client.list_tags_for_resource.return_value = {
            'Tags': [{'Key': 'tag1', 'Value': 'value1'}, {'Key': 'tag2', 'Value': 'value2'}]
        }

        # Mock the AWS account ID and region
        with patch.object(AwsHelper, 'get_aws_account_id', return_value='123456789012'):
            with patch.object(AwsHelper, 'get_aws_region', return_value='us-west-2'):
                # Test with a workgroup name
                tags = AwsHelper.get_resource_tags_athena_workgroup(
                    mock_athena_client, 'test-workgroup'
                )

                # Verify the result
                assert len(tags) == 2
                assert {'Key': 'tag1', 'Value': 'value1'} in tags
                assert {'Key': 'tag2', 'Value': 'value2'} in tags

                # Verify the ARN was constructed correctly
                mock_athena_client.list_tags_for_resource.assert_called_once_with(
                    ResourceARN='arn:aws:athena:us-west-2:123456789012:workgroup/test-workgroup'
                )

    def test_get_resource_tags_athena_workgroup_client_error(self):
        """Test that get_resource_tags_athena_workgroup returns empty list on ClientError."""
        # Mock the Athena client to raise a ClientError
        mock_athena_client = MagicMock()
        mock_athena_client.list_tags_for_resource.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'ListTagsForResource',
        )

        # Test with a workgroup name
        tags = AwsHelper.get_resource_tags_athena_workgroup(mock_athena_client, 'test-workgroup')

        # Verify the result is an empty list
        assert tags == []
        mock_athena_client.list_tags_for_resource.assert_called_once()

    def test_verify_resource_managed_by_mcp_key_value_true(self):
        """Test that verify_resource_managed_by_mcp returns True when the resource is managed (key_value format)."""
        # Test with key_value format (default) and managed resource
        tags = [
            {'Key': MCP_MANAGED_TAG_KEY, 'Value': MCP_MANAGED_TAG_VALUE},
            {'Key': 'tag2', 'Value': 'value2'},
        ]

        result = AwsHelper.verify_resource_managed_by_mcp(tags)
        assert result is True

    def test_verify_resource_managed_by_mcp_key_value_false(self):
        """Test that verify_resource_managed_by_mcp returns False when the resource is not managed (key_value format)."""
        # Test with key_value format (default) and unmanaged resource
        tags = [
            {'Key': MCP_MANAGED_TAG_KEY, 'Value': 'wrong-value'},
            {'Key': 'tag2', 'Value': 'value2'},
        ]

        result = AwsHelper.verify_resource_managed_by_mcp(tags)
        assert result is False

    def test_verify_resource_managed_by_mcp_tag_key_value_true(self):
        """Test that verify_resource_managed_by_mcp returns True when the resource is managed (tag_key_value format)."""
        # Test with tag_key_value format and managed resource
        tags = [
            {'TagKey': MCP_MANAGED_TAG_KEY, 'TagValue': MCP_MANAGED_TAG_VALUE},
            {'TagKey': 'tag2', 'TagValue': 'value2'},
        ]

        result = AwsHelper.verify_resource_managed_by_mcp(tags, tag_format='tag_key_value')
        assert result is True

    def test_verify_resource_managed_by_mcp_tag_key_value_false(self):
        """Test that verify_resource_managed_by_mcp returns False when the resource is not managed (tag_key_value format)."""
        # Test with tag_key_value format and unmanaged resource
        tags = [
            {'TagKey': MCP_MANAGED_TAG_KEY, 'TagValue': 'wrong-value'},
            {'TagKey': 'tag2', 'TagValue': 'value2'},
        ]

        result = AwsHelper.verify_resource_managed_by_mcp(tags, tag_format='tag_key_value')
        assert result is False

    def test_verify_resource_managed_by_mcp_empty_tags(self):
        """Test that verify_resource_managed_by_mcp returns False when tags are empty."""
        # Test with empty tags
        result = AwsHelper.verify_resource_managed_by_mcp([])
        assert result is False

    def test_verify_resource_managed_by_mcp_missing_tag(self):
        """Test that verify_resource_managed_by_mcp returns False when the MCP managed tag is missing."""
        # Test with tags that don't include the MCP managed tag
        tags = [{'Key': 'tag1', 'Value': 'value1'}, {'Key': 'tag2', 'Value': 'value2'}]

        result = AwsHelper.verify_resource_managed_by_mcp(tags)
        assert result is False

    def test_get_resource_tags_glue_job(self):
        """Test that get_resource_tags_glue_job returns the correct tags."""
        mock_glue_client = MagicMock()
        mock_glue_client.get_tags.return_value = {
            'Tags': {MCP_MANAGED_TAG_KEY: MCP_MANAGED_TAG_VALUE}
        }

        result = AwsHelper.get_resource_tags_glue_job(mock_glue_client, 'jobname')
        assert result[MCP_MANAGED_TAG_KEY] == MCP_MANAGED_TAG_VALUE

    def test_get_resource_tags_for_untagged_glue_job(self):
        """Test that get_resource_tags_glue_job returns an empty dict when get-tags returns no tags."""
        mock_glue_client = MagicMock()
        mock_glue_client.get_tags.return_value = {'Tags': {}}

        result = AwsHelper.get_resource_tags_glue_job(mock_glue_client, 'jobname')
        assert len(result) == 0

    def test_get_resource_tags_for_glue_job_client_error(self):
        """Test that get_resource_tags_glue_job returns an empty dict when get-tags returns a ClientError."""
        mock_glue_client = MagicMock()
        mock_glue_client.get_tags.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'GetTags',
        )

        result = AwsHelper.get_resource_tags_glue_job(mock_glue_client, 'jobname')
        assert len(result) == 0

    def test_is_resource_mcp_managed_with_tags(self):
        """Test that is_resource_mcp_managed returns True when the resource has the MCP managed tag."""
        # Mock the Glue client
        mock_glue_client = MagicMock()
        mock_glue_client.get_tags.return_value = {
            'Tags': {MCP_MANAGED_TAG_KEY: MCP_MANAGED_TAG_VALUE}
        }

        # Test with a resource that has the MCP managed tag
        result = AwsHelper.is_resource_mcp_managed(
            mock_glue_client, 'arn:aws:glue:us-west-2:123456789012:database/test-db'
        )
        assert result is True
        mock_glue_client.get_tags.assert_called_once_with(
            ResourceArn='arn:aws:glue:us-west-2:123456789012:database/test-db'
        )

    def test_is_resource_mcp_managed_without_tags(self):
        """Test that is_resource_mcp_managed returns False when the resource doesn't have the MCP managed tag."""
        # Mock the Glue client
        mock_glue_client = MagicMock()
        mock_glue_client.get_tags.return_value = {'Tags': {}}

        # Test with a resource that doesn't have the MCP managed tag
        result = AwsHelper.is_resource_mcp_managed(
            mock_glue_client, 'arn:aws:glue:us-west-2:123456789012:database/test-db'
        )
        assert result is False
        mock_glue_client.get_tags.assert_called_once_with(
            ResourceArn='arn:aws:glue:us-west-2:123456789012:database/test-db'
        )

    def test_is_resource_mcp_managed_with_parameters(self):
        """Test that is_resource_mcp_managed checks parameters when tag check fails."""
        # Mock the Glue client to raise an exception when getting tags
        mock_glue_client = MagicMock()
        mock_glue_client.get_tags.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'GetTags',
        )

        # Test with parameters that have the MCP managed tag
        parameters = {MCP_MANAGED_TAG_KEY: MCP_MANAGED_TAG_VALUE}
        result = AwsHelper.is_resource_mcp_managed(
            mock_glue_client,
            'arn:aws:glue:us-west-2:123456789012:database/test-db',
            parameters=parameters,
        )
        assert result is True
        mock_glue_client.get_tags.assert_called_once()

    def test_is_resource_mcp_managed_without_parameters(self):
        """Test that is_resource_mcp_managed returns False when tag check fails and no parameters are provided."""
        # Mock the Glue client to raise an exception when getting tags
        mock_glue_client = MagicMock()
        mock_glue_client.get_tags.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'GetTags',
        )

        # Test without parameters
        result = AwsHelper.is_resource_mcp_managed(
            mock_glue_client, 'arn:aws:glue:us-west-2:123456789012:database/test-db'
        )
        assert result is False
        mock_glue_client.get_tags.assert_called_once()

    def test_is_resource_mcp_managed_with_parameters_not_managed(self):
        """Test that is_resource_mcp_managed returns False when parameters don't have the MCP managed tag."""
        # Mock the Glue client to raise an exception when getting tags
        mock_glue_client = MagicMock()
        mock_glue_client.get_tags.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'GetTags',
        )

        # Test with parameters that don't have the MCP managed tag
        parameters = {'some_key': 'some_value'}
        result = AwsHelper.is_resource_mcp_managed(
            mock_glue_client,
            'arn:aws:glue:us-west-2:123456789012:database/test-db',
            parameters=parameters,
        )
        assert result is False
        mock_glue_client.get_tags.assert_called_once()

    def test_verify_emr_cluster_managed_by_mcp_success(self):
        """Test that verify_emr_cluster_managed_by_mcp returns valid when the cluster is managed by MCP."""
        # Mock the EMR client
        mock_emr_client = MagicMock()
        mock_emr_client.describe_cluster.return_value = {
            'Cluster': {
                'Id': 'j-12345ABCDEF',
                'Name': 'TestCluster',
                'Status': {'State': 'RUNNING'},
                'Tags': [
                    {'Key': MCP_MANAGED_TAG_KEY, 'Value': MCP_MANAGED_TAG_VALUE},
                    {'Key': MCP_RESOURCE_TYPE_TAG_KEY, 'Value': 'EMRCluster'},
                ],
            }
        }

        # Test with a cluster that is managed by MCP
        result = AwsHelper.verify_emr_cluster_managed_by_mcp(
            mock_emr_client, 'j-12345ABCDEF', 'EMRCluster'
        )

        # Verify the result
        assert result['is_valid'] is True
        assert result['error_message'] is None
        mock_emr_client.describe_cluster.assert_called_once_with(ClusterId='j-12345ABCDEF')

    def test_verify_emr_cluster_managed_by_mcp_not_managed(self):
        """Test that verify_emr_cluster_managed_by_mcp returns invalid when the cluster is not managed by MCP."""
        # Mock the EMR client
        mock_emr_client = MagicMock()
        mock_emr_client.describe_cluster.return_value = {
            'Cluster': {
                'Id': 'j-12345ABCDEF',
                'Name': 'TestCluster',
                'Status': {'State': 'RUNNING'},
                'Tags': [
                    {'Key': 'SomeOtherTag', 'Value': 'SomeValue'},
                ],
            }
        }

        # Test with a cluster that is not managed by MCP
        result = AwsHelper.verify_emr_cluster_managed_by_mcp(
            mock_emr_client, 'j-12345ABCDEF', 'EMRCluster'
        )

        # Verify the result
        assert result['is_valid'] is False
        assert 'not managed by MCP' in result['error_message']
        mock_emr_client.describe_cluster.assert_called_once_with(ClusterId='j-12345ABCDEF')

    def test_verify_athena_data_catalog_managed_by_mcp_success(self):
        """Test that verify_athena_data_catalog_managed_by_mcp returns valid when the data catalog is managed by MCP."""
        # Mock the Athena client
        mock_athena_client = MagicMock()
        mock_athena_client.get_data_catalog.return_value = {
            'DataCatalog': {
                'Name': 'test-catalog',
                'Type': 'GLUE',
            }
        }
        mock_athena_client.list_tags_for_resource.return_value = {
            'Tags': [
                {'Key': MCP_MANAGED_TAG_KEY, 'Value': MCP_MANAGED_TAG_VALUE},
                {'Key': 'tag2', 'Value': 'value2'},
            ]
        }

        # Mock the AWS account ID, region, and partition
        with patch.object(AwsHelper, 'get_aws_account_id', return_value='123456789012'):
            with patch.object(AwsHelper, 'get_aws_region', return_value='us-west-2'):
                with patch.object(AwsHelper, 'get_aws_partition', return_value='aws'):
                    # Test with a data catalog that is managed by MCP
                    result = AwsHelper.verify_athena_data_catalog_managed_by_mcp(
                        mock_athena_client, 'test-catalog'
                    )

                    # Verify the result
                    assert result['is_valid'] is True
                    assert result['error_message'] is None
                    mock_athena_client.get_data_catalog.assert_called_once_with(
                        Name='test-catalog'
                    )
                    mock_athena_client.list_tags_for_resource.assert_called_once_with(
                        ResourceARN='arn:aws:athena:us-west-2:123456789012:datacatalog/test-catalog'
                    )

    def test_verify_athena_data_catalog_managed_by_mcp_with_workgroup(self):
        """Test that verify_athena_data_catalog_managed_by_mcp works with a workgroup specified."""
        # Mock the Athena client
        mock_athena_client = MagicMock()
        mock_athena_client.get_data_catalog.return_value = {
            'DataCatalog': {
                'Name': 'test-catalog',
                'Type': 'GLUE',
            }
        }
        mock_athena_client.list_tags_for_resource.return_value = {
            'Tags': [
                {'Key': MCP_MANAGED_TAG_KEY, 'Value': MCP_MANAGED_TAG_VALUE},
                {'Key': 'tag2', 'Value': 'value2'},
            ]
        }

        # Mock the AWS account ID, region, and partition
        with patch.object(AwsHelper, 'get_aws_account_id', return_value='123456789012'):
            with patch.object(AwsHelper, 'get_aws_region', return_value='us-west-2'):
                with patch.object(AwsHelper, 'get_aws_partition', return_value='aws'):
                    # Test with a data catalog that is managed by MCP and a workgroup
                    result = AwsHelper.verify_athena_data_catalog_managed_by_mcp(
                        mock_athena_client, 'test-catalog', work_group='test-workgroup'
                    )

                    # Verify the result
                    assert result['is_valid'] is True
                    assert result['error_message'] is None
                    mock_athena_client.get_data_catalog.assert_called_once_with(
                        Name='test-catalog', WorkGroup='test-workgroup'
                    )
                    mock_athena_client.list_tags_for_resource.assert_called_once_with(
                        ResourceARN='arn:aws:athena:us-west-2:123456789012:datacatalog/test-catalog'
                    )

    def test_verify_athena_data_catalog_managed_by_mcp_not_managed(self):
        """Test that verify_athena_data_catalog_managed_by_mcp returns invalid when the data catalog is not managed by MCP."""
        # Mock the Athena client
        mock_athena_client = MagicMock()
        mock_athena_client.get_data_catalog.return_value = {
            'DataCatalog': {
                'Name': 'test-catalog',
                'Type': 'GLUE',
            }
        }
        mock_athena_client.list_tags_for_resource.return_value = {
            'Tags': [
                {'Key': 'SomeOtherTag', 'Value': 'SomeValue'},
            ]
        }

        # Mock the AWS account ID, region, and partition
        with patch.object(AwsHelper, 'get_aws_account_id', return_value='123456789012'):
            with patch.object(AwsHelper, 'get_aws_region', return_value='us-west-2'):
                with patch.object(AwsHelper, 'get_aws_partition', return_value='aws'):
                    # Test with a data catalog that is not managed by MCP
                    result = AwsHelper.verify_athena_data_catalog_managed_by_mcp(
                        mock_athena_client, 'test-catalog'
                    )

                    # Verify the result
                    assert result['is_valid'] is False
                    assert 'not managed by MCP' in result['error_message']
                    mock_athena_client.get_data_catalog.assert_called_once_with(
                        Name='test-catalog'
                    )
                    mock_athena_client.list_tags_for_resource.assert_called_once_with(
                        ResourceARN='arn:aws:athena:us-west-2:123456789012:datacatalog/test-catalog'
                    )

    def test_verify_athena_data_catalog_managed_by_mcp_tag_error(self):
        """Test that verify_athena_data_catalog_managed_by_mcp handles errors when checking tags."""
        # Mock the Athena client
        mock_athena_client = MagicMock()
        mock_athena_client.get_data_catalog.return_value = {
            'DataCatalog': {
                'Name': 'test-catalog',
                'Type': 'GLUE',
            }
        }
        mock_athena_client.list_tags_for_resource.side_effect = Exception('Error listing tags')

        # Mock the AWS account ID, region, and partition
        with patch.object(AwsHelper, 'get_aws_account_id', return_value='123456789012'):
            with patch.object(AwsHelper, 'get_aws_region', return_value='us-west-2'):
                with patch.object(AwsHelper, 'get_aws_partition', return_value='aws'):
                    # Test with an error when checking tags
                    result = AwsHelper.verify_athena_data_catalog_managed_by_mcp(
                        mock_athena_client, 'test-catalog'
                    )

                    # Verify the result
                    assert result['is_valid'] is False
                    assert 'Error checking data catalog tags' in result['error_message']
                    mock_athena_client.get_data_catalog.assert_called_once_with(
                        Name='test-catalog'
                    )
                    mock_athena_client.list_tags_for_resource.assert_called_once_with(
                        ResourceARN='arn:aws:athena:us-west-2:123456789012:datacatalog/test-catalog'
                    )

    def test_verify_athena_data_catalog_managed_by_mcp_get_error(self):
        """Test that verify_athena_data_catalog_managed_by_mcp handles errors when getting the data catalog."""
        # Mock the Athena client to raise an exception
        mock_athena_client = MagicMock()
        mock_athena_client.get_data_catalog.side_effect = Exception('Data catalog not found')

        # Test with an error when getting the data catalog
        result = AwsHelper.verify_athena_data_catalog_managed_by_mcp(
            mock_athena_client, 'nonexistent-catalog'
        )

        # Verify the result
        assert result['is_valid'] is False
        assert 'Error getting data catalog' in result['error_message']
        mock_athena_client.get_data_catalog.assert_called_once_with(Name='nonexistent-catalog')
        mock_athena_client.list_tags_for_resource.assert_not_called()

    def test_verify_emr_cluster_managed_by_mcp_wrong_type(self):
        """Test that verify_emr_cluster_managed_by_mcp returns invalid when the cluster has the wrong resource type."""
        # Mock the EMR client
        mock_emr_client = MagicMock()
        mock_emr_client.describe_cluster.return_value = {
            'Cluster': {
                'Id': 'j-12345ABCDEF',
                'Name': 'TestCluster',
                'Status': {'State': 'RUNNING'},
                'Tags': [
                    {'Key': MCP_MANAGED_TAG_KEY, 'Value': MCP_MANAGED_TAG_VALUE},
                    {'Key': MCP_RESOURCE_TYPE_TAG_KEY, 'Value': 'WrongType'},
                ],
            }
        }

        # Test with a cluster that has the wrong resource type
        result = AwsHelper.verify_emr_cluster_managed_by_mcp(
            mock_emr_client, 'j-12345ABCDEF', 'EMRInstanceFleet'
        )

        # Verify the result
        assert result['is_valid'] is False
        assert 'incorrect type' in result['error_message']
        mock_emr_client.describe_cluster.assert_called_once_with(ClusterId='j-12345ABCDEF')

    def test_verify_emr_cluster_managed_by_mcp_client_error(self):
        """Test that verify_emr_cluster_managed_by_mcp handles ClientError correctly."""
        # Mock the EMR client to raise a ClientError
        mock_emr_client = MagicMock()
        mock_emr_client.describe_cluster.side_effect = ClientError(
            {'Error': {'Code': 'ClusterNotFound', 'Message': 'Cluster not found'}},
            'DescribeCluster',
        )

        # Test with a cluster that doesn't exist
        result = AwsHelper.verify_emr_cluster_managed_by_mcp(
            mock_emr_client, 'j-nonexistent', 'EMRCluster'
        )

        # Verify the result
        assert result['is_valid'] is False
        assert 'Error retrieving cluster' in result['error_message']
        mock_emr_client.describe_cluster.assert_called_once_with(ClusterId='j-nonexistent')

    def test_verify_emr_cluster_managed_by_mcp_cluster_resource_type(self):
        """Test that verify_emr_cluster_managed_by_mcp accepts EMR_CLUSTER_RESOURCE_TYPE as valid."""
        # Mock the EMR client
        mock_emr_client = MagicMock()
        mock_emr_client.describe_cluster.return_value = {
            'Cluster': {
                'Id': 'j-12345ABCDEF',
                'Name': 'TestCluster',
                'Status': {'State': 'RUNNING'},
                'Tags': [
                    {'Key': MCP_MANAGED_TAG_KEY, 'Value': MCP_MANAGED_TAG_VALUE},
                    {'Key': MCP_RESOURCE_TYPE_TAG_KEY, 'Value': 'EMRCluster'},
                ],
            }
        }

        # Test with a cluster that has EMRCluster type but we're checking for EMRInstanceFleet
        # This should still be valid because EMRCluster is always acceptable
        result = AwsHelper.verify_emr_cluster_managed_by_mcp(
            mock_emr_client, 'j-12345ABCDEF', 'EMRInstanceFleet'
        )

        # Verify the result
        assert result['is_valid'] is True
        assert result['error_message'] is None
        mock_emr_client.describe_cluster.assert_called_once_with(ClusterId='j-12345ABCDEF')

    def test_verify_emr_cluster_managed_by_mcp_no_tags(self):
        """Test that verify_emr_cluster_managed_by_mcp handles clusters with no tags."""
        # Mock the EMR client
        mock_emr_client = MagicMock()
        mock_emr_client.describe_cluster.return_value = {
            'Cluster': {
                'Id': 'j-12345ABCDEF',
                'Name': 'TestCluster',
                'Status': {'State': 'RUNNING'},
                # No Tags field
            }
        }

        # Test with a cluster that has no tags
        result = AwsHelper.verify_emr_cluster_managed_by_mcp(
            mock_emr_client, 'j-12345ABCDEF', 'EMRCluster'
        )

        # Verify the result
        assert result['is_valid'] is False
        assert 'not managed by MCP' in result['error_message']
        mock_emr_client.describe_cluster.assert_called_once_with(ClusterId='j-12345ABCDEF')
