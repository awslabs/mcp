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

"""Unit tests for the list_customer_iam_access function in logs_and_telemetry module."""

import unittest
from awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.list_customer_iam_access import (
    list_customer_iam_access,
)
from awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.register_module import register_module
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, Mock


class TestListCustomerIamAccess(unittest.TestCase):
    """Tests for the list_customer_iam_access function."""

    def _extract_tool_function(self, mock_tool_decorator, index=0):
        """Helper method to extract a tool function from the mock decorator."""
        count = 0
        for args, kwargs in mock_tool_decorator.call_args_list:
            if len(args) > 0 and callable(args[0]):
                if count == index:
                    return args[0]
                count += 1
        return None

    def test_list_customer_iam_access_basic(self):
        """Test the list_customer_iam_access function with basic inputs."""
        # Setup mock client manager and clients
        mock_client_manager = MagicMock()
        mock_kafka_client = MagicMock()
        mock_iam_client = MagicMock()

        # Configure get_client to return different clients based on service name
        def get_client_side_effect(region, service_name):
            if service_name == 'kafka':
                return mock_kafka_client
            elif service_name == 'iam':
                return mock_iam_client
            return MagicMock()

        mock_client_manager.get_client.side_effect = get_client_side_effect

        # Mock responses
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {
                'BrokerNodeGroupInfo': {
                    'ConnectivityInfo': {
                        'VpcConnectivity': {
                            'ClientAuthentication': {'Sasl': {'Iam': {'Enabled': True}}}
                        }
                    }
                }
            }
        }

        mock_kafka_client.get_cluster_policy.return_value = {
            'Policy': {
                'Version': '2012-10-17',
                'Statement': [
                    {'Effect': 'Allow', 'Action': ['kafka:DescribeCluster'], 'Resource': '*'}
                ],
            }
        }

        # Mock IAM paginator
        mock_paginator = MagicMock()
        mock_iam_client.get_paginator.return_value = mock_paginator

        # Mock paginator response
        mock_paginator.paginate.return_value = [
            {
                'Policies': [
                    {
                        'PolicyName': 'TestPolicy',
                        'Arn': 'arn:aws:iam::123456789012:policy/TestPolicy',
                        'DefaultVersionId': 'v1',
                    }
                ]
            }
        ]

        # Mock policy version response
        mock_iam_client.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': ['kafka:Connect', 'kafka:DescribeCluster'],
                            'Resource': 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234',
                        }
                    ]
                }
            }
        }

        # Mock entities for policy response
        mock_iam_client.list_entities_for_policy.return_value = {
            'PolicyGroups': [],
            'PolicyUsers': [],
            'PolicyRoles': [{'RoleName': 'TestRole', 'RoleId': 'AROA1234567890EXAMPLE'}],
        }

        # Test data
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'

        # Call the function
        result = list_customer_iam_access(
            cluster_arn=cluster_arn, client_manager=mock_client_manager
        )

        # Verify the result
        self.assertEqual(result['cluster_info']['cluster_arn'], cluster_arn)
        self.assertEqual(result['cluster_info']['cluster_name'], 'test-cluster')
        self.assertTrue(result['cluster_info']['iam_auth_enabled'])
        self.assertEqual(result['resource_policies']['Version'], '2012-10-17')
        self.assertEqual(len(result['matching_policies']), 1)

        # Verify the matching policy details
        policy_arn = 'arn:aws:iam::123456789012:policy/TestPolicy'
        self.assertIn(policy_arn, result['matching_policies'])
        self.assertEqual(result['matching_policies'][policy_arn]['PolicyName'], 'TestPolicy')
        self.assertEqual(result['matching_policies'][policy_arn]['ResourceType'], 'exact')
        self.assertEqual(len(result['matching_policies'][policy_arn]['PolicyRoles']), 1)
        self.assertEqual(
            result['matching_policies'][policy_arn]['PolicyRoles'][0]['RoleName'], 'TestRole'
        )

    def test_list_customer_iam_access_wildcard_match(self):
        """Test the list_customer_iam_access function with wildcard resource matching."""
        # Setup mock client manager and clients
        mock_client_manager = MagicMock()
        mock_kafka_client = MagicMock()
        mock_iam_client = MagicMock()

        # Configure get_client to return different clients based on service name
        def get_client_side_effect(region, service_name):
            if service_name == 'kafka':
                return mock_kafka_client
            elif service_name == 'iam':
                return mock_iam_client
            return MagicMock()

        mock_client_manager.get_client.side_effect = get_client_side_effect

        # Mock responses
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {
                'BrokerNodeGroupInfo': {
                    'ConnectivityInfo': {
                        'VpcConnectivity': {
                            'ClientAuthentication': {'Sasl': {'Iam': {'Enabled': False}}}
                        }
                    }
                }
            }
        }

        mock_kafka_client.get_cluster_policy.return_value = {'Policy': {}}

        # Mock IAM paginator
        mock_paginator = MagicMock()
        mock_iam_client.get_paginator.return_value = mock_paginator

        # Mock paginator response with multiple policies
        mock_paginator.paginate.return_value = [
            {
                'Policies': [
                    {
                        'PolicyName': 'WildcardPolicy',
                        'Arn': 'arn:aws:iam::123456789012:policy/WildcardPolicy',
                        'DefaultVersionId': 'v1',
                    },
                    {
                        'PolicyName': 'ClusterWildcardPolicy',
                        'Arn': 'arn:aws:iam::123456789012:policy/ClusterWildcardPolicy',
                        'DefaultVersionId': 'v1',
                    },
                    {
                        'PolicyName': 'PatternPolicy',
                        'Arn': 'arn:aws:iam::123456789012:policy/PatternPolicy',
                        'DefaultVersionId': 'v1',
                    },
                ]
            }
        ]

        # Mock policy version responses
        def get_policy_version_side_effect(PolicyArn, VersionId):
            if PolicyArn == 'arn:aws:iam::123456789012:policy/WildcardPolicy':
                return {
                    'PolicyVersion': {
                        'Document': {
                            'Statement': [
                                {'Effect': 'Allow', 'Action': ['kafka:*'], 'Resource': '*'}
                            ]
                        }
                    }
                }
            elif PolicyArn == 'arn:aws:iam::123456789012:policy/ClusterWildcardPolicy':
                return {
                    'PolicyVersion': {
                        'Document': {
                            'Statement': [
                                {
                                    'Effect': 'Allow',
                                    'Action': ['kafka:Connect'],
                                    'Resource': 'arn:aws:kafka:us-west-2:*:cluster/test-cluster/*',
                                }
                            ]
                        }
                    }
                }
            elif PolicyArn == 'arn:aws:iam::123456789012:policy/PatternPolicy':
                return {
                    'PolicyVersion': {
                        'Document': {
                            'Statement': [
                                {
                                    'Effect': 'Allow',
                                    'Action': ['kafka-cluster:*'],
                                    'Resource': 'arn:aws:kafka:us-west-2:123456789012:cluster/test-*/*',
                                }
                            ]
                        }
                    }
                }
            return {}

        mock_iam_client.get_policy_version.side_effect = get_policy_version_side_effect

        # Mock entities for policy response
        def list_entities_side_effect(PolicyArn):
            return {'PolicyGroups': [], 'PolicyUsers': [], 'PolicyRoles': []}

        mock_iam_client.list_entities_for_policy.side_effect = list_entities_side_effect

        # Test data
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'

        # Call the function
        result = list_customer_iam_access(
            cluster_arn=cluster_arn, client_manager=mock_client_manager
        )

        # Verify the result
        self.assertEqual(result['cluster_info']['cluster_arn'], cluster_arn)
        self.assertEqual(result['cluster_info']['cluster_name'], 'test-cluster')
        self.assertFalse(result['cluster_info']['iam_auth_enabled'])

        # Verify the matching policies
        self.assertEqual(len(result['matching_policies']), 3)

        # Check wildcard policy
        wildcard_policy_arn = 'arn:aws:iam::123456789012:policy/WildcardPolicy'
        self.assertIn(wildcard_policy_arn, result['matching_policies'])
        self.assertEqual(
            result['matching_policies'][wildcard_policy_arn]['ResourceType'], 'global_wildcard'
        )

        # Check cluster wildcard policy
        cluster_wildcard_policy_arn = 'arn:aws:iam::123456789012:policy/ClusterWildcardPolicy'
        self.assertIn(cluster_wildcard_policy_arn, result['matching_policies'])
        self.assertEqual(
            result['matching_policies'][cluster_wildcard_policy_arn]['ResourceType'],
            'cluster_wildcard',
        )

        # Check pattern policy
        pattern_policy_arn = 'arn:aws:iam::123456789012:policy/PatternPolicy'
        self.assertIn(pattern_policy_arn, result['matching_policies'])
        self.assertEqual(
            result['matching_policies'][pattern_policy_arn]['ResourceType'], 'pattern_match'
        )

    def test_list_customer_iam_access_no_policy(self):
        """Test the list_customer_iam_access function when no cluster policy exists."""
        # Setup mock client manager and clients
        mock_client_manager = MagicMock()
        mock_kafka_client = MagicMock()
        mock_iam_client = MagicMock()

        # Configure get_client to return different clients based on service name
        def get_client_side_effect(region, service_name):
            if service_name == 'kafka':
                return mock_kafka_client
            elif service_name == 'iam':
                return mock_iam_client
            return MagicMock()

        mock_client_manager.get_client.side_effect = get_client_side_effect

        # Mock responses
        mock_kafka_client.describe_cluster_v2.return_value = {'ClusterInfo': {}}

        # Mock get_cluster_policy to raise NotFoundException
        error_response = {'Error': {'Code': 'NotFoundException', 'Message': 'Policy not found'}}
        mock_kafka_client.get_cluster_policy.side_effect = ClientError(
            error_response, 'GetClusterPolicy'
        )

        # Mock IAM paginator
        mock_paginator = MagicMock()
        mock_iam_client.get_paginator.return_value = mock_paginator

        # Mock paginator response with no matching policies
        mock_paginator.paginate.return_value = [
            {
                'Policies': [
                    {
                        'PolicyName': 'UnrelatedPolicy',
                        'Arn': 'arn:aws:iam::123456789012:policy/UnrelatedPolicy',
                        'DefaultVersionId': 'v1',
                    }
                ]
            }
        ]

        # Mock policy version response
        mock_iam_client.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Statement': [{'Effect': 'Allow', 'Action': ['s3:*'], 'Resource': '*'}]
                }
            }
        }

        # Test data
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'

        # Call the function
        result = list_customer_iam_access(
            cluster_arn=cluster_arn, client_manager=mock_client_manager
        )

        # Verify the result
        self.assertEqual(result['cluster_info']['cluster_arn'], cluster_arn)
        self.assertEqual(result['cluster_info']['cluster_name'], 'test-cluster')
        self.assertFalse(result['cluster_info']['iam_auth_enabled'])
        self.assertEqual(result['resource_policies'], [])
        self.assertEqual(len(result['matching_policies']), 0)

    def test_list_customer_iam_access_invalid_arn(self):
        """Test the list_customer_iam_access function with an invalid ARN."""
        # Setup mock client manager
        mock_client_manager = MagicMock()

        # Test data
        invalid_arn = 'arn:aws:s3:us-west-2:123456789012:bucket/test-bucket'

        # Call the function and expect an exception
        with self.assertRaises(ValueError) as context:
            list_customer_iam_access(cluster_arn=invalid_arn, client_manager=mock_client_manager)

        self.assertIn('cluster_arn must be a valid MSK cluster ARN', str(context.exception))

    def test_list_customer_iam_access_client_error(self):
        """Test the list_customer_iam_access function when an AWS API error occurs."""
        # Setup mock client manager and clients
        mock_client_manager = MagicMock()
        mock_kafka_client = MagicMock()

        # Configure get_client to return different clients based on service name
        def get_client_side_effect(region, service_name):
            if service_name == 'kafka':
                return mock_kafka_client
            return MagicMock()

        mock_client_manager.get_client.side_effect = get_client_side_effect

        # Mock describe_cluster_v2 to raise an error
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        mock_kafka_client.describe_cluster_v2.side_effect = ClientError(
            error_response, 'DescribeClusterV2'
        )

        # Test data
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'

        # Call the function and expect an exception
        with self.assertRaises(ClientError) as context:
            list_customer_iam_access(cluster_arn=cluster_arn, client_manager=mock_client_manager)

        self.assertEqual(context.exception.response['Error']['Code'], 'AccessDeniedException')

    def test_list_customer_iam_access_no_client_manager(self):
        """Test the list_customer_iam_access function when no client manager is provided."""
        # Test data
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'

        # Call the function and expect an exception
        with self.assertRaises(ValueError) as context:
            list_customer_iam_access(cluster_arn=cluster_arn, client_manager=None)

        self.assertIn('Client manager must be provided', str(context.exception))

    def test_list_customer_iam_access_tool_registration(self):
        """Test that the list_customer_iam_access_tool is properly registered."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator

        # Register the module
        register_module(mock_mcp)

        # Verify the tool was registered
        self.assertEqual(mock_mcp.tool.call_count, 2)  # Both tools should be registered

        # Check that one of the calls was for list_customer_iam_access
        tool_names = [call_args[1]['name'] for call_args in mock_mcp.tool.call_args_list]
        self.assertIn('list_customer_iam_access', tool_names)

        # Find the index of the list_customer_iam_access tool
        list_customer_iam_access_index = tool_names.index('list_customer_iam_access')

        # Verify the tool decorator was called with a function
        self.assertTrue(
            callable(mock_tool_decorator.call_args_list[list_customer_iam_access_index][0][0])
        )


if __name__ == '__main__':
    unittest.main()
