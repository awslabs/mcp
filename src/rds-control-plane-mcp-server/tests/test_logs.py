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

"""Tests for the logs module which handles RDS database log file operations."""

import pytest
from awslabs.rds_control_plane_mcp_server.config import get_pagination_config
from awslabs.rds_control_plane_mcp_server.logs import list_db_log_files
from awslabs.rds_control_plane_mcp_server.models import DBLogFileSummary
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


class TestListDBLogFiles:
    """Tests for the list_db_log_files function."""

    @pytest.mark.asyncio
    async def test_success(self, mock_rds_client):
        """Test successful retrieval and processing of log files."""
        db_instance_identifier = 'test-instance'
        mock_log_files = [
            {
                'LogFileName': 'log1.log',
                'LastWritten': 1624500000000,  # milliseconds since epoch
                'Size': 1024,
            },
            {
                'LogFileName': 'log2.log',
                'LastWritten': 1624600000000,
                'Size': 2048,
            },
        ]

        mock_paginator = MagicMock()
        mock_page_iterator = MagicMock()
        mock_paginator.paginate.return_value = mock_page_iterator
        mock_page_iterator.__iter__.return_value = [{'DescribeDBLogFiles': mock_log_files}]
        mock_rds_client.get_paginator.return_value = mock_paginator

        result = await list_db_log_files(db_instance_identifier, mock_rds_client)

        mock_rds_client.get_paginator.assert_called_once_with('describe_db_log_files')
        mock_paginator.paginate.assert_called_once_with(
            DBInstanceIdentifier=db_instance_identifier,
            FileSize=1,
            PaginationConfig=get_pagination_config(),
        )

        assert isinstance(result, list)
        assert len(result) == 2

        assert isinstance(result[0], DBLogFileSummary)
        assert result[0].log_file_name == 'log1.log'
        assert result[0].size == 1024
        assert result[0].last_written == datetime.fromtimestamp(1624500000000 / 1000)

        assert isinstance(result[1], DBLogFileSummary)
        assert result[1].log_file_name == 'log2.log'
        assert result[1].size == 2048
        assert result[1].last_written == datetime.fromtimestamp(1624600000000 / 1000)

    @pytest.mark.asyncio
    async def test_empty_response(self, mock_rds_client):
        """Test handling of empty response from RDS API."""
        db_instance_identifier = 'test-instance'

        mock_paginator = MagicMock()
        mock_page_iterator = MagicMock()
        mock_paginator.paginate.return_value = mock_page_iterator
        mock_page_iterator.__iter__.return_value = [{'DescribeDBLogFiles': []}]
        mock_rds_client.get_paginator.return_value = mock_paginator

        result = await list_db_log_files(db_instance_identifier, mock_rds_client)

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_multiple_pages(self, mock_rds_client):
        """Test handling of paginated results from RDS API."""
        db_instance_identifier = 'test-instance'
        mock_log_files_page1 = [
            {
                'LogFileName': 'log1.log',
                'LastWritten': 1624500000000,
                'Size': 1024,
            },
        ]
        mock_log_files_page2 = [
            {
                'LogFileName': 'log2.log',
                'LastWritten': 1624600000000,
                'Size': 2048,
            },
        ]

        mock_paginator = MagicMock()
        mock_page_iterator = MagicMock()
        mock_paginator.paginate.return_value = mock_page_iterator
        mock_page_iterator.__iter__.return_value = [
            {'DescribeDBLogFiles': mock_log_files_page1},
            {'DescribeDBLogFiles': mock_log_files_page2},
        ]
        mock_rds_client.get_paginator.return_value = mock_paginator

        result = await list_db_log_files(db_instance_identifier, mock_rds_client)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0].log_file_name == 'log1.log'
        assert result[1].log_file_name == 'log2.log'

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_rds_client):
        """Test exception handling when RDS API fails."""
        db_instance_identifier = 'test-instance'
        mock_exception = Exception('Test error')
        mock_error_response = {'error': 'Test error'}

        mock_rds_client.get_paginator.side_effect = mock_exception

        with patch(
            'awslabs.rds_control_plane_mcp_server.logs.handle_aws_error',
            new_callable=AsyncMock,
            return_value=mock_error_response,
        ) as mock_handle_error:
            result = await list_db_log_files(db_instance_identifier, mock_rds_client)

            mock_handle_error.assert_called_once()
            error_msg = mock_handle_error.call_args[0][0]
            assert db_instance_identifier in error_msg
            assert mock_handle_error.call_args[0][1] == mock_exception
            assert result == mock_error_response
