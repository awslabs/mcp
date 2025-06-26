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

"""Tests for the RDS Control Plane MCP Server."""

import argparse
import pytest
from awslabs.rds_control_plane_mcp_server.common.constants import MCP_SERVER_VERSION
from awslabs.rds_control_plane_mcp_server.resources.clusters.get_cluster_detail import (
    GetClusterDetailHandler,
)

# Handler imports
from awslabs.rds_control_plane_mcp_server.resources.clusters.list_clusters import (
    ListClustersHandler,
)
from awslabs.rds_control_plane_mcp_server.resources.instances.get_instance_detail import (
    GetInstanceDetailHandler,
)
from awslabs.rds_control_plane_mcp_server.resources.instances.list_db_logs import ListDBLogsHandler
from awslabs.rds_control_plane_mcp_server.resources.instances.list_instances import (
    ListInstancesHandler,
)
from awslabs.rds_control_plane_mcp_server.resources.instances.list_performance_reports import (
    ListPerformanceReportHandler,
)
from awslabs.rds_control_plane_mcp_server.resources.instances.read_performance_report import (
    ReadPerformanceReportHandler,
)

# Server imports
from awslabs.rds_control_plane_mcp_server.server import create_mcp_server, main
from mcp.server.fastmcp import FastMCP
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
@patch('awslabs.rds_control_plane_mcp_server.server.FastMCP')
async def test_server_initialization(mock_fastmcp):
    """Test the server initialization by creating a server instance."""
    server = create_mcp_server()

    mock_fastmcp.assert_called_once()
    args, kwargs = mock_fastmcp.call_args
    assert args[0] == 'awslabs.rds-control-plane-mcp-server'
    assert kwargs['version'] == MCP_SERVER_VERSION
    assert 'instructions' in kwargs
    assert (
        'This server provides access to Amazon RDS database instances and clusters.'
        in kwargs['instructions']
    )
    assert 'dependencies' in kwargs
    assert 'pydantic' in kwargs['dependencies']
    assert 'loguru' in kwargs['dependencies']
    assert 'boto3' in kwargs['dependencies']
    assert server == mock_fastmcp.return_value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'port,max_items,readonly,read_only_str',
    [
        (8888, 100, 'true', 'True'),
        (9999, 50, 'false', 'False'),
    ],
)
@patch('argparse.ArgumentParser.parse_args')
@patch('awslabs.rds_control_plane_mcp_server.server._rds_client', MagicMock())
@patch('awslabs.rds_control_plane_mcp_server.server._pi_client', MagicMock())
@patch('awslabs.rds_control_plane_mcp_server.server.logger')
@patch('awslabs.rds_control_plane_mcp_server.server.create_mcp_server')
async def test_main_function(
    mock_create_server, mock_logger, mock_parse_args, port, max_items, readonly, read_only_str
):
    """Test the main function with different command-line arguments."""
    mock_parse_args.return_value = argparse.Namespace(
        port=port,
        max_items=max_items,
        readonly=readonly,
    )

    mock_server = MagicMock(spec=FastMCP)
    mock_server.settings = MagicMock()
    mock_create_server.return_value = mock_server

    result = main()

    assert mock_server.settings.port == port
    mock_logger.info.assert_any_call(
        f'Starting RDS Control Plane MCP Server v{MCP_SERVER_VERSION}'
    )
    mock_logger.info.assert_any_call(f'Read-only mode: {read_only_str}')
    mock_logger.info.assert_any_call(f'Max items to fetch: {max_items}')
    mock_server.run.assert_called_once()
    assert result == mock_server


@pytest.mark.asyncio
async def test_list_clusters_handler_initialization():
    """Test that ListClustersHandler is properly initialized."""
    mock_mcp = MagicMock(spec=FastMCP)
    mock_rds_client = MagicMock()

    ListClustersHandler(mock_mcp, mock_rds_client)

    mock_mcp.resource.assert_called_once()
    call_args = mock_mcp.resource.call_args

    assert call_args[1]['uri'] == 'aws-rds://db-cluster'
    assert call_args[1]['name'] == 'ListDBClusters'
    assert 'description' in call_args[1]


