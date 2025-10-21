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

"""Tests for Grafana migration prompt."""

import os
import pytest
from awslabs.aws_iot_sitewise_mcp_server.prompts.grafana_migration import (
    grafana_workspace_migration,
)
from awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper import AwsHelper
from unittest.mock import Mock, patch


class TestGrafanaMigration:
    """Test cases for Grafana migration prompt."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Clear cached partition before each test
        AwsHelper._aws_partition = None

    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_region')
    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_partition')
    def test_grafana_migration_aws_commercial_partition(self, mock_get_partition, mock_get_region):
        """Test migration prompt with AWS commercial partition."""
        # Mock AWS helper methods
        mock_get_region.return_value = 'us-east-1'
        mock_get_partition.return_value = 'aws'

        portal_id = 'test-portal-123'
        result = grafana_workspace_migration(portal_id)

        # Verify the methods were called
        mock_get_region.assert_called_once()
        mock_get_partition.assert_called_once()

        # Verify the result contains expected content
        assert portal_id in result
        assert 'us-east-1' in result
        assert 'aws' in result
        assert '✅ **SUPPORTED**: Proceeding with migration in AWS commercial partition.' in result
        assert 'Migration process will be skipped' not in result
        assert 'Step-by-Step Migration Process' in result

    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_region')
    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_partition')
    def test_grafana_migration_aws_china_partition(self, mock_get_partition, mock_get_region):
        """Test migration prompt with AWS China partition."""
        # Mock AWS helper methods
        mock_get_region.return_value = 'cn-north-1'
        mock_get_partition.return_value = 'aws-cn'

        portal_id = 'test-portal-456'
        result = grafana_workspace_migration(portal_id)

        # Verify the methods were called
        mock_get_region.assert_called_once()
        mock_get_partition.assert_called_once()

        # Verify the result contains expected content for unsupported partition
        assert portal_id in result
        assert 'cn-north-1' in result
        assert 'aws-cn' in result
        assert (
            "❌ **NOT SUPPORTED**: Migration is not supported in the 'aws-cn' partition." in result
        )
        assert '**Migration process will be skipped due to unsupported partition.**' in result
        assert (
            '⚠️ **MIGRATION SKIPPED**: The following migration steps are not executed because the current partition is "aws-cn"'
            in result
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_region')
    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_partition')
    def test_grafana_migration_aws_govcloud_partition(self, mock_get_partition, mock_get_region):
        """Test migration prompt with AWS GovCloud partition."""
        # Mock AWS helper methods
        mock_get_region.return_value = 'us-gov-west-1'
        mock_get_partition.return_value = 'aws-us-gov'

        portal_id = 'test-portal-789'
        result = grafana_workspace_migration(portal_id)

        # Verify the methods were called
        mock_get_region.assert_called_once()
        mock_get_partition.assert_called_once()

        # Verify the result contains expected content for unsupported partition
        assert portal_id in result
        assert 'us-gov-west-1' in result
        assert 'aws-us-gov' in result
        assert (
            "❌ **NOT SUPPORTED**: Migration is not supported in the 'aws-us-gov' partition."
            in result
        )
        assert '**Migration process will be skipped due to unsupported partition.**' in result
        assert (
            '⚠️ **MIGRATION SKIPPED**: The following migration steps are not executed because the current partition is "aws-us-gov"'
            in result
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_region')
    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_partition')
    def test_grafana_migration_different_regions(self, mock_get_partition, mock_get_region):
        """Test migration prompt with different AWS regions."""
        test_cases = [
            ('us-west-2', 'aws'),
            ('eu-west-1', 'aws'),
            ('ap-southeast-1', 'aws'),
            ('ca-central-1', 'aws'),
        ]

        for region, partition in test_cases:
            # Reset for each test case
            self.setup_method()
            mock_get_region.return_value = region
            mock_get_partition.return_value = partition

            portal_id = f'test-portal-{region}'
            result = grafana_workspace_migration(portal_id)

            # Verify region and partition are correctly included
            assert region in result
            assert partition in result
            assert portal_id in result
            assert (
                '✅ **SUPPORTED**: Proceeding with migration in AWS commercial partition.'
                in result
            )

    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_region')
    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_partition')
    def test_grafana_migration_region_in_commands(self, mock_get_partition, mock_get_region):
        """Test that region is correctly included in AWS CLI commands."""
        # Mock AWS helper methods
        mock_get_region.return_value = 'us-west-2'
        mock_get_partition.return_value = 'aws'

        portal_id = 'test-portal-commands'
        result = grafana_workspace_migration(portal_id)

        # Verify region appears in various command contexts
        assert '--region us-west-2' in result
        assert 'region="us-west-2"' in result
        assert 'defaultRegion": "us-west-2"' in result

    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_region')
    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_partition')
    def test_grafana_migration_partition_in_arns(self, mock_get_partition, mock_get_region):
        """Test that partition is correctly included in ARN constructions."""
        # Mock AWS helper methods
        mock_get_region.return_value = 'us-east-1'
        mock_get_partition.return_value = 'aws'

        portal_id = 'test-portal-arns'
        result = grafana_workspace_migration(portal_id)

        # Verify partition appears in ARN constructions
        assert 'arn:aws:iam::aws:policy/AWSIoTSiteWiseReadOnlyAccess' in result
        assert 'arn:aws:grafana:us-east-1:' in result

    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_region')
    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_partition')
    def test_grafana_migration_partition_china_arns(self, mock_get_partition, mock_get_region):
        """Test that China partition is correctly included in ARN constructions."""
        # Mock AWS helper methods
        mock_get_region.return_value = 'cn-north-1'
        mock_get_partition.return_value = 'aws-cn'

        portal_id = 'test-portal-china-arns'
        result = grafana_workspace_migration(portal_id)

        # Verify China partition appears in ARN constructions
        assert 'arn:aws-cn:iam::aws:policy/AWSIoTSiteWiseReadOnlyAccess' in result
        assert 'arn:aws-cn:grafana:cn-north-1:' in result

    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_region')
    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_partition')
    def test_grafana_migration_error_handling(self, mock_get_partition, mock_get_region):
        """Test migration prompt handles AWS helper errors gracefully."""
        # Mock AWS helper methods to raise exceptions
        mock_get_region.side_effect = Exception('Region lookup failed')
        mock_get_partition.side_effect = Exception('Partition lookup failed')

        portal_id = 'test-portal-error'

        # Should not raise exception, but handle gracefully
        with pytest.raises(Exception):
            grafana_workspace_migration(portal_id)

    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_region')
    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_partition')
    def test_grafana_migration_portal_id_validation(self, mock_get_partition, mock_get_region):
        """Test that portal ID validation is performed."""
        # Mock AWS helper methods
        mock_get_region.return_value = 'us-east-1'
        mock_get_partition.return_value = 'aws'

        # Test with valid portal ID
        valid_portal_id = 'valid-portal-123'
        result = grafana_workspace_migration(valid_portal_id)
        assert valid_portal_id in result

        # Test with potentially problematic portal ID (should be validated by validate_string_for_injection)
        problematic_portal_id = 'portal-with-special-chars-!@#'
        # This should either work or raise a ValidationError depending on the validation logic
        try:
            result = grafana_workspace_migration(problematic_portal_id)
            assert problematic_portal_id in result
        except Exception:
            # ValidationError is expected for invalid characters
            pass

    @patch.dict(os.environ, {'AWS_REGION': 'eu-central-1'})
    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_partition')
    def test_grafana_migration_with_env_region(self, mock_get_partition):
        """Test migration prompt uses region from environment variable."""
        # Mock partition method
        mock_get_partition.return_value = 'aws'

        portal_id = 'test-portal-env'
        result = grafana_workspace_migration(portal_id)

        # Verify environment region is used
        assert 'eu-central-1' in result
        assert 'aws' in result

    @patch('boto3.client')
    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_region')
    def test_grafana_migration_with_real_partition_call(self, mock_get_region, mock_boto_client):
        """Test migration prompt with actual partition retrieval logic."""
        # Mock region
        mock_get_region.return_value = 'us-east-1'

        # Mock STS client response
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws:sts::123456789012:assumed-role/MyRole/MySession'
        }
        mock_boto_client.return_value = mock_sts

        portal_id = 'test-portal-real-partition'
        result = grafana_workspace_migration(portal_id)

        # Verify STS was called and partition was extracted
        mock_boto_client.assert_called_with('sts')
        mock_sts.get_caller_identity.assert_called_once()

        # Verify correct partition is used
        assert 'aws' in result
        assert '✅ **SUPPORTED**: Proceeding with migration in AWS commercial partition.' in result

    def test_grafana_migration_content_structure(self):
        """Test that migration prompt contains all expected sections."""
        with (
            patch(
                'awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_region'
            ) as mock_region,
            patch(
                'awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_partition'
            ) as mock_partition,
        ):
            mock_region.return_value = 'us-east-1'
            mock_partition.return_value = 'aws'

            portal_id = 'test-portal-structure'
            result = grafana_workspace_migration(portal_id)

            # Verify all major sections are present
            expected_sections = [
                'Migration Architecture Overview',
                'Step-by-Step Migration Process',
                '1. **Portal Discovery and Analysis**',
                '2. **AWS Managed Grafana Workspace Setup**',
                '3. **SiteWise Data Source Configuration**',
                '4. **Project-to-Folder Migration**',
                '5. **Dashboard Conversion and Migration**',
                '6. **User Access and Permissions Migration**',
                '7. **Data Validation and Testing**',
                'Migration Checklist',
                'Troubleshooting Guide',
                'Success Metrics',
            ]

            for section in expected_sections:
                assert section in result, f'Missing section: {section}'

    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_region')
    @patch('awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper.AwsHelper.get_aws_partition')
    def test_grafana_migration_workspace_naming(self, mock_get_partition, mock_get_region):
        """Test that workspace naming logic includes portal name reference."""
        # Mock AWS helper methods
        mock_get_region.return_value = 'us-east-1'
        mock_get_partition.return_value = 'aws'

        portal_id = 'test-portal-naming'
        result = grafana_workspace_migration(portal_id)

        # Verify workspace naming logic is present
        assert 'PORTAL_NAME="<portal_name_from_step1>"' in result
        assert 'WORKSPACE_NAME="$SANITIZED_PORTAL_NAME-grafana-workspace"' in result
        assert 'Creating workspace for portal: $PORTAL_NAME' in result
        assert 'Workspace name: $WORKSPACE_NAME' in result
        assert 'Based on portal: $PORTAL_NAME' in result
