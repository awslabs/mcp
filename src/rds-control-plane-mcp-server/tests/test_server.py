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

"""Tests for the RDS Control Plane MCP Server resources."""

import json
import pytest
from awslabs.rds_control_plane_mcp_server.models import (
    DBLogFileSummary,
    PerformanceReportSummary,
)
from awslabs.rds_control_plane_mcp_server.resources import (
    get_cluster_detail_resource,
    get_cluster_list_resource,
    get_instance_detail_resource,
    get_instance_list_resource,
)
from awslabs.rds_control_plane_mcp_server.server import (
    get_cluster_resource,
    get_instance_resource,
    list_clusters_resource,
    list_db_log_files_resource,
    list_instances_resource,
    list_performance_reports_resource,
    read_performance_report_resource,
)
from datetime import datetime
from unittest.mock import ANY, AsyncMock, MagicMock, patch


class TestClusterResources:
    """Test cases for cluster-related resource endpoints."""

    @pytest.mark.asyncio
    async def test_get_cluster_list_resource(self, mock_rds_client):
        """Test retrieving cluster list resource."""
        with patch(
            'awslabs.rds_control_plane_mcp_server.resources.asyncio.to_thread'
        ) as mock_to_thread:
            mock_to_thread.return_value = {
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

            result = await get_cluster_list_resource(mock_rds_client)

            # Verify result
            result_json = json.loads(result)
            assert result_json['count'] == 1, 'Expected one cluster in result'
            assert result_json['clusters'][0]['cluster_id'] == 'test-cluster', (
                'Incorrect cluster ID'
            )
            assert result_json['clusters'][0]['engine'] == 'aurora-mysql', 'Incorrect engine'
            assert result_json['resource_uri'] == 'aws-rds://db-cluster', 'Incorrect resource URI'

    @pytest.mark.asyncio
    async def test_get_cluster_detail_resource(self, mock_rds_client):
        """Test retrieving cluster detail resource."""
        with patch(
            'awslabs.rds_control_plane_mcp_server.resources.asyncio.to_thread'
        ) as mock_to_thread:
            mock_to_thread.return_value = {
                'DBClusters': [
                    {
                        'DBClusterIdentifier': 'test-cluster',
                        'Engine': 'aurora-mysql',
                        'EngineVersion': '5.7.12',
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

            result = await get_cluster_detail_resource('test-cluster', mock_rds_client)

            result_json = json.loads(result)
            assert result_json['cluster_id'] == 'test-cluster', 'Incorrect cluster ID'
            assert result_json['engine'] == 'aurora-mysql', 'Incorrect engine'
            assert result_json['engine_version'] == '5.7.12', 'Incorrect engine version'
            assert result_json['status'] == 'available', 'Incorrect status'
            assert result_json['members'][0]['instance_id'] == 'test-instance-1', (
                'Incorrect member instance'
            )
            assert result_json['resource_uri'] == 'aws-rds://db-cluster/test-cluster', (
                'Incorrect resource URI'
            )

    @pytest.mark.asyncio
    async def test_list_clusters_resource(self):
        """Test the list_clusters_resource function."""
        with (
            patch('awslabs.rds_control_plane_mcp_server.server._rds_client') as mock_rds_client,
            patch(
                'awslabs.rds_control_plane_mcp_server.server.get_cluster_list_resource'
            ) as mock_get_cluster_list,
        ):
            mock_get_cluster_list.return_value = json.dumps(
                {
                    'clusters': [{'cluster_id': 'test-cluster'}],
                    'count': 1,
                    'resource_uri': 'aws-rds://db-cluster',
                }
            )

            result = await list_clusters_resource()

            mock_get_cluster_list.assert_called_once_with(rds_client=mock_rds_client)

            result_json = json.loads(result)
            assert result_json['count'] == 1, 'Expected one cluster in result'
            assert result_json['clusters'][0]['cluster_id'] == 'test-cluster', (
                'Incorrect cluster ID'
            )
            assert result_json['resource_uri'] == 'aws-rds://db-cluster', 'Incorrect resource URI'

    @pytest.mark.asyncio
    async def test_get_cluster_resource(self):
        """Test the get_cluster_resource function."""
        with (
            patch('awslabs.rds_control_plane_mcp_server.server._rds_client') as mock_rds_client,
            patch(
                'awslabs.rds_control_plane_mcp_server.server.get_cluster_detail_resource'
            ) as mock_get_cluster_detail,
        ):
            mock_get_cluster_detail.return_value = json.dumps(
                {
                    'cluster_id': 'test-cluster',
                    'engine': 'aurora-mysql',
                    'status': 'available',
                    'resource_uri': 'aws-rds://db-cluster/test-cluster',
                }
            )

            result = await get_cluster_resource('test-cluster')

            mock_get_cluster_detail.assert_called_once_with(
                cluster_id='test-cluster', rds_client=mock_rds_client
            )

            result_json = json.loads(result)
            assert result_json['cluster_id'] == 'test-cluster', 'Incorrect cluster ID'
            assert result_json['resource_uri'] == 'aws-rds://db-cluster/test-cluster', (
                'Incorrect resource URI'
            )

    @pytest.mark.asyncio
    async def test_error_handling_in_get_cluster_list_resource(self):
        """Test error handling in get_cluster_list_resource function."""
        mock_rds_client = MagicMock()
        mock_rds_client.describe_db_clusters = MagicMock(side_effect=Exception('Test error'))

        with patch(
            'awslabs.rds_control_plane_mcp_server.resources.asyncio.to_thread',
            side_effect=Exception('Test error'),
        ):
            result = await get_cluster_list_resource(mock_rds_client)

            result_json = json.loads(result)
            assert 'error' in result_json, 'Expected error key in response'
            assert 'Test error' in result_json['error_message'], 'Incorrect error message'


class TestInstanceResources:
    """Test cases for instance-related resource endpoints."""

    @pytest.mark.asyncio
    async def test_get_instance_list_resource(self, mock_rds_client):
        """Test retrieving instance list resource."""
        with patch(
            'awslabs.rds_control_plane_mcp_server.resources.asyncio.to_thread'
        ) as mock_to_thread:
            mock_to_thread.return_value = {
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
                        'VpcSecurityGroups': [
                            {
                                'VpcSecurityGroupId': 'sg-67890',
                                'Status': 'active',
                            }
                        ],
                        'TagList': [
                            {
                                'Key': 'Environment',
                                'Value': 'Development',
                            }
                        ],
                    },
                ]
            }

            result = await get_instance_list_resource(mock_rds_client)

            result_json = json.loads(result)
            assert result_json['count'] == 2, 'Expected two instances in result'
            assert result_json['instances'][0]['instance_id'] == 'test-instance-1', (
                'Incorrect first instance ID'
            )
            assert result_json['instances'][1]['instance_id'] == 'test-instance-2', (
                'Incorrect second instance ID'
            )
            assert result_json['instances'][0]['db_cluster'] == 'test-cluster', (
                'Incorrect cluster association'
            )
            assert result_json['instances'][1]['db_cluster'] is None, (
                'Expected null cluster association'
            )
            assert result_json['resource_uri'] == 'aws-rds://db-instance', 'Incorrect resource URI'

    @pytest.mark.asyncio
    async def test_get_instance_detail_resource(self, mock_rds_client):
        """Test retrieving instance detail resource."""
        with patch(
            'awslabs.rds_control_plane_mcp_server.resources.asyncio.to_thread'
        ) as mock_to_thread:
            mock_to_thread.return_value = {
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
                        'PreferredBackupWindow': '07:00-09:00',
                        'PreferredMaintenanceWindow': 'sun:05:00-sun:06:00',
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

            result = await get_instance_detail_resource('test-instance-1', mock_rds_client)

            result_json = json.loads(result)
            assert result_json['instance_id'] == 'test-instance-1', 'Incorrect instance ID'
            assert result_json['db_cluster'] == 'test-cluster', 'Incorrect cluster association'
            assert result_json['engine'] == 'aurora-mysql', 'Incorrect engine'
            assert result_json['storage']['encrypted'] is True, (
                'Incorrect storage encryption setting'
            )
            assert (
                result_json['endpoint']['address']
                == 'test-instance-1.abc123.us-east-1.rds.amazonaws.com'
            ), 'Incorrect endpoint address'
            assert result_json['endpoint']['port'] == 3306, 'Incorrect endpoint port'
            assert result_json['resource_uri'] == 'aws-rds://db-instance/test-instance-1', (
                'Incorrect resource URI'
            )

    @pytest.mark.asyncio
    async def test_list_instances_resource(self):
        """Test the list_instances_resource function."""
        with (
            patch('awslabs.rds_control_plane_mcp_server.server._rds_client') as mock_rds_client,
            patch(
                'awslabs.rds_control_plane_mcp_server.server.get_instance_list_resource'
            ) as mock_get_instance_list,
        ):
            mock_get_instance_list.return_value = json.dumps(
                {
                    'instances': [
                        {'instance_id': 'test-instance-1'},
                        {'instance_id': 'test-instance-2'},
                    ],
                    'count': 2,
                    'resource_uri': 'aws-rds://db-instance',
                }
            )

            result = await list_instances_resource()

            mock_get_instance_list.assert_called_once_with(rds_client=mock_rds_client)

            result_json = json.loads(result)
            assert result_json['count'] == 2, 'Expected two instances in result'
            assert result_json['instances'][0]['instance_id'] == 'test-instance-1', (
                'Incorrect first instance ID'
            )
            assert result_json['instances'][1]['instance_id'] == 'test-instance-2', (
                'Incorrect second instance ID'
            )
            assert result_json['resource_uri'] == 'aws-rds://db-instance', 'Incorrect resource URI'

    @pytest.mark.asyncio
    async def test_get_instance_resource(self):
        """Test the get_instance_resource function."""
        with (
            patch('awslabs.rds_control_plane_mcp_server.server._rds_client') as mock_rds_client,
            patch(
                'awslabs.rds_control_plane_mcp_server.server.get_instance_detail_resource'
            ) as mock_get_instance_detail,
        ):
            mock_get_instance_detail.return_value = json.dumps(
                {
                    'instance_id': 'test-instance-1',
                    'db_cluster': 'test-cluster',
                    'status': 'available',
                    'resource_uri': 'aws-rds://db-instance/test-instance-1',
                }
            )

            result = await get_instance_resource('test-instance-1')

            mock_get_instance_detail.assert_called_once_with('test-instance-1', mock_rds_client)

            result_json = json.loads(result)
            assert result_json['instance_id'] == 'test-instance-1', 'Incorrect instance ID'
            assert result_json['db_cluster'] == 'test-cluster', 'Incorrect cluster association'
            assert result_json['resource_uri'] == 'aws-rds://db-instance/test-instance-1', (
                'Incorrect resource URI'
            )

    @pytest.mark.asyncio
    async def test_error_handling_in_get_instance_detail_resource(self):
        """Test error handling in get_instance_detail_resource function for non-existent instance."""
        with patch(
            'awslabs.rds_control_plane_mcp_server.resources.asyncio.to_thread'
        ) as mock_to_thread:
            mock_to_thread.return_value = {'DBInstances': []}

            result = await get_instance_detail_resource('non-existent-instance', MagicMock())

            result_json = json.loads(result)
            assert 'error' in result_json, 'Expected error key in response'
            assert 'non-existent-instance' in result_json['error'], 'Incorrect error message'


class TestPerformanceReportsResource:
    """Test cases for performance reports resource endpoints."""

    @pytest.mark.asyncio
    async def test_list_performance_reports_success(self):
        """Test successful retrieval of performance reports list."""
        dbi_resource_identifier = 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        mock_reports = [
            PerformanceReportSummary(
                analysis_report_id='report-123',
                create_time=datetime(2025, 6, 1, 12, 0, 0),
                start_time=datetime(2025, 6, 1, 10, 0, 0),
                end_time=datetime(2025, 6, 1, 11, 0, 0),
                status='SUCCEEDED',
            ),
            PerformanceReportSummary(
                analysis_report_id='report-456',
                create_time=datetime(2025, 6, 2, 12, 0, 0),
                start_time=datetime(2025, 6, 2, 10, 0, 0),
                end_time=datetime(2025, 6, 2, 11, 0, 0),
                status='RUNNING',
            ),
        ]

        with patch(
            'awslabs.rds_control_plane_mcp_server.server.list_performance_reports',
            new_callable=AsyncMock,
            return_value=mock_reports,
        ) as mock_list_reports:
            result = await list_performance_reports_resource(dbi_resource_identifier)

        mock_list_reports.assert_called_once_with(dbi_resource_identifier, ANY)

        assert len(result) == 2, 'Expected two performance reports'
        assert isinstance(result[0], PerformanceReportSummary), (
            'Expected PerformanceReportSummary instance'
        )
        assert result[0].analysis_report_id == 'report-123', 'Incorrect report ID'
        assert result[0].status == 'SUCCEEDED', 'Incorrect report status'

        assert isinstance(result[1], PerformanceReportSummary), (
            'Expected PerformanceReportSummary instance'
        )
        assert result[1].analysis_report_id == 'report-456', 'Incorrect report ID'
        assert result[1].status == 'RUNNING', 'Incorrect report status'

    @pytest.mark.asyncio
    async def test_list_performance_reports_error(self):
        """Test handling of errors when listing performance reports."""
        dbi_resource_identifier = 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        error_response = {
            'error': 'Failed to list performance reports',
            'details': 'Access denied',
        }

        with patch(
            'awslabs.rds_control_plane_mcp_server.server.list_performance_reports',
            new_callable=AsyncMock,
            return_value=error_response,
        ) as mock_list_reports:
            result = await list_performance_reports_resource(dbi_resource_identifier)

        mock_list_reports.assert_called_once()
        assert result == error_response, 'Expected error response to be returned'
        assert result.get('error') == 'Failed to list performance reports', (
            'Incorrect error message'
        )
        assert result.get('details') == 'Access denied', 'Incorrect error details'

    @pytest.mark.asyncio
    async def test_read_performance_report_success(self):
        """Test successful retrieval of a specific performance report."""
        dbi_resource_identifier = 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        report_identifier = 'report-123'
        mock_report_content = {
            'AnalysisReportId': 'report-123',
            'Status': 'SUCCEEDED',
            'AnalysisData': {},
        }

        with patch(
            'awslabs.rds_control_plane_mcp_server.server.read_performance_report',
            new_callable=AsyncMock,
            return_value=mock_report_content,
        ) as mock_read_report:
            result = await read_performance_report_resource(
                dbi_resource_identifier, report_identifier
            )

        mock_read_report.assert_called_once_with(
            dbi_resource_identifier=dbi_resource_identifier,
            report_id=report_identifier,
            pi_client=ANY,
        )

        assert result == mock_report_content, 'Expected mock report content to be returned'
        assert result['AnalysisReportId'] == 'report-123', 'Incorrect analysis report ID'
        assert result['Status'] == 'SUCCEEDED', 'Incorrect status'

    @pytest.mark.asyncio
    async def test_read_performance_report_error(self):
        """Test handling of errors when reading a performance report."""
        dbi_resource_identifier = 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        report_identifier = 'report-999'  # Non-existent report
        error_response = {
            'error': 'Failed to read performance report',
            'details': 'Report not found',
        }

        with patch(
            'awslabs.rds_control_plane_mcp_server.server.read_performance_report',
            new_callable=AsyncMock,
            return_value=error_response,
        ) as mock_read_report:
            result = await read_performance_report_resource(
                dbi_resource_identifier, report_identifier
            )

        mock_read_report.assert_called_once()
        assert result == error_response, 'Expected error response to be returned'
        assert result.get('error') == 'Failed to read performance report', (
            'Incorrect error message'
        )
        assert result.get('details') == 'Report not found', 'Incorrect error details'


class TestDBLogFilesResource:
    """Test cases for DB log files resource endpoints."""

    @pytest.mark.asyncio
    async def test_list_db_log_files_success(self):
        """Test successful retrieval of database log files."""
        db_instance_identifier = 'instance-123'
        mock_log_files = [
            DBLogFileSummary(
                log_file_name='error.log', last_written=datetime(2025, 6, 1, 12, 0, 0), size=1024
            ),
            DBLogFileSummary(
                log_file_name='slow-query.log',
                last_written=datetime(2025, 6, 1, 12, 30, 0),
                size=2048,
            ),
        ]

        with patch(
            'awslabs.rds_control_plane_mcp_server.server.list_db_log_files',
            new_callable=AsyncMock,
            return_value=mock_log_files,
        ) as mock_list_logs:
            result = await list_db_log_files_resource(db_instance_identifier)

        mock_list_logs.assert_called_once_with(
            db_instance_identifier=db_instance_identifier, rds_client=ANY
        )

        assert len(result) == 2, 'Expected two log files'
        assert isinstance(result[0], DBLogFileSummary), 'Expected DBLogFileSummary instance'
        assert result[0].log_file_name == 'error.log', 'Incorrect log file name'
        assert result[0].size == 1024, 'Incorrect log file size'
        assert isinstance(result[0].last_written, datetime), 'Expected datetime instance'

        assert isinstance(result[1], DBLogFileSummary), 'Expected DBLogFileSummary instance'
        assert result[1].log_file_name == 'slow-query.log', 'Incorrect log file name'
        assert result[1].size == 2048, 'Incorrect log file size'
        assert isinstance(result[1].last_written, datetime), 'Expected datetime instance'

    @pytest.mark.asyncio
    async def test_list_db_log_files_error(self):
        """Test handling of errors when listing database log files."""
        db_instance_identifier = 'instance-123'
        error_response = {'error': 'Failed to list log files', 'details': 'Access denied'}

        with patch(
            'awslabs.rds_control_plane_mcp_server.server.list_db_log_files',
            new_callable=AsyncMock,
            return_value=error_response,
        ) as mock_list_logs:
            result = await list_db_log_files_resource(db_instance_identifier)

        mock_list_logs.assert_called_once()
        assert result == error_response, 'Expected error response to be returned'
        assert result.get('error') == 'Failed to list log files', 'Incorrect error message'
        assert result.get('details') == 'Access denied', 'Incorrect error details'
