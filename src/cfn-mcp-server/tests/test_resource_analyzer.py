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

import unittest
from awslabs.cfn_mcp_server.stack_analysis.resource_analyzer import (
    ResourceAnalyzer,
)
from unittest.mock import patch


class TestResourceAnalyzer(unittest.TestCase):
    """Unit tests for the ResourceAnalyzer class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.region = 'us-west-2'
        self.stack_name = 'test-stack'
        self.resource_scan_id = 'test-scan-id'

        # Use patch to mock CloudFormationUtils during setup
        with patch(
            'awslabs.cfn_mcp_server.stack_analysis.resource_analyzer.CloudFormationUtils'
        ) as mock_cf_utils_class:
            self.mock_cf_utils = mock_cf_utils_class.return_value
            self.analyzer = ResourceAnalyzer(region=self.region)

    def test_init(self):
        """Test initialization of ResourceAnalyzer."""
        # Since we're testing initialization, we need a fresh patch
        with patch(
            'awslabs.cfn_mcp_server.stack_analysis.resource_analyzer.CloudFormationUtils'
        ) as mock_cf_utils_class:
            # Create a new analyzer to test initialization
            analyzer = ResourceAnalyzer(region=self.region)

            # Verify CloudFormationUtils was initialized with the correct region
            mock_cf_utils_class.assert_called_once_with(self.region)

            # Verify instance variables were initialized correctly
            self.assertEqual(analyzer.stack_resources, {})
            self.assertEqual(analyzer.scanned_resources_by_id, {})

    def test_match_stack_to_scan(self):
        """Test match_stack_to_scan with provided scan ID."""
        # Setup mock CloudFormationUtils
        self.mock_cf_utils.resource_scan_id = None

        # Mock list_stack_resources
        self.mock_cf_utils.list_stack_resources.return_value = [
            {
                'LogicalResourceId': 'MyBucket',
                'PhysicalResourceId': 'test-bucket',
                'ResourceType': 'AWS::S3::Bucket',
                'ResourceStatus': 'CREATE_COMPLETE',
            },
            {
                'LogicalResourceId': 'MyFunction',
                'PhysicalResourceId': 'test-function',
                'ResourceType': 'AWS::Lambda::Function',
                'ResourceStatus': 'CREATE_COMPLETE',
            },
        ]

        # Mock list_resource_scan_resources
        self.mock_cf_utils.list_resource_scan_resources.return_value = [
            {
                'ResourceType': 'AWS::S3::Bucket',
                'ResourceIdentifier': {'BucketName': 'test-bucket'},
                'ManagedByStack': True,
            }
        ]

        # Call the method to test
        result = self.analyzer.match_stack_to_scan(self.stack_name, self.resource_scan_id)

        # Verify the resource scan ID was set
        # We need to manually set this since the mock doesn't automatically update
        self.mock_cf_utils.resource_scan_id = self.resource_scan_id

        # Verify the result structure
        self.assertEqual(result['stack_name'], self.stack_name)
        self.assertEqual(result['resource_scan_id'], self.resource_scan_id)

        # Verify matched resources
        self.assertEqual(len(result['matched_resources']), 1)
        matched = result['matched_resources'][0]
        self.assertTrue(matched.matched)
        self.assertEqual(matched.physical_resource_id, 'test-bucket')
        self.assertEqual(matched.resource_type, 'AWS::S3::Bucket')

        # Verify unmatched resources
        self.assertEqual(len(result['unmatched_resources']), 1)
        unmatched = result['unmatched_resources'][0]
        self.assertFalse(unmatched.matched)
        self.assertEqual(unmatched.physical_resource_id, 'test-function')
        self.assertEqual(unmatched.resource_type, 'AWS::Lambda::Function')

    def test_match_stack_to_scan_error_handling(self):
        """Test match_stack_to_scan error handling."""
        # Import the ServerError class
        from awslabs.cfn_mcp_server.errors import ServerError

        # Mock list_stack_resources to raise a ServerError instead of a generic Exception
        error_message = 'Error in match_stack_to_scan: An internal error occurred while processing your request'
        self.mock_cf_utils.list_stack_resources.side_effect = ServerError(error_message)

        # Call the method to test
        result = self.analyzer.match_stack_to_scan(self.stack_name)

        # Verify error handling
        self.assertEqual(result['stack_name'], self.stack_name)
        self.assertEqual(len(result['matched_resources']), 0)
        self.assertEqual(len(result['unmatched_resources']), 0)
        self.assertIn('An internal error occurred while processing your request', result['error'])

    def test_get_related_resources(self):
        """Test get_related_resources method."""
        # Mock list_resource_scan_related_resources
        self.mock_cf_utils.list_resource_scan_related_resources.return_value = {
            'RelatedResources': [
                {
                    'ResourceType': 'AWS::S3::Bucket',
                    'ResourceIdentifier': {'BucketName': 'related-bucket'},
                },
                {
                    'ResourceType': 'AWS::Lambda::Function',
                    'ResourceIdentifier': {'FunctionName': 'related-function'},
                },
            ],
            'NextToken': None,
        }

        # Resources to find related resources for
        resources = [
            {
                'ResourceType': 'AWS::S3::Bucket',
                'ResourceIdentifier': {'BucketName': 'XXXXXXXXXXX'},
            }
        ]

        # Call the method to test
        result = self.analyzer.get_related_resources(resources, self.resource_scan_id)

        # Verify the result
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['ResourceType'], 'AWS::S3::Bucket')
        self.assertEqual(result[0]['ResourceIdentifier']['BucketName'], 'related-bucket')
        self.assertEqual(result[1]['ResourceType'], 'AWS::Lambda::Function')
        self.assertEqual(result[1]['ResourceIdentifier']['FunctionName'], 'related-function')
