"""Tests for CloudWatch Application Signals MCP Server."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from awslabs.cloudwatch_appsignals_mcp_server.server import (
    list_monitored_services,
    get_service_detail,
)


@pytest.mark.asyncio
async def test_list_monitored_services_success():
    """Test successful listing of monitored services."""
    mock_response = {
        'ServiceSummaries': [
            {
                'KeyAttributes': {
                    'Name': 'test-service',
                    'Type': 'AWS::ECS::Service',
                    'Environment': 'production',
                }
            }
        ]
    }

    with patch('boto3.client') as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.list_services.return_value = mock_response

        result = await list_monitored_services()

        assert 'Application Signals Services (1 total)' in result
        assert 'test-service' in result
        assert 'AWS::ECS::Service' in result


@pytest.mark.asyncio
async def test_list_monitored_services_empty():
    """Test when no services are found."""
    mock_response = {'ServiceSummaries': []}

    with patch('boto3.client') as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.list_services.return_value = mock_response

        result = await list_monitored_services()

        assert result == 'No services found in Application Signals.'


@pytest.mark.asyncio
async def test_get_service_detail_success():
    """Test successful retrieval of service details."""
    mock_list_response = {
        'ServiceSummaries': [
            {'KeyAttributes': {'Name': 'test-service', 'Type': 'AWS::ECS::Service'}}
        ]
    }

    mock_get_response = {
        'Service': {
            'KeyAttributes': {'Name': 'test-service', 'Type': 'AWS::ECS::Service'},
            'AttributeMaps': [{'Platform': 'ECS', 'Application': 'test-app'}],
            'MetricReferences': [
                {
                    'Namespace': 'AWS/ApplicationSignals',
                    'MetricName': 'Latency',
                    'MetricType': 'GAUGE',
                    'Dimensions': [{'Name': 'Service', 'Value': 'test-service'}],
                }
            ],
            'LogGroupReferences': [{'Identifier': '/aws/ecs/test-service'}],
        }
    }

    with patch('boto3.client') as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.list_services.return_value = mock_list_response
        mock_client.get_service.return_value = mock_get_response

        result = await get_service_detail('test-service')

        assert 'Service Details: test-service' in result
        assert 'AWS::ECS::Service' in result
        assert 'Platform: ECS' in result
        assert 'AWS/ApplicationSignals/Latency' in result
        assert '/aws/ecs/test-service' in result


@pytest.mark.asyncio
async def test_get_service_detail_not_found():
    """Test when service is not found."""
    mock_response = {'ServiceSummaries': []}

    with patch('boto3.client') as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.list_services.return_value = mock_response

        result = await get_service_detail('nonexistent-service')

        assert "Service 'nonexistent-service' not found" in result
