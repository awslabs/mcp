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

"""Tests for AWS Carbon Footprint MCP Server."""

import json
import pytest
from awslabs.carbon_footprint_mcp_server.server import (
    create_carbon_export,
    get_export_data,
    get_export_status,
    list_carbon_exports,
    query_carbon_data,
    run_aws_cli_command,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestCarbonFootprintMCPServer:
    """Test cases for Carbon Footprint MCP Server."""

    @pytest.mark.asyncio
    async def test_run_aws_cli_command_success(self):
        """Test successful AWS CLI command execution."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b'{"result": "success"}', b'')

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await run_aws_cli_command(['aws', 'bcm-data-exports', 'list-exports'])
            assert result == {'result': 'success'}

    @pytest.mark.asyncio
    async def test_run_aws_cli_command_failure(self):
        """Test AWS CLI command execution failure."""
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b'', b'Error message')

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with pytest.raises(Exception, match='AWS CLI error: Error message'):
                await run_aws_cli_command(['aws', 'bcm-data-exports', 'list-exports'])

    @pytest.mark.asyncio
    async def test_create_carbon_export_success(self):
        """Test successful carbon export creation."""
        mock_result = {
            'ExportArn': 'arn:aws:bcm-data-exports:us-east-1:123456789012:export/test-export'
        }

        with patch(
            'awslabs.carbon_footprint_mcp_server.server.run_aws_cli_command',
            return_value=mock_result,
        ):
            result = await create_carbon_export(
                export_name='test-export',
                s3_bucket='test-bucket',
                start_date='2024-01-01',
                end_date='2024-01-31',
            )

            result_data = json.loads(result)
            assert result_data['status'] == 'success'
            assert result_data['export_name'] == 'test-export'
            assert 'arn:aws:bcm-data-exports' in result_data['export_arn']

    @pytest.mark.asyncio
    async def test_create_carbon_export_invalid_date(self):
        """Test carbon export creation with invalid date format."""
        result = await create_carbon_export(
            export_name='test-export',
            s3_bucket='test-bucket',
            start_date='invalid-date',
            end_date='2024-01-31',
        )

        result_data = json.loads(result)
        assert result_data['status'] == 'error'
        assert 'time data' in result_data['message']

    @pytest.mark.asyncio
    async def test_list_carbon_exports_success(self):
        """Test successful listing of carbon exports."""
        mock_result = {
            'Exports': [
                {
                    'ExportName': 'carbon-export-1',
                    'ExportArn': 'arn:aws:bcm-data-exports:us-east-1:123456789012:export/carbon-export-1',
                    'ExportStatus': {'StatusCode': 'ACTIVE', 'CreatedAt': '2024-01-01T00:00:00Z'},
                    'Description': 'Test carbon export',
                }
            ]
        }

        with patch(
            'awslabs.carbon_footprint_mcp_server.server.run_aws_cli_command',
            return_value=mock_result,
        ):
            result = await list_carbon_exports()

            result_data = json.loads(result)
            assert result_data['status'] == 'success'
            assert len(result_data['exports']) == 1
            assert result_data['exports'][0]['export_name'] == 'carbon-export-1'

    @pytest.mark.asyncio
    async def test_list_carbon_exports_empty(self):
        """Test listing carbon exports when none exist."""
        mock_result = {'Exports': []}

        with patch(
            'awslabs.carbon_footprint_mcp_server.server.run_aws_cli_command',
            return_value=mock_result,
        ):
            result = await list_carbon_exports()

            result_data = json.loads(result)
            assert result_data['status'] == 'success'
            assert result_data['message'] == 'No carbon exports found'
            assert result_data['exports'] == []

    @pytest.mark.asyncio
    async def test_get_export_status_success(self):
        """Test successful export status retrieval."""
        mock_result = {
            'Export': {
                'ExportName': 'test-export',
                'ExportStatus': {
                    'StatusCode': 'COMPLETED',
                    'StatusReason': 'Export completed successfully',
                    'CreatedAt': '2024-01-01T00:00:00Z',
                    'CompletedAt': '2024-01-01T01:00:00Z',
                },
                'Description': 'Test export',
                'DestinationConfigurations': {
                    'S3Destination': {'S3Bucket': 'test-bucket', 'S3Prefix': 'carbon-exports/'}
                },
            }
        }

        export_arn = 'arn:aws:bcm-data-exports:us-east-1:123456789012:export/test-export'

        with patch(
            'awslabs.carbon_footprint_mcp_server.server.run_aws_cli_command',
            return_value=mock_result,
        ):
            result = await get_export_status(export_arn)

            result_data = json.loads(result)
            assert result_data['status'] == 'success'
            assert result_data['export_name'] == 'test-export'
            assert result_data['current_status'] == 'COMPLETED'

    @pytest.mark.asyncio
    async def test_query_carbon_data_success(self):
        """Test successful carbon data query."""
        result = await query_carbon_data(
            start_date='2024-01-01',
            end_date='2024-01-31',
            service='EC2-Instance',
            group_by='service',
        )

        result_data = json.loads(result)
        assert result_data['status'] == 'success'
        assert result_data['query_parameters']['service_filter'] == 'EC2-Instance'
        assert result_data['query_parameters']['group_by'] == 'service'
        assert 'sql_query' in result_data

    @pytest.mark.asyncio
    async def test_get_export_data_not_complete(self):
        """Test retrieving data from incomplete export."""
        export_arn = 'arn:aws:bcm-data-exports:us-east-1:123456789012:export/test-export'

        # Mock get_export_status to return incomplete status
        mock_status_result = {
            'status': 'success',
            'current_status': 'CREATING',
            'export_name': 'test-export',
        }

        with patch(
            'awslabs.carbon_footprint_mcp_server.server.get_export_status',
            return_value=json.dumps(mock_status_result),
        ):
            result = await get_export_data(export_arn)

            result_data = json.loads(result)
            assert result_data['status'] == 'error'
            assert 'not complete' in result_data['message']

    @pytest.mark.asyncio
    async def test_get_export_data_success(self):
        """Test successful export data retrieval."""
        export_arn = 'arn:aws:bcm-data-exports:us-east-1:123456789012:export/test-export'

        # Mock get_export_status to return completed status
        mock_status_result = {
            'status': 'success',
            'current_status': 'COMPLETED',
            'export_name': 'test-export',
            'destination': {
                'S3Destination': {'S3Bucket': 'test-bucket', 'S3Prefix': 'carbon-exports/'}
            },
        }

        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'carbon-exports/data.csv',
                    'Size': 1024,
                    'LastModified': '2024-01-01T00:00:00Z',  # String instead of datetime
                }
            ]
        }

        with (
            patch(
                'awslabs.carbon_footprint_mcp_server.server.get_export_status',
                return_value=json.dumps(mock_status_result),
            ),
            patch(
                'awslabs.carbon_footprint_mcp_server.server.get_aws_clients',
                return_value={'s3': mock_s3_client, 'region': 'us-east-1'},
            ),
        ):
            result = await get_export_data(export_arn)

            result_data = json.loads(result)
            assert result_data['status'] == 'success'
            assert len(result_data['files']) == 1
            assert result_data['files'][0]['file_key'] == 'carbon-exports/data.csv'


if __name__ == '__main__':
    pytest.main([__file__])
