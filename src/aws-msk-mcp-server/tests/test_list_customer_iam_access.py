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

"""Tests for the list_customer_iam_access module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.list_customer_iam_access import (
    list_customer_iam_access,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


class TestListCustomerIamAccess:
    """Tests for the list_customer_iam_access module."""

    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.get_cluster_name')
    def test_list_customer_iam_access_basic(self, mock_get_cluster_name):
        """Test the list_customer_iam_access function with basic parameters."""
        # Set up mocks
        mock_kafka_client = MagicMock()
        mock_iam_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda service: {
            'kafka': mock_kafka_client,
            'iam': mock_iam_client,
        }[service]

        # Mock the response from describe_cluster
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {
                'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                'ClusterName': 'test-cluster',
                'BrokerNodeGroupInfo': {
                    'ConnectivityInfo': {
                        'VpcConnectivity': {
                            'ClientAuthentication': {'Sasl': {'Iam': {'Enabled': True}}}
                        }
                    }
                },
            }
        }

        # Mock the response from get_cluster_policy
        mock_kafka_client.get_cluster_policy.return_value = {
            'CurrentVersion': '1',
            'Policy': '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::123456789012:role/TestRole"},"Action":["kafka:GetBootstrapBrokers","kafka:DescribeCluster"],"Resource":"arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/*"}]}',
        }

        # Mock the response from list_policies
        mock_iam_client.get_paginator.return_value.paginate.return_value = [
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

        # Mock the response from get_policy_version
        mock_iam_client.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': ['kafka:GetBootstrapBrokers', 'kafka:DescribeCluster'],
                            'Resource': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/*',
                        }
                    ],
                }
            }
        }

        # Mock the response from list_entities_for_policy
        mock_iam_client.list_entities_for_policy.return_value = {
            'PolicyRoles': [{'RoleName': 'TestRole', 'RoleId': 'AROAEXAMPLEID'}]
        }

        # Mock the get_cluster_name function
        mock_get_cluster_name.return_value = 'test-cluster'

        # Set up parameters
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'

        # Call the function
        result = list_customer_iam_access(
            cluster_arn=cluster_arn, client_manager=mock_client_manager
        )

        # Verify the result
        assert 'cluster_info' in result
        assert 'resource_policies' in result
        assert 'matching_policies' in result

        assert result['cluster_info']['cluster_name'] == 'test-cluster'
        assert result['cluster_info']['iam_auth_enabled'] is True

        # Verify the calls
        mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)
        mock_kafka_client.get_cluster_policy.assert_called_once_with(ClusterArn=cluster_arn)
        mock_get_cluster_name.assert_called_once_with(cluster_arn)

    def test_list_customer_iam_access_with_no_policy(self):
        """Test the list_customer_iam_access function when there's no policy."""
        # Set up mocks
        mock_kafka_client = MagicMock()
        mock_iam_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda service: {
            'kafka': mock_kafka_client,
            'iam': mock_iam_client,
        }[service]

        # Mock the response from describe_cluster
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {
                'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                'ClusterName': 'test-cluster',
            }
        }

        # Mock the response from get_cluster_policy to raise an error
        mock_kafka_client.get_cluster_policy.side_effect = ClientError(
            {'Error': {'Code': 'NotFoundException', 'Message': 'Policy not found'}},
            'GetClusterPolicy',
        )

        # Mock the response from list_policies
        mock_iam_client.get_paginator.return_value.paginate.return_value = [{'Policies': []}]

        # Set up parameters
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'

        # Call the function
        result = list_customer_iam_access(
            cluster_arn=cluster_arn, client_manager=mock_client_manager
        )

        # Verify the result
        assert 'cluster_info' in result
        assert 'resource_policies' in result
        assert 'matching_policies' in result

        assert result['resource_policies'] == []
        assert result['matching_policies'] == {}

        # Verify the calls
        mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)
        mock_kafka_client.get_cluster_policy.assert_called_once_with(ClusterArn=cluster_arn)

    def test_list_customer_iam_access_missing_client_manager(self):
        """Test the list_customer_iam_access function with a missing client manager."""
        # Set up parameters
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'

        # Call the function and expect an error
        with pytest.raises(ValueError) as excinfo:
            list_customer_iam_access(cluster_arn=cluster_arn, client_manager=None)

        # Verify the error
        assert 'Client manager must be provided' in str(excinfo.value)

    def test_list_customer_iam_access_invalid_cluster_arn(self):
        """Test the list_customer_iam_access function with an invalid cluster ARN."""
        # Set up parameters
        cluster_arn = 'invalid-arn'
        mock_client_manager = MagicMock()

        # Call the function and expect an error
        with pytest.raises(ValueError) as excinfo:
            list_customer_iam_access(cluster_arn=cluster_arn, client_manager=mock_client_manager)

        # Verify the error
        assert 'cluster_arn must be a valid MSK cluster ARN' in str(excinfo.value)

    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.get_cluster_name')
    def test_list_customer_iam_access_exact_match(self, mock_get_cluster_name):
        """Test the list_customer_iam_access function with an exact ARN match."""
        # Set up mocks
        mock_kafka_client = MagicMock()
        mock_iam_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda service: {
            'kafka': mock_kafka_client,
            'iam': mock_iam_client,
        }[service]

        # Mock the response from describe_cluster
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {
                'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                'ClusterName': 'test-cluster',
            }
        }

        # Mock the response from get_cluster_policy
        mock_kafka_client.get_cluster_policy.return_value = {'Policy': '{}'}

        # Mock the response from list_policies
        mock_iam_client.get_paginator.return_value.paginate.return_value = [
            {
                'Policies': [
                    {
                        'PolicyName': 'ExactMatchPolicy',
                        'Arn': 'arn:aws:iam::123456789012:policy/ExactMatchPolicy',
                        'DefaultVersionId': 'v1',
                    }
                ]
            }
        ]

        # Mock the response from get_policy_version - exact match
        mock_iam_client.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': ['kafka:GetBootstrapBrokers'],
                            'Resource': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                        }
                    ],
                }
            }
        }

        # Mock the response from list_entities_for_policy
        mock_iam_client.list_entities_for_policy.return_value = {
            'PolicyRoles': [{'RoleName': 'ExactMatchRole', 'RoleId': 'AROAEXAMPLEID1'}]
        }

        # Mock the get_cluster_name function
        mock_get_cluster_name.return_value = 'test-cluster'

        # Set up parameters
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'

        # Call the function
        result = list_customer_iam_access(
            cluster_arn=cluster_arn, client_manager=mock_client_manager
        )

        # Verify the result
        assert 'matching_policies' in result
        assert 'arn:aws:iam::123456789012:policy/ExactMatchPolicy' in result['matching_policies']
        assert (
            result['matching_policies']['arn:aws:iam::123456789012:policy/ExactMatchPolicy'][
                'ResourceType'
            ]
            == 'exact'
        )

    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.get_cluster_name')
    def test_list_customer_iam_access_global_wildcard(self, mock_get_cluster_name):
        """Test the list_customer_iam_access function with a global wildcard match."""
        # Set up mocks
        mock_kafka_client = MagicMock()
        mock_iam_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda service: {
            'kafka': mock_kafka_client,
            'iam': mock_iam_client,
        }[service]

        # Mock the response from describe_cluster
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {
                'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                'ClusterName': 'test-cluster',
            }
        }

        # Mock the response from get_cluster_policy
        mock_kafka_client.get_cluster_policy.return_value = {'Policy': '{}'}

        # Mock the response from list_policies
        mock_iam_client.get_paginator.return_value.paginate.return_value = [
            {
                'Policies': [
                    {
                        'PolicyName': 'GlobalWildcardPolicy',
                        'Arn': 'arn:aws:iam::123456789012:policy/GlobalWildcardPolicy',
                        'DefaultVersionId': 'v1',
                    }
                ]
            }
        ]

        # Mock the response from get_policy_version - global wildcard
        mock_iam_client.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': ['kafka:GetBootstrapBrokers'],
                            'Resource': '*',
                        }
                    ],
                }
            }
        }

        # Mock the response from list_entities_for_policy
        mock_iam_client.list_entities_for_policy.return_value = {
            'PolicyRoles': [{'RoleName': 'GlobalWildcardRole', 'RoleId': 'AROAEXAMPLEID2'}]
        }

        # Mock the get_cluster_name function
        mock_get_cluster_name.return_value = 'test-cluster'

        # Set up parameters
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'

        # Call the function
        result = list_customer_iam_access(
            cluster_arn=cluster_arn, client_manager=mock_client_manager
        )

        # Verify the result
        assert 'matching_policies' in result
        assert (
            'arn:aws:iam::123456789012:policy/GlobalWildcardPolicy' in result['matching_policies']
        )
        assert (
            result['matching_policies']['arn:aws:iam::123456789012:policy/GlobalWildcardPolicy'][
                'ResourceType'
            ]
            == 'global_wildcard'
        )

    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.get_cluster_name')
    def test_list_customer_iam_access_cluster_wildcard(self, mock_get_cluster_name):
        """Test the list_customer_iam_access function with a cluster wildcard match."""
        # Set up mocks
        mock_kafka_client = MagicMock()
        mock_iam_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda service: {
            'kafka': mock_kafka_client,
            'iam': mock_iam_client,
        }[service]

        # Mock the response from describe_cluster
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {
                'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                'ClusterName': 'test-cluster',
            }
        }

        # Mock the response from get_cluster_policy
        mock_kafka_client.get_cluster_policy.return_value = {'Policy': '{}'}

        # Mock the response from list_policies
        mock_iam_client.get_paginator.return_value.paginate.return_value = [
            {
                'Policies': [
                    {
                        'PolicyName': 'ClusterWildcardPolicy',
                        'Arn': 'arn:aws:iam::123456789012:policy/ClusterWildcardPolicy',
                        'DefaultVersionId': 'v1',
                    }
                ]
            }
        ]

        # Mock the response from get_policy_version - cluster wildcard
        mock_iam_client.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': ['kafka:GetBootstrapBrokers'],
                            'Resource': 'arn:aws:kafka:us-east-1:*:cluster/test-cluster/*',
                        }
                    ],
                }
            }
        }

        # Mock the response from list_entities_for_policy
        mock_iam_client.list_entities_for_policy.return_value = {
            'PolicyRoles': [{'RoleName': 'ClusterWildcardRole', 'RoleId': 'AROAEXAMPLEID3'}]
        }

        # Mock the get_cluster_name function
        mock_get_cluster_name.return_value = 'test-cluster'

        # Set up parameters
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'

        # Call the function
        result = list_customer_iam_access(
            cluster_arn=cluster_arn, client_manager=mock_client_manager
        )

        # Verify the result
        assert 'matching_policies' in result
        assert (
            'arn:aws:iam::123456789012:policy/ClusterWildcardPolicy' in result['matching_policies']
        )
        assert (
            result['matching_policies']['arn:aws:iam::123456789012:policy/ClusterWildcardPolicy'][
                'ResourceType'
            ]
            == 'cluster_wildcard'
        )

    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.get_cluster_name')
    def test_list_customer_iam_access_pattern_match(self, mock_get_cluster_name):
        """Test the list_customer_iam_access function with a pattern match."""
        # Set up mocks
        mock_kafka_client = MagicMock()
        mock_iam_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda service: {
            'kafka': mock_kafka_client,
            'iam': mock_iam_client,
        }[service]

        # Mock the response from describe_cluster
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {
                'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                'ClusterName': 'test-cluster',
            }
        }

        # Mock the response from get_cluster_policy
        mock_kafka_client.get_cluster_policy.return_value = {'Policy': '{}'}

        # Mock the response from list_policies
        mock_iam_client.get_paginator.return_value.paginate.return_value = [
            {
                'Policies': [
                    {
                        'PolicyName': 'PatternMatchPolicy',
                        'Arn': 'arn:aws:iam::123456789012:policy/PatternMatchPolicy',
                        'DefaultVersionId': 'v1',
                    }
                ]
            }
        ]

        # Mock the response from get_policy_version - pattern match
        mock_iam_client.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': ['kafka:GetBootstrapBrokers'],
                            'Resource': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-*/*',
                        }
                    ],
                }
            }
        }

        # Mock the response from list_entities_for_policy
        mock_iam_client.list_entities_for_policy.return_value = {
            'PolicyRoles': [{'RoleName': 'PatternMatchRole', 'RoleId': 'AROAEXAMPLEID4'}]
        }

        # Mock the get_cluster_name function
        mock_get_cluster_name.return_value = 'test-cluster'

        # Set up parameters
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'

        # Call the function
        result = list_customer_iam_access(
            cluster_arn=cluster_arn, client_manager=mock_client_manager
        )

        # Verify the result
        assert 'matching_policies' in result
        assert 'arn:aws:iam::123456789012:policy/PatternMatchPolicy' in result['matching_policies']
        assert (
            result['matching_policies']['arn:aws:iam::123456789012:policy/PatternMatchPolicy'][
                'ResourceType'
            ]
            == 'pattern_match'
        )

    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.get_cluster_name')
    def test_list_customer_iam_access_string_action(self, mock_get_cluster_name):
        """Test the list_customer_iam_access function with action as a string."""
        # Set up mocks
        mock_kafka_client = MagicMock()
        mock_iam_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda service: {
            'kafka': mock_kafka_client,
            'iam': mock_iam_client,
        }[service]

        # Mock the response from describe_cluster
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {
                'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                'ClusterName': 'test-cluster',
            }
        }

        # Mock the response from get_cluster_policy
        mock_kafka_client.get_cluster_policy.return_value = {'Policy': '{}'}

        # Mock the response from list_policies
        mock_iam_client.get_paginator.return_value.paginate.return_value = [
            {
                'Policies': [
                    {
                        'PolicyName': 'StringActionPolicy',
                        'Arn': 'arn:aws:iam::123456789012:policy/StringActionPolicy',
                        'DefaultVersionId': 'v1',
                    }
                ]
            }
        ]

        # Mock the response from get_policy_version - action as a string
        mock_iam_client.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': 'kafka:GetBootstrapBrokers',
                            'Resource': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/*',
                        }
                    ],
                }
            }
        }

        # Mock the response from list_entities_for_policy
        mock_iam_client.list_entities_for_policy.return_value = {
            'PolicyRoles': [{'RoleName': 'StringActionRole', 'RoleId': 'AROAEXAMPLEID5'}]
        }

        # Mock the get_cluster_name function
        mock_get_cluster_name.return_value = 'test-cluster'

        # Set up parameters
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'

        # Call the function
        result = list_customer_iam_access(
            cluster_arn=cluster_arn, client_manager=mock_client_manager
        )

        # Verify the result
        assert 'matching_policies' in result
        assert 'arn:aws:iam::123456789012:policy/StringActionPolicy' in result['matching_policies']

    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.get_cluster_name')
    def test_list_customer_iam_access_kafka_cluster_action(self, mock_get_cluster_name):
        """Test the list_customer_iam_access function with kafka-cluster action prefix."""
        # Set up mocks
        mock_kafka_client = MagicMock()
        mock_iam_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda service: {
            'kafka': mock_kafka_client,
            'iam': mock_iam_client,
        }[service]

        # Mock the response from describe_cluster
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {
                'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                'ClusterName': 'test-cluster',
            }
        }

        # Mock the response from get_cluster_policy
        mock_kafka_client.get_cluster_policy.return_value = {'Policy': '{}'}

        # Mock the response from list_policies
        mock_iam_client.get_paginator.return_value.paginate.return_value = [
            {
                'Policies': [
                    {
                        'PolicyName': 'KafkaClusterPolicy',
                        'Arn': 'arn:aws:iam::123456789012:policy/KafkaClusterPolicy',
                        'DefaultVersionId': 'v1',
                    }
                ]
            }
        ]

        # Mock the response from get_policy_version - kafka-cluster action
        mock_iam_client.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': ['kafka-cluster:Connect', 'kafka-cluster:DescribeCluster'],
                            'Resource': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/*',
                        }
                    ],
                }
            }
        }

        # Mock the response from list_entities_for_policy
        mock_iam_client.list_entities_for_policy.return_value = {
            'PolicyRoles': [{'RoleName': 'KafkaClusterRole', 'RoleId': 'AROAEXAMPLEID6'}]
        }

        # Mock the get_cluster_name function
        mock_get_cluster_name.return_value = 'test-cluster'

        # Set up parameters
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'

        # Call the function
        result = list_customer_iam_access(
            cluster_arn=cluster_arn, client_manager=mock_client_manager
        )

        # Verify the result
        assert 'matching_policies' in result
        assert 'arn:aws:iam::123456789012:policy/KafkaClusterPolicy' in result['matching_policies']

    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.get_cluster_name')
    def test_list_customer_iam_access_string_resource(self, mock_get_cluster_name):
        """Test the list_customer_iam_access function with resource as a string."""
        # Set up mocks
        mock_kafka_client = MagicMock()
        mock_iam_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda service: {
            'kafka': mock_kafka_client,
            'iam': mock_iam_client,
        }[service]

        # Mock the response from describe_cluster
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {
                'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                'ClusterName': 'test-cluster',
            }
        }

        # Mock the response from get_cluster_policy
        mock_kafka_client.get_cluster_policy.return_value = {'Policy': '{}'}

        # Mock the response from list_policies
        mock_iam_client.get_paginator.return_value.paginate.return_value = [
            {
                'Policies': [
                    {
                        'PolicyName': 'StringResourcePolicy',
                        'Arn': 'arn:aws:iam::123456789012:policy/StringResourcePolicy',
                        'DefaultVersionId': 'v1',
                    }
                ]
            }
        ]

        # Mock the response from get_policy_version - resource as a string
        mock_iam_client.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': ['kafka:GetBootstrapBrokers'],
                            'Resource': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/*',
                        }
                    ],
                }
            }
        }

        # Mock the response from list_entities_for_policy
        mock_iam_client.list_entities_for_policy.return_value = {
            'PolicyRoles': [{'RoleName': 'StringResourceRole', 'RoleId': 'AROAEXAMPLEID7'}]
        }

        # Mock the get_cluster_name function
        mock_get_cluster_name.return_value = 'test-cluster'

        # Set up parameters
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'

        # Call the function
        result = list_customer_iam_access(
            cluster_arn=cluster_arn, client_manager=mock_client_manager
        )

        # Verify the result
        assert 'matching_policies' in result
        assert (
            'arn:aws:iam::123456789012:policy/StringResourcePolicy' in result['matching_policies']
        )