@pytest.mark.asyncio
async def test_get_cluster_detail_handler_initialization():
    """Test that GetClusterDetailHandler is properly initialized."""
    mock_mcp = MagicMock(spec=FastMCP)
    mock_rds_client = MagicMock()

    GetClusterDetailHandler(mock_mcp, mock_rds_client)

    mock_mcp.resource.assert_called_once()
    call_args = mock_mcp.resource.call_args

    assert 'aws-rds://db-cluster/{cluster_id}' in call_args[1]['uri']
    assert call_args[1]['name'] == 'GetDBClusterDetail'
    assert 'description' in call_args[1]


@pytest.mark.asyncio
async def test_list_instances_handler_initialization():
    """Test that ListInstancesHandler is properly initialized."""
    mock_mcp = MagicMock(spec=FastMCP)
    mock_rds_client = MagicMock()

    ListInstancesHandler(mock_mcp, mock_rds_client)

    mock_mcp.resource.assert_called_once()
    call_args = mock_mcp.resource.call_args

    assert call_args[1]['uri'] == 'aws-rds://db-instance'
    assert call_args[1]['name'] == 'ListDBInstances'
    assert 'description' in call_args[1]


@pytest.mark.asyncio
async def test_get_instance_detail_handler_initialization():
    """Test that GetInstanceDetailHandler is properly initialized."""
    mock_mcp = MagicMock(spec=FastMCP)
    mock_rds_client = MagicMock()

    GetInstanceDetailHandler(mock_mcp, mock_rds_client)

    mock_mcp.resource.assert_called_once()
    call_args = mock_mcp.resource.call_args

    assert 'aws-rds://db-instance/{instance_id}' in call_args[1]['uri']
    assert call_args[1]['name'] == 'GetDBInstanceDetails'
    assert 'description' in call_args[1]


@pytest.mark.asyncio
async def test_list_db_logs_handler_initialization():
    """Test that ListDBLogsHandler is properly initialized."""
    mock_mcp = MagicMock(spec=FastMCP)
    mock_rds_client = MagicMock()

    ListDBLogsHandler(mock_mcp, mock_rds_client)

    mock_mcp.resource.assert_called_once()
    call_args = mock_mcp.resource.call_args

    assert 'aws-rds://db-instance/{db_instance_identifier}/log' in call_args[1]['uri']
    assert call_args[1]['name'] == 'ListDBLogFiles'
    assert 'description' in call_args[1]


@pytest.mark.asyncio
async def test_list_performance_report_handler_initialization():
    """Test that ListPerformanceReportHandler is properly initialized."""
    mock_mcp = MagicMock(spec=FastMCP)
    mock_pi_client = MagicMock()

    ListPerformanceReportHandler(mock_mcp, mock_pi_client)

    mock_mcp.resource.assert_called_once()
    call_args = mock_mcp.resource.call_args

    assert (
        'aws-rds://db-instance/{dbi_resource_identifier}/performance_report' in call_args[1]['uri']
    )
    assert call_args[1]['name'] == 'ListPerformanceReports'
    assert 'description' in call_args[1]


@pytest.mark.asyncio
async def test_read_performance_report_handler_initialization():
    """Test that ReadPerformanceReportHandler is properly initialized."""
    mock_mcp = MagicMock(spec=FastMCP)
    mock_pi_client = MagicMock()

    ReadPerformanceReportHandler(mock_mcp, mock_pi_client)

    mock_mcp.resource.assert_called_once()
    call_args = mock_mcp.resource.call_args

    assert (
        'aws-rds://db-instance/{dbi_resource_identifier}/performance_report/{report_id}'
        in call_args[1]['uri']
    )
    assert call_args[1]['name'] == 'ReadPerformanceReport'
    assert 'description' in call_args[1]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'attr,expected_values',
    [
        (
            'instructions',
            [
                'This server provides access to Amazon RDS database instances and clusters',
                'View detailed information about RDS DB instances',
                'View detailed information about RDS DB clusters',
                'Access connection endpoints, configuration, and status information',
                'List performance reports and log files for DB instances',
                'The server operates in read-only mode by default',
            ],
        ),
        ('dependencies', ['pydantic', 'loguru', 'boto3']),
    ],
)
@patch('awslabs.rds_control_plane_mcp_server.server.FastMCP')
async def test_server_attributes(mock_fastmcp, attr, expected_values):
    """Test server configuration attributes."""
    create_mcp_server()

    attribute_value = mock_fastmcp.call_args.kwargs[attr]
    for expected in expected_values:
        assert expected in attribute_value
