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

"""Test fixtures for the rds-monitoring-mcp-server tests."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server."""
    return MagicMock()


@pytest.fixture
async def aws_credentials():
    """Mocked AWS Credentials for boto3."""
    import os

    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture
def mock_pi_client():
    """Create a mock Performance Insights client."""
    client = MagicMock()
    client.meta.region_name = 'us-east-1'
    return client


@pytest.fixture
def mock_rds_client(aws_credentials):
    """Create a mock RDS client with detailed mock configuration."""
    client = MagicMock()
    client.meta.region_name = 'us-east-1'

    # Add mock implementations for RDS API calls
    client.describe_db_clusters = MagicMock(
        return_value={
            'DBClusters': [
                {
                    'DBClusterIdentifier': 'test-cluster',
                    'Engine': 'aurora-mysql',
                    'Status': 'available',
                    'Endpoint': 'test-cluster.cluster-abc123.us-east-1.rds.amazonaws.com',
                    'ReaderEndpoint': 'test-cluster.cluster-ro-abc123.us-east-1.rds.amazonaws.com',
                    'MultiAZ': True,
                    'BackupRetentionPeriod': 7,
                    'PreferredBackupWindow': '07:00-09:00',
                    'PreferredMaintenanceWindow': 'sun:05:00-sun:06:00',
                    'DBClusterMembers': [
                        {
                            'DBInstanceIdentifier': 'test-instance-1',
                            'IsClusterWriter': True,
                            'DBClusterParameterGroupStatus': 'in-sync',
                        }
                    ],
                    'VpcSecurityGroups': [
                        {
                            'VpcSecurityGroupId': 'sg-12345',
                            'Status': 'active',
                        }
                    ],
                    'TagList': [
                        {
                            'Key': 'Environment',
                            'Value': 'Test',
                        }
                    ],
                }
            ]
        }
    )

    client.describe_db_instances = MagicMock(
        return_value={
            'DBInstances': [
                {
                    'DBInstanceIdentifier': 'test-instance-1',
                    'DBClusterIdentifier': 'test-cluster',
                    'Engine': 'aurora-mysql',
                    'EngineVersion': '5.7.12',
                    'DBInstanceClass': 'db.r5.large',
                    'DBInstanceStatus': 'available',
                    'AvailabilityZone': 'us-east-1a',
                    'MultiAZ': False,
                    'PubliclyAccessible': False,
                    'StorageType': 'aurora',
                    'StorageEncrypted': True,
                    'Endpoint': {
                        'Address': 'test-instance-1.abc123.us-east-1.rds.amazonaws.com',
                        'Port': 3306,
                        'HostedZoneId': 'Z2R2ITUGPM61AM',
                    },
                    'TagList': [],
                },
                {
                    'DBInstanceIdentifier': 'test-instance-2',
                    'Engine': 'mysql',
                    'EngineVersion': '8.0.23',
                    'DBInstanceClass': 'db.t3.medium',
                    'DBInstanceStatus': 'available',
                    'AvailabilityZone': 'us-east-1b',
                    'MultiAZ': False,
                    'PubliclyAccessible': False,
                    'StorageType': 'gp2',
                    'AllocatedStorage': 20,
                    'StorageEncrypted': False,
                    'Endpoint': {
                        'Address': 'test-instance-2.def456.us-east-1.rds.amazonaws.com',
                        'Port': 3306,
                        'HostedZoneId': 'Z2R2ITUGPM61AM',
                    },
                    'TagList': [],
                },
            ]
        }
    )

    return client


@pytest.fixture
def mock_boto3():
    """Create a mock boto3 module."""
    with patch('boto3.client') as mock_client, patch('boto3.Session') as mock_session:
        mock_pi = MagicMock()
        mock_rds = MagicMock()
        mock_cloudwatch = MagicMock()

        mock_client.side_effect = lambda service, region_name=None: {
            'pi': mock_pi,
            'rds': mock_rds,
            'cloudwatch': mock_cloudwatch,
        }[service]

        mock_session_instance = MagicMock()
        mock_session_instance.client.side_effect = lambda service, region_name=None: {
            'pi': mock_pi,
            'rds': mock_rds,
            'cloudwatch': mock_cloudwatch,
        }[service]
        mock_session.return_value = mock_session_instance

        yield {
            'client': mock_client,
            'Session': mock_session,
            'pi': mock_pi,
            'rds': mock_rds,
            'cloudwatch': mock_cloudwatch,
        }
