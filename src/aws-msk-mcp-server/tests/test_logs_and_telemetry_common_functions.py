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

"""Unit tests for the common_functions module used by logs_and_telemetry."""

import unittest
from awslabs.aws_msk_mcp_server.tools.common_functions.common_functions import (
    check_mcp_generated_tag,
    get_cluster_name,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestCommonFunctions(unittest.TestCase):
    """Tests for the common_functions module used by logs_and_telemetry."""

    def test_get_cluster_name_from_arn(self):
        """Test the get_cluster_name function with a valid ARN."""
        # Test with a valid ARN
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        cluster_name = get_cluster_name(cluster_arn)
        self.assertEqual(cluster_name, 'test-cluster')

    def test_get_cluster_name_from_direct_name(self):
        """Test the get_cluster_name function with a direct cluster name."""
        # Test with a direct cluster name
        cluster_name = 'test-cluster'
        result = get_cluster_name(cluster_name)
        self.assertEqual(result, 'test-cluster')

    def test_get_cluster_name_invalid_arn(self):
        """Test the get_cluster_name function with an invalid ARN."""
        # Test with an invalid ARN
        invalid_arns = [
            'arn:aws:kafka:us-west-2:123456789012:cluster',
            'arn:aws:kafka:us-west-2:123456789012:cluster/',
        ]

        for invalid_arn in invalid_arns:
            with self.assertRaises(ValueError):
                get_cluster_name(invalid_arn)

    def test_get_cluster_name_non_kafka_arn(self):
        """Test the get_cluster_name function with a non-kafka ARN."""
        # Test with a non-kafka ARN
        non_kafka_arn = 'arn:aws:s3:us-west-2:123456789012:bucket/test-bucket'
        # Non-kafka ARNs should be treated as direct cluster names
        result = get_cluster_name(non_kafka_arn)
        self.assertEqual(result, non_kafka_arn)

    def test_get_cluster_name_non_arn(self):
        """Test the get_cluster_name function with a non-ARN string."""
        # Test with a non-ARN string
        non_arn = 'not-an-arn'
        # Non-ARN strings should be treated as direct cluster names
        result = get_cluster_name(non_arn)
        self.assertEqual(result, non_arn)

    def test_check_mcp_generated_tag_true(self):
        """Test the check_mcp_generated_tag function when the tag is present and true."""
        # Setup
        mock_client = MagicMock()
        mock_client.list_tags_for_resource.return_value = {'Tags': {'MCP Generated': 'true'}}

        # Test
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        result = check_mcp_generated_tag(cluster_arn, mock_client)

        # Verify
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn=cluster_arn)
        self.assertTrue(result)

    def test_check_mcp_generated_tag_false(self):
        """Test the check_mcp_generated_tag function when the tag is present but false."""
        # Setup
        mock_client = MagicMock()
        mock_client.list_tags_for_resource.return_value = {'Tags': {'MCP Generated': 'false'}}

        # Test
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        result = check_mcp_generated_tag(cluster_arn, mock_client)

        # Verify
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn=cluster_arn)
        self.assertFalse(result)

    def test_check_mcp_generated_tag_missing(self):
        """Test the check_mcp_generated_tag function when the tag is missing."""
        # Setup
        mock_client = MagicMock()
        mock_client.list_tags_for_resource.return_value = {'Tags': {'Other Tag': 'value'}}

        # Test
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        result = check_mcp_generated_tag(cluster_arn, mock_client)

        # Verify
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn=cluster_arn)
        self.assertFalse(result)

    def test_check_mcp_generated_tag_empty(self):
        """Test the check_mcp_generated_tag function when no tags are present."""
        # Setup
        mock_client = MagicMock()
        mock_client.list_tags_for_resource.return_value = {'Tags': {}}

        # Test
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        result = check_mcp_generated_tag(cluster_arn, mock_client)

        # Verify
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn=cluster_arn)
        self.assertFalse(result)

    def test_check_mcp_generated_tag_no_tags_key(self):
        """Test the check_mcp_generated_tag function when the Tags key is missing."""
        # Setup
        mock_client = MagicMock()
        mock_client.list_tags_for_resource.return_value = {}

        # Test
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        result = check_mcp_generated_tag(cluster_arn, mock_client)

        # Verify
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn=cluster_arn)
        self.assertFalse(result)

    def test_check_mcp_generated_tag_case_insensitive(self):
        """Test the check_mcp_generated_tag function with case-insensitive tag value."""
        # Setup
        mock_client = MagicMock()
        mock_client.list_tags_for_resource.return_value = {'Tags': {'MCP Generated': 'TRUE'}}

        # Test
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        result = check_mcp_generated_tag(cluster_arn, mock_client)

        # Verify
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn=cluster_arn)
        self.assertTrue(result)

    def test_check_mcp_generated_tag_client_error(self):
        """Test the check_mcp_generated_tag function when a client error occurs."""
        # Setup
        mock_client = MagicMock()
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'User is not authorized to perform: kafka:ListTagsForResource',
            }
        }
        mock_client.list_tags_for_resource.side_effect = ClientError(
            error_response, 'ListTagsForResource'
        )

        # Test
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        with self.assertRaises(ClientError) as context:
            check_mcp_generated_tag(cluster_arn, mock_client)

        # Verify
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn=cluster_arn)
        self.assertEqual(context.exception.response['Error']['Code'], 'AccessDeniedException')

    def test_check_mcp_generated_tag_no_client(self):
        """Test the check_mcp_generated_tag function with no client."""
        # Test
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        with self.assertRaises(ValueError) as context:
            check_mcp_generated_tag(cluster_arn, None)

        # Verify
        self.assertEqual(
            str(context.exception),
            'Client must be provided. This function should only be called from a tool function.',
        )


if __name__ == '__main__':
    unittest.main()
