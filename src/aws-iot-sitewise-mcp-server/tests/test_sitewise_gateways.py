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

"""Tests for AWS IoT SiteWise Gateway Management Tools."""

import os
import pytest
import sys
from awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways import (
    associate_time_series_to_asset_property,
    create_gateway,
    delete_gateway,
    delete_time_series,
    describe_gateway,
    describe_gateway_capability_configuration,
    describe_time_series,
    disassociate_time_series_from_asset_property,
    list_gateways,
    list_time_series,
    update_gateway,
    update_gateway_capability_configuration,
)
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


# Add the project root directory and its parent to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.dirname(project_dir))
sys.path.insert(0, os.path.dirname(os.path.dirname(project_dir)))


class TestSiteWiseGateways:
    """Test cases for SiteWise gateway management tools."""

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_create_gateway_success(self, mock_boto_client):
        """Test successful gateway creation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'gatewayId': 'gateway-123',
            'gatewayArn': 'arn:aws:iotsitewise:us-east-1:123456789012:gateway/gateway-123',
        }
        mock_client.create_gateway.return_value = mock_response

        gateway_platform = {'greengrassV2': {'coreDeviceThingName': 'test-core-device'}}

        result = create_gateway(
            gateway_name='Test Gateway',
            gateway_platform=gateway_platform,
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['gateway_id'] == 'gateway-123'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_describe_gateway_success(self, mock_boto_client):
        """Test successful gateway description."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'gatewayId': 'gateway-123',
            'gatewayName': 'Test Gateway',
            'gatewayArn': 'arn:aws:iotsitewise:us-east-1:123456789012:gateway/gateway-123',
            'gatewayPlatform': {'greengrassV2': {'coreDeviceThingName': 'test-core-device'}},
            'gatewayCapabilitySummaries': [],
            'creationDate': Mock(),
            'lastUpdateDate': Mock(),
        }
        mock_response['creationDate'].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_response['lastUpdateDate'].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_client.describe_gateway.return_value = mock_response

        result = describe_gateway(gateway_id='gateway-123', region='us-east-1')

        assert result['success'] is True
        assert result['gateway_id'] == 'gateway-123'
        assert result['gateway_name'] == 'Test Gateway'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_list_gateways_success(self, mock_boto_client):
        """Test successful gateway listing."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'gatewaySummaries': [
                {'gatewayId': 'gateway-1', 'gatewayName': 'Gateway 1'},
                {'gatewayId': 'gateway-2', 'gatewayName': 'Gateway 2'},
            ],
            'nextToken': 'token-123',
        }
        mock_client.list_gateways.return_value = mock_response

        result = list_gateways(region='us-east-1')

        assert result['success'] is True
        assert len(result['gateway_summaries']) == 2

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_update_gateway_success(self, mock_boto_client):
        """Test successful gateway update."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        result = update_gateway(
            gateway_id='gateway-123', gateway_name='Updated Gateway', region='us-east-1'
        )

        assert result['success'] is True
        assert 'successfully' in result['message']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_delete_gateway_success(self, mock_boto_client):
        """Test successful gateway deletion."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        result = delete_gateway(gateway_id='gateway-123', region='us-east-1')

        assert result['success'] is True
        assert 'successfully' in result['message']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_describe_time_series_success(self, mock_boto_client):
        """Test successful time series description."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'assetId': 'asset-123',
            'propertyId': 'prop-456',
            'alias': '/test/alias',
            'timeSeriesId': 'ts-789',
            'dataType': 'DOUBLE',
            'dataTypeSpec': '',
            'timeSeriesCreationDate': Mock(),
            'timeSeriesLastUpdateDate': Mock(),
            'timeSeriesArn': 'arn:aws:iotsitewise:us-east-1:123456789012:time-series/ts-789',
        }
        mock_response['timeSeriesCreationDate'].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_response['timeSeriesLastUpdateDate'].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_client.describe_time_series.return_value = mock_response

        result = describe_time_series(alias='/test/alias', region='us-east-1')

        assert result['success'] is True
        assert result['time_series_id'] == 'ts-789'
        assert result['alias'] == '/test/alias'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_list_time_series_with_filters(self, mock_boto_client):
        """Test time series listing with filters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'TimeSeriesSummaries': [
                {'timeSeriesId': 'ts-1', 'alias': '/test/alias1'},
                {'timeSeriesId': 'ts-2', 'alias': '/test/alias2'},
            ],
            'nextToken': 'token-123',
        }
        mock_client.list_time_series.return_value = mock_response

        result = list_time_series(
            region='us-east-1',
            asset_id='asset-123',
            alias_prefix='/test',
            time_series_type='ASSOCIATED',
        )

        assert result['success'] is True
        assert len(result['time_series_summaries']) == 2

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_associate_time_series_success(self, mock_boto_client):
        """Test successful time series association."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        result = associate_time_series_to_asset_property(
            alias='/test/alias',
            asset_id='asset-123',
            property_id='prop-456',
            region='us-east-1',
        )

        assert result['success'] is True
        assert 'successfully' in result['message']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_disassociate_time_series_success(self, mock_boto_client):
        """Test successful time series disassociation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        result = disassociate_time_series_from_asset_property(
            alias='/test/alias',
            asset_id='asset-123',
            property_id='prop-456',
            region='us-east-1',
        )

        assert result['success'] is True
        assert 'successfully' in result['message']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_delete_time_series_success(self, mock_boto_client):
        """Test successful time series deletion."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        result = delete_time_series(alias='/test/alias', region='us-east-1')

        assert result['success'] is True
        assert 'successfully' in result['message']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_gateway_error_handling(self, mock_boto_client):
        """Test error handling in gateway operations."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {'Code': 'ConflictException', 'Message': 'Gateway already exists'}
        }
        mock_client.create_gateway.side_effect = ClientError(error_response, 'CreateGateway')

        result = create_gateway(
            gateway_name='Test Gateway',
            gateway_platform={'greengrassV2': {'coreDeviceThingName': 'test-device'}},
            region='us-east-1',
        )

        assert result['success'] is False
        assert result['error_code'] == 'ConflictException'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_describe_gateway_capability_configuration_success(self, mock_boto_client):
        """Test successful gateway capability configuration description."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'gatewayId': 'gateway-123',
            'capabilityNamespace': 'iotsitewise:opcuacollector:1',
            'capabilityConfiguration': '{"sources": []}',
            'capabilitySyncStatus': 'IN_SYNC',
        }
        mock_client.describe_gateway_capability_configuration.return_value = mock_response

        result = describe_gateway_capability_configuration(
            gateway_id='gateway-123',
            capability_namespace='iotsitewise:opcuacollector:1',
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['gateway_id'] == 'gateway-123'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_update_gateway_capability_configuration_success(self, mock_boto_client):
        """Test successful gateway capability configuration update."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'capabilityNamespace': 'iotsitewise:opcuacollector:1',
            'capabilitySyncStatus': 'OUT_OF_SYNC',
        }
        mock_client.update_gateway_capability_configuration.return_value = mock_response

        result = update_gateway_capability_configuration(
            gateway_id='gateway-123',
            capability_namespace='iotsitewise:opcuacollector:1',
            capability_configuration='{"sources": []}',
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['capability_sync_status'] == 'OUT_OF_SYNC'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_create_gateway_with_tags(self, mock_boto_client):
        """Test create gateway with tags parameter."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'gatewayId': 'gateway-123',
            'gatewayArn': 'arn:aws:iotsitewise:us-east-1:123456789012:gateway/gateway-123',
        }
        mock_client.create_gateway.return_value = mock_response

        gateway_platform = {
            'greengrass': {
                'groupArn': 'arn:aws:greengrass:us-east-1:123456789012:group/test-group'
            }
        }

        # Test with tags
        result = create_gateway(
            gateway_name='Test Gateway',
            gateway_platform=gateway_platform,
            region='us-west-2',
            tags={'Environment': 'Test', 'Project': 'SiteWise'},
        )

        assert result['success'] is True
        mock_client.create_gateway.assert_called_once_with(
            gatewayName='Test Gateway',
            gatewayPlatform=gateway_platform,
            tags={'Environment': 'Test', 'Project': 'SiteWise'},
        )

        # Test without tags
        mock_client.reset_mock()
        result = create_gateway(
            gateway_name='Test Gateway',
            gateway_platform=gateway_platform,
            region='us-east-1',
            tags=None,
        )

        assert result['success'] is True
        mock_client.create_gateway.assert_called_once_with(
            gatewayName='Test Gateway', gatewayPlatform=gateway_platform
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_list_gateways_with_next_token(self, mock_boto_client):
        """Test list gateways with next token parameter."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'gatewaySummaries': [{'id': 'gateway-1', 'name': 'Gateway 1'}],
            'nextToken': 'next-token-123',
        }
        mock_client.list_gateways.return_value = mock_response

        # Test with next_token
        result = list_gateways(region='us-west-2', next_token='prev-token', max_results=100)

        assert result['success'] is True
        mock_client.list_gateways.assert_called_once_with(maxResults=100, nextToken='prev-token')

        # Test without next_token
        mock_client.reset_mock()
        result = list_gateways(
            region='us-east-1',
            next_token=None,
            max_results=25,
        )

        assert result['success'] is True
        mock_client.list_gateways.assert_called_once_with(maxResults=25)

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_list_time_series_with_all_params(self, mock_boto_client):
        """Test list time series with all optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'TimeSeriesSummaries': [
                {'timeSeriesId': 'ts-1', 'alias': '/company/plant/temperature'}
            ],
            'nextToken': 'next-token-123',
        }
        mock_client.list_time_series.return_value = mock_response

        # Test with all parameters
        result = list_time_series(
            region='us-west-2',
            next_token='prev-token',
            max_results=200,
            asset_id='asset-123',
            alias_prefix='/company/plant',
            time_series_type='ASSOCIATED',
        )

        assert result['success'] is True
        mock_client.list_time_series.assert_called_once_with(
            maxResults=200,
            nextToken='prev-token',
            assetId='asset-123',
            aliasPrefix='/company/plant',
            timeSeriesType='ASSOCIATED',
        )

        # Test with minimal parameters
        mock_client.reset_mock()
        result = list_time_series(
            region='us-east-1',
            next_token=None,
            max_results=50,
            asset_id=None,
            alias_prefix=None,
            time_series_type=None,
        )

        assert result['success'] is True
        mock_client.list_time_series.assert_called_once_with(maxResults=50)

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_describe_time_series_with_all_params(self, mock_boto_client):
        """Test describe time series with different parameter combinations."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'assetId': 'asset-123',
            'propertyId': 'prop-456',
            'alias': '/company/plant/temperature',
            'timeSeriesId': 'ts-789',
            'dataType': 'DOUBLE',
            'dataTypeSpec': 'IEEE754',
            'timeSeriesCreationDate': Mock(),
            'timeSeriesLastUpdateDate': Mock(),
            'timeSeriesArn': 'arn:aws:iotsitewise:us-east-1:123456789012:time-series/ts-789',
        }
        mock_response['timeSeriesCreationDate'].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_response['timeSeriesLastUpdateDate'].isoformat.return_value = '2023-01-02T00:00:00Z'
        mock_client.describe_time_series.return_value = mock_response

        # Test with alias only
        result = describe_time_series(
            alias='/company/plant/temperature',
            asset_id=None,
            property_id=None,
            region='us-west-2',
        )

        assert result['success'] is True
        mock_client.describe_time_series.assert_called_once_with(
            alias='/company/plant/temperature'
        )

        # Test with asset_id and property_id
        mock_client.reset_mock()
        result = describe_time_series(
            alias=None,
            asset_id='asset-123',
            property_id='prop-456',
            region='us-east-1',
        )

        assert result['success'] is True
        mock_client.describe_time_series.assert_called_once_with(
            assetId='asset-123', propertyId='prop-456'
        )

        # Test with all parameters
        mock_client.reset_mock()
        result = describe_time_series(
            alias='/company/plant/temperature',
            asset_id='asset-123',
            property_id='prop-456',
            region='us-west-2',
        )

        assert result['success'] is True
        mock_client.describe_time_series.assert_called_once_with(
            alias='/company/plant/temperature',
            assetId='asset-123',
            propertyId='prop-456',
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_associate_time_series_with_client_token(self, mock_boto_client):
        """Test associate time series with client token parameter."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Test with client_token
        result = associate_time_series_to_asset_property(
            alias='/company/plant/temperature',
            asset_id='asset-123',
            property_id='prop-456',
            region='us-west-2',
            client_token='association-token',
        )

        assert result['success'] is True
        mock_client.associate_time_series_to_asset_property.assert_called_once_with(
            alias='/company/plant/temperature',
            assetId='asset-123',
            propertyId='prop-456',
            clientToken='association-token',
        )

        # Test without client_token
        mock_client.reset_mock()
        result = associate_time_series_to_asset_property(
            alias='/company/plant/temperature',
            asset_id='asset-123',
            property_id='prop-456',
            region='us-east-1',
            client_token=None,
        )

        assert result['success'] is True
        mock_client.associate_time_series_to_asset_property.assert_called_once_with(
            alias='/company/plant/temperature',
            assetId='asset-123',
            propertyId='prop-456',
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_disassociate_time_series_with_client_token(self, mock_boto_client):
        """Test disassociate time series with client token parameter."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Test with client_token
        result = disassociate_time_series_from_asset_property(
            alias='/company/plant/temperature',
            asset_id='asset-123',
            property_id='prop-456',
            region='us-west-2',
            client_token='disassociation-token',
        )

        assert result['success'] is True
        mock_client.disassociate_time_series_from_asset_property.assert_called_once_with(
            alias='/company/plant/temperature',
            assetId='asset-123',
            propertyId='prop-456',
            clientToken='disassociation-token',
        )

        # Test without client_token
        mock_client.reset_mock()
        result = disassociate_time_series_from_asset_property(
            alias='/company/plant/temperature',
            asset_id='asset-123',
            property_id='prop-456',
            region='us-east-1',
            client_token=None,
        )

        assert result['success'] is True
        mock_client.disassociate_time_series_from_asset_property.assert_called_once_with(
            alias='/company/plant/temperature',
            assetId='asset-123',
            propertyId='prop-456',
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_delete_time_series_with_all_params(self, mock_boto_client):
        """Test delete time series with different parameter combinations."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Test with alias only
        result = delete_time_series(
            alias='/company/plant/temperature',
            asset_id=None,
            property_id=None,
            region='us-west-2',
            client_token=None,
        )

        assert result['success'] is True
        mock_client.delete_time_series.assert_called_once_with(alias='/company/plant/temperature')

        # Test with asset_id and property_id
        mock_client.reset_mock()
        result = delete_time_series(
            alias=None,
            asset_id='asset-123',
            property_id='prop-456',
            region='us-east-1',
            client_token=None,
        )

        assert result['success'] is True
        mock_client.delete_time_series.assert_called_once_with(
            assetId='asset-123', propertyId='prop-456'
        )

        # Test with all parameters including client_token
        mock_client.reset_mock()
        result = delete_time_series(
            alias='/company/plant/temperature',
            asset_id='asset-123',
            property_id='prop-456',
            region='us-west-2',
            client_token='delete-token',
        )

        assert result['success'] is True
        mock_client.delete_time_series.assert_called_once_with(
            alias='/company/plant/temperature',
            assetId='asset-123',
            propertyId='prop-456',
            clientToken='delete-token',
        )

        # Test without client_token but with alias
        mock_client.reset_mock()
        result = delete_time_series(
            alias='/company/plant/temperature',
            asset_id=None,
            property_id=None,
            region='us-east-1',
            client_token=None,
        )

        assert result['success'] is True
        mock_client.delete_time_series.assert_called_once_with(alias='/company/plant/temperature')

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways.create_sitewise_client')
    def test_all_functions_client_error_handling(self, mock_boto_client):
        """Test that all functions handle ClientError exceptions properly."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'InternalFailureException',
                'Message': 'Internal server error',
            }
        }

        # Test create_gateway error handling
        mock_client.create_gateway.side_effect = ClientError(error_response, 'CreateGateway')
        result = create_gateway(
            gateway_name='Test Gateway',
            gateway_platform={'greengrass': {'groupArn': 'arn:test'}},
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test describe_gateway error handling
        mock_client.describe_gateway.side_effect = ClientError(error_response, 'DescribeGateway')
        result = describe_gateway(gateway_id='gateway-123')
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test list_gateways error handling
        mock_client.list_gateways.side_effect = ClientError(error_response, 'ListGateways')
        result = list_gateways()
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test update_gateway error handling
        mock_client.update_gateway.side_effect = ClientError(error_response, 'UpdateGateway')
        result = update_gateway(gateway_id='gateway-123', gateway_name='Updated Gateway')
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test delete_gateway error handling
        mock_client.delete_gateway.side_effect = ClientError(error_response, 'DeleteGateway')
        result = delete_gateway(gateway_id='gateway-123')
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test describe_gateway_capability_configuration error handling
        mock_client.describe_gateway_capability_configuration.side_effect = ClientError(
            error_response, 'DescribeGatewayCapabilityConfiguration'
        )
        result = describe_gateway_capability_configuration(
            gateway_id='gateway-123',
            capability_namespace='iotsitewise:opcuacollector:1',
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test update_gateway_capability_configuration error handling
        mock_client.update_gateway_capability_configuration.side_effect = ClientError(
            error_response, 'UpdateGatewayCapabilityConfiguration'
        )
        result = update_gateway_capability_configuration(
            gateway_id='gateway-123',
            capability_namespace='iotsitewise:opcuacollector:1',
            capability_configuration='{"sources": []}',
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test list_time_series error handling
        mock_client.list_time_series.side_effect = ClientError(error_response, 'ListTimeSeries')
        result = list_time_series()
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test describe_time_series error handling
        mock_client.describe_time_series.side_effect = ClientError(
            error_response, 'DescribeTimeSeries'
        )
        result = describe_time_series(alias='/company/plant/temperature')
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test associate_time_series_to_asset_property error handling
        mock_client.associate_time_series_to_asset_property.side_effect = ClientError(
            error_response, 'AssociateTimeSeriesToAssetProperty'
        )
        result = associate_time_series_to_asset_property(
            alias='/company/plant/temperature',
            asset_id='asset-123',
            property_id='prop-456',
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test disassociate_time_series_from_asset_property error handling
        mock_client.disassociate_time_series_from_asset_property.side_effect = ClientError(
            error_response, 'DisassociateTimeSeriesFromAssetProperty'
        )
        result = disassociate_time_series_from_asset_property(
            alias='/company/plant/temperature',
            asset_id='asset-123',
            property_id='prop-456',
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test delete_time_series error handling
        mock_client.delete_time_series.side_effect = ClientError(
            error_response, 'DeleteTimeSeries'
        )
        result = delete_time_series(alias='/company/plant/temperature')
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'


if __name__ == '__main__':
    pytest.main([__file__])
