"""Tests for CloudWatch Application Signals MCP Server."""

import pytest
from awslabs.cloudwatch_appsignals_mcp_server.server import (
    get_service_detail,
    list_monitored_services,
    remove_null_values,
    main,
)
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
import sys


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


def test_remove_null_values():
    """Test remove_null_values function."""
    # Test with mix of None and non-None values
    input_dict = {
        'key1': 'value1',
        'key2': None,
        'key3': 'value3',
        'key4': None,
        'key5': 0,  # Should not be removed
        'key6': '',  # Should not be removed
        'key7': False,  # Should not be removed
    }
    
    result = remove_null_values(input_dict)
    
    assert result == {
        'key1': 'value1',
        'key3': 'value3',
        'key5': 0,
        'key6': '',
        'key7': False,
    }
    assert 'key2' not in result
    assert 'key4' not in result


@pytest.mark.asyncio
async def test_list_monitored_services_client_error():
    """Test ClientError handling in list_monitored_services."""
    error_response = {
        'Error': {
            'Code': 'AccessDeniedException',
            'Message': 'User is not authorized to perform this action'
        }
    }
    
    with patch('boto3.client') as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.list_services.side_effect = ClientError(error_response, 'ListServices')
        
        result = await list_monitored_services()
        
        assert 'AWS Error: User is not authorized to perform this action' in result


@pytest.mark.asyncio
async def test_list_monitored_services_general_exception():
    """Test general exception handling in list_monitored_services."""
    with patch('boto3.client') as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.list_services.side_effect = Exception('Unexpected error occurred')
        
        result = await list_monitored_services()
        
        assert 'Error: Unexpected error occurred' in result


@pytest.mark.asyncio
async def test_get_service_detail_client_error():
    """Test ClientError handling in get_service_detail."""
    mock_list_response = {
        'ServiceSummaries': [
            {'KeyAttributes': {'Name': 'test-service', 'Type': 'AWS::ECS::Service'}}
        ]
    }
    
    error_response = {
        'Error': {
            'Code': 'ResourceNotFoundException',
            'Message': 'Service not found in Application Signals'
        }
    }
    
    with patch('boto3.client') as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.list_services.return_value = mock_list_response
        mock_client.get_service.side_effect = ClientError(error_response, 'GetService')
        
        result = await get_service_detail('test-service')
        
        assert 'AWS Error: Service not found in Application Signals' in result


@pytest.mark.asyncio
async def test_get_service_detail_general_exception():
    """Test general exception handling in get_service_detail."""
    mock_list_response = {
        'ServiceSummaries': [
            {'KeyAttributes': {'Name': 'test-service', 'Type': 'AWS::ECS::Service'}}
        ]
    }
    
    with patch('boto3.client') as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.list_services.return_value = mock_list_response
        mock_client.get_service.side_effect = Exception('Unexpected error in get_service')
        
        result = await get_service_detail('test-service')
        
        assert 'Error: Unexpected error in get_service' in result


def test_main_normal_execution():
    """Test normal execution of main function."""
    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.mcp') as mock_mcp:
        main()
        mock_mcp.run.assert_called_once_with(transport='stdio')


def test_main_keyboard_interrupt():
    """Test KeyboardInterrupt handling in main function."""
    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.mcp') as mock_mcp:
        mock_mcp.run.side_effect = KeyboardInterrupt()
        
        # Should not raise an exception
        main()
        
        mock_mcp.run.assert_called_once_with(transport='stdio')


def test_main_general_exception():
    """Test general exception handling in main function."""
    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.mcp') as mock_mcp:
        mock_mcp.run.side_effect = Exception('Server error')
        
        with pytest.raises(Exception, match='Server error'):
            main()
        
        mock_mcp.run.assert_called_once_with(transport='stdio')
