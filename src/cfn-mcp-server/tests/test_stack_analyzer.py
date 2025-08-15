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

"""Tests for the StackAnalyzer class."""

import pytest
from awslabs.cfn_mcp_server.stack_analysis.stack_analyzer import StackAnalyzer
from unittest.mock import MagicMock, patch


class TestStackAnalyzerPytest:
    """Pytest tests for StackAnalyzer."""

    @pytest.fixture
    def mock_cfn_utils(self):
        """Create a mock CloudFormationUtils instance."""
        return MagicMock()

    @pytest.fixture
    def mock_resource_matcher(self):
        """Create a mock ResourceAnalyzer instance."""
        return MagicMock()

    @pytest.fixture
    def stack_analyzer(self, mock_cfn_utils, mock_resource_matcher):
        """Create StackAnalyzer with mocked dependencies."""
        # Create the analyzer first
        analyzer = StackAnalyzer(region='us-east-1')

        # Then manually set the mocks
        analyzer.cfn_utils = mock_cfn_utils
        analyzer.resource_matcher = mock_resource_matcher

        return analyzer

    def test_get_best_cfn_practices(self):
        """Test getting CloudFormation best practices."""
        best_practices = StackAnalyzer.get_best_cfn_practices()

        expected_keys = [
            'nested_stacks',
            'cross_stack_references',
            'resource_management',
            'stack_policies',
            'iam_access_control',
            'parameter_constraints',
            'resource_dependencies',
            'resource_cleanup',
            'common_components',
        ]

        for key in expected_keys:
            assert key in best_practices
            assert isinstance(best_practices[key], str)

    def test_analyze_stack_success_pytest(
        self, stack_analyzer, mock_cfn_utils, mock_resource_matcher
    ):
        """Test analyzing a stack successfully."""
        stack_name = 'test-stack'

        # Manually set the mocks on the stack_analyzer instance
        stack_analyzer.cfn_utils = mock_cfn_utils
        stack_analyzer.resource_matcher = mock_resource_matcher

        # Mock describe_stack
        stack_details = {
            'StackName': stack_name,
            'StackStatus': 'CREATE_COMPLETE',
            'CreationTime': '2023-01-01T00:00:00Z',
            'LastUpdatedTime': '2023-01-02T00:00:00Z',
            'Outputs': [{'OutputKey': 'BucketName', 'OutputValue': 'my-bucket'}],
            'Parameters': [{'ParameterKey': 'Environment', 'ParameterValue': 'test'}],
        }
        mock_cfn_utils.describe_stack.return_value = stack_details

        # Mock resource_matcher.match_stack_to_scan
        mock_resource = MagicMock()
        mock_resource.scanned_resource_type = 'AWS::S3::Bucket'
        mock_resource.resource_identifier = {'BucketName': 'my-bucket'}
        mock_resource.logical_resource_id = 'MyBucket'
        mock_resource.physical_resource_id = 'my-bucket'
        mock_resource.resource_status = 'CREATE_COMPLETE'
        mock_resource.matched = True

        resource_analysis_results = {
            'stack_name': stack_name,
            'resource_scan_id': 'test-scan-id',
            'matched_resources': [mock_resource],
            'unmatched_resources': [],
        }
        mock_resource_matcher.match_stack_to_scan.return_value = resource_analysis_results

        # Mock resource_matcher.get_related_resources
        related_resources = [
            {
                'ResourceType': 'AWS::IAM::Role',
                'ResourceIdentifier': {'RoleName': 'my-bucket-role'},
                'ManagedByStack': False,
            }
        ]
        mock_resource_matcher.get_related_resources.return_value = related_resources

        # Mock _generate_augmentation_recommendation
        with patch.object(
            stack_analyzer, '_generate_augmentation_recommendation'
        ) as mock_augmentation:
            mock_augment_rec = MagicMock()
            mock_augment_rec.generated_template_id = 'template-id-123'
            mock_augment_rec.template_body = '{"Resources": {}}'
            mock_augmentation.return_value = (mock_augment_rec, related_resources)

            # Mock account_resource_summary
            with patch.object(stack_analyzer, 'account_resource_summary') as mock_account_summary:
                account_summary = {
                    'overall_summary': {
                        'total_resources': 100,
                        'managed_resources': 80,
                        'unmanaged_resources': 20,
                        'managed_percentage': 80.0,
                        'unmanaged_percentage': 20.0,
                    },
                    'scan_metadata': {
                        'scan_id': 'test-scan-id',
                        'scan_time': '2023-01-01T00:00:00Z',
                    },
                }
                mock_account_summary.return_value = account_summary

                # Call the method to test
                result = stack_analyzer.analyze_stack(stack_name)

                # Verify the result
                assert result['stack_info'] == stack_details
                assert result['stack_status'] == 'CREATE_COMPLETE'
                assert result['creation_time'] == '2023-01-01T00:00:00Z'
                assert result['last_updated_time'] == '2023-01-02T00:00:00Z'
                assert result['outputs'] == [
                    {'OutputKey': 'BucketName', 'OutputValue': 'my-bucket'}
                ]
                assert result['parameters'] == [
                    {'ParameterKey': 'Environment', 'ParameterValue': 'test'}
                ]
                assert 'resource_summary' in result
                assert 'related_resources_summary' in result
                assert 'account_summary' in result
                assert result['augment_recommendation'] == 'template-id-123'
                assert result['related_unmanaged_count'] == len(related_resources)

                # Verify the method calls
                mock_cfn_utils.describe_stack.assert_called_once_with(stack_name)
                mock_resource_matcher.match_stack_to_scan.assert_called_once_with(stack_name)
                mock_resource_matcher.get_related_resources.assert_called_once()
                mock_augmentation.assert_called_once()
                mock_account_summary.assert_called_once()

    def test_analyze_stack_error_pytest(self, stack_analyzer, mock_cfn_utils):
        """Test analyzing a stack with error."""
        stack_name = 'test-stack'

        # Manually set the mock
        stack_analyzer.cfn_utils = mock_cfn_utils

        # Update the error message to match what's actually returned
        error_msg = 'Stack "test-stack" not found'
        mock_cfn_utils.describe_stack.side_effect = Exception(error_msg)

        result = stack_analyzer.analyze_stack(stack_name)

        assert 'error' in result
        assert error_msg in result['error']

    def test_account_resource_summary_success_full(self, stack_analyzer, mock_cfn_utils):
        """Test account_resource_summary method with full response."""
        # Manually set the mock
        stack_analyzer.cfn_utils = mock_cfn_utils

        # Set a resource scan ID directly
        mock_cfn_utils.resource_scan_id = 'test-scan-id'

        # Mock list_resource_scan_resources
        scan_results = [
            {
                'ResourceType': 'AWS::S3::Bucket',
                'ResourceIdentifier': {'BucketName': 'bucket1'},
                'ManagedByStack': True,
                'ResourceStatus': 'CREATE_COMPLETE',
            },
            {
                'ResourceType': 'AWS::S3::Bucket',
                'ResourceIdentifier': {'BucketName': 'bucket2'},
                'ManagedByStack': False,
                'ResourceStatus': 'CREATE_COMPLETE',
            },
            {
                'ResourceType': 'AWS::Lambda::Function',
                'ResourceIdentifier': {'FunctionName': 'function1'},
                'ManagedByStack': False,
                'ResourceStatus': 'CREATE_COMPLETE',
            },
        ]
        mock_cfn_utils.list_resource_scan_resources.return_value = scan_results

        # Call the method to test with minimal=False (default)
        result = stack_analyzer.account_resource_summary(minimal=False)

        # Verify the result
        assert 'scan_metadata' in result
        assert result['scan_metadata']['scan_id'] == 'test-scan-id'
        assert result['scan_metadata']['total_resources_scanned'] == 3

        assert 'overall_summary' in result
        assert result['overall_summary']['total_resources'] == 3
        assert result['overall_summary']['managed_resources'] == 1
        assert result['overall_summary']['unmanaged_resources'] == 2
        assert result['overall_summary']['managed_percentage'] == pytest.approx(33.33, 0.01)
        assert result['overall_summary']['unmanaged_percentage'] == pytest.approx(66.67, 0.01)
        assert result['overall_summary']['unique_resource_types'] == 2

        assert 'resources_by_type' in result
        assert 'AWS::S3::Bucket' in result['resources_by_type']
        assert 'AWS::Lambda::Function' in result['resources_by_type']

        assert result['resources_by_type']['AWS::S3::Bucket']['total'] == 2
        assert result['resources_by_type']['AWS::S3::Bucket']['managed'] == 1
        assert result['resources_by_type']['AWS::S3::Bucket']['unmanaged'] == 1

        assert result['resources_by_type']['AWS::Lambda::Function']['total'] == 1
        assert result['resources_by_type']['AWS::Lambda::Function']['managed'] == 0
        assert result['resources_by_type']['AWS::Lambda::Function']['unmanaged'] == 1

        assert 'resources_by_type_ranked' in result
        assert len(result['resources_by_type_ranked']) == 2

        assert 'top_unmanaged_types' in result
        assert len(result['top_unmanaged_types']) == 2

        assert 'unmanaged_resources_detail' in result
        assert len(result['unmanaged_resources_detail']) == 2

    def test_account_resource_summary_minimal(self, stack_analyzer, mock_cfn_utils):
        """Test account_resource_summary method with minimal response."""
        # Manually set the mock
        stack_analyzer.cfn_utils = mock_cfn_utils

        # Set a resource scan ID directly
        mock_cfn_utils.resource_scan_id = 'test-scan-id'

        # Mock list_resource_scan_resources
        scan_results = [
            {
                'ResourceType': 'AWS::S3::Bucket',
                'ResourceIdentifier': {'BucketName': 'bucket1'},
                'ManagedByStack': True,
                'ResourceStatus': 'CREATE_COMPLETE',
            },
            {
                'ResourceType': 'AWS::S3::Bucket',
                'ResourceIdentifier': {'BucketName': 'bucket2'},
                'ManagedByStack': False,
                'ResourceStatus': 'CREATE_COMPLETE',
            },
            {
                'ResourceType': 'AWS::Lambda::Function',
                'ResourceIdentifier': {'FunctionName': 'function1'},
                'ManagedByStack': False,
                'ResourceStatus': 'CREATE_COMPLETE',
            },
        ]
        mock_cfn_utils.list_resource_scan_resources.return_value = scan_results

        # Call the method with minimal=True
        result = stack_analyzer.account_resource_summary(minimal=True)

        # Verify the minimal result
        assert 'scan_metadata' in result
        assert result['scan_metadata']['scan_id'] == 'test-scan-id'
        assert result['scan_metadata']['total_resources_scanned'] == 3

        assert 'overall_summary' in result
        assert result['overall_summary']['total_resources'] == 3
        assert result['overall_summary']['managed_resources'] == 1
        assert result['overall_summary']['unmanaged_resources'] == 2
        assert result['overall_summary']['managed_percentage'] == pytest.approx(33.33, 0.01)
        assert result['overall_summary']['unmanaged_percentage'] == pytest.approx(66.67, 0.01)

        # These should not be present in minimal response
        assert 'resources_by_type' not in result
        assert 'resources_by_type_ranked' not in result
        assert 'top_unmanaged_types' not in result
        assert 'unmanaged_resources_detail' not in result

    def test_validate_resource_scan_id_with_id(self, stack_analyzer, mock_cfn_utils):
        """Test _validate_resource_scan_id when ID already exists."""
        mock_cfn_utils.resource_scan_id = 'existing-scan-id'

        result = stack_analyzer._validate_resource_scan_id()

        assert result is True
        mock_cfn_utils.list_resource_scans.assert_not_called()

    def test_validate_resource_scan_id_without_id_success(self, stack_analyzer, mock_cfn_utils):
        """Test _validate_resource_scan_id when ID doesn't exist but can be found."""
        # Manually set the mock
        stack_analyzer.cfn_utils = mock_cfn_utils

        # Set resource_scan_id to None
        mock_cfn_utils.resource_scan_id = None

        # Mock list_resource_scans
        mock_cfn_utils.list_resource_scans.return_value = [{'ResourceScanId': 'new-scan-id'}]

        result = stack_analyzer._validate_resource_scan_id()

        assert result is True
        assert mock_cfn_utils.resource_scan_id == 'new-scan-id'

    def test_summarize_resources_by_managed_status(self, stack_analyzer):
        """Test summarizing resources by managed status."""
        # Mock resource analysis results
        mock_resource = MagicMock()
        mock_resource.resource_type = 'AWS::S3::Bucket'
        mock_resource.scanned_resource_type = 'AWS::S3::Bucket'

        resource_analysis_results = {
            'matched_resources': [mock_resource],
            'unmatched_resources': [],
        }

        result = stack_analyzer._summarize_resources_by_managed_status(resource_analysis_results)

        assert result['total_resources'] == 1
        assert result['managed_resources'] == 1
        assert result['unmanaged_resources'] == 0
        assert 'by_resource_type' in result

    def test_summarize_related_resources(self, stack_analyzer):
        """Test summarizing related resources."""
        # Mock related resources
        related_resources = [
            {
                'ResourceType': 'AWS::S3::Bucket',
                'ResourceIdentifier': {'BucketName': 'bucket1'},
                'ManagedByStack': True,
            },
            {
                'ResourceType': 'AWS::IAM::Role',
                'ResourceIdentifier': {'RoleName': 'role1'},
                'ManagedByStack': False,
            },
        ]

        # Mock _group_resources_by_product_type
        with patch.object(stack_analyzer, '_group_resources_by_product_type') as mock_group:
            mock_group.return_value = {
                'Storage': [related_resources[0]],
                'Security': [related_resources[1]],
            }

            result = stack_analyzer._summarize_related_resources(related_resources)

            assert result['total_resources'] == 2
            assert result['managed_resources'] == 1
            assert result['unmanaged_resources'] == 1
            assert 'by_product_type' in result
            mock_group.assert_called_once_with(related_resources)

    def test_group_resources_by_product_type(self, stack_analyzer):
        """Test grouping resources by product type."""
        # Mock related resources
        related_resources = [
            {
                'ResourceType': 'AWS::S3::Bucket',
                'ResourceIdentifier': {'BucketName': 'bucket1'},
            },
            {
                'ResourceType': 'AWS::IAM::Role',
                'ResourceIdentifier': {'RoleName': 'role1'},
            },
        ]

        # Mock RecommendationGenerator
        with patch(
            'awslabs.cfn_mcp_server.stack_analysis.stack_analyzer.RecommendationGenerator'
        ) as mock_rec_gen_class:
            mock_rec_gen = MagicMock()
            mock_rec_gen_class.return_value = mock_rec_gen

            mock_rec_gen._categorize_resources_by_product_type.return_value = {
                'Storage': [related_resources[0]],
                'Security': [related_resources[1]],
            }

            result = stack_analyzer._group_resources_by_product_type(related_resources)

            mock_rec_gen_class.assert_called_once_with(region='us-east-1')
            mock_rec_gen._categorize_resources_by_product_type.assert_called_once_with(
                resources=related_resources
            )
            assert 'Storage' in result
            assert 'Security' in result
            assert result['Storage'] == [related_resources[0]]
            assert result['Security'] == [related_resources[1]]


@pytest.mark.asyncio
class TestStackAnalyzerAsync:
    """Async tests for the StackAnalyzer class."""

    @pytest.fixture
    def stack_analyzer(self):
        """Create a StackAnalyzer instance for testing."""
        # Create new mocks directly in this fixture instead of trying to use fixtures from another class
        with (
            patch(
                'awslabs.cfn_mcp_server.stack_analysis.stack_analyzer.CloudFormationUtils'
            ) as mock_cf_utils_class,
            patch(
                'awslabs.cfn_mcp_server.stack_analysis.stack_analyzer.ResourceAnalyzer'
            ) as mock_resource_analyzer_class,
        ):
            # Create mock instances
            mock_cfn_utils = MagicMock()
            mock_resource_matcher = MagicMock()

            # Set up the return values for the mocks
            mock_cf_utils_class.return_value = mock_cfn_utils
            mock_resource_analyzer_class.return_value = mock_resource_matcher

            # Create the analyzer
            analyzer = StackAnalyzer(region='us-east-1')

            # Manually set the mocks to ensure they're used
            analyzer.cfn_utils = mock_cfn_utils
            analyzer.resource_matcher = mock_resource_matcher

            yield analyzer

    async def test_async_compatibility(self, stack_analyzer):
        """Test that the class can be used in async contexts."""
        # This test doesn't do much but ensures the class can be instantiated in an async context
        assert isinstance(stack_analyzer, StackAnalyzer)
        assert stack_analyzer.region == 'us-east-1'
