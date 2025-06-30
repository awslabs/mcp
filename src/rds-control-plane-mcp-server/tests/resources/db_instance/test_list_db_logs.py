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

"""Tests for list_db_log_files resource."""

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from awslabs.rds_control_plane_mcp_server.resources.db_instance.list_db_logs import list_db_log_files
from awslabs.rds_control_plane_mcp_server.common.constants import RESOURCE_PREFIX_DB_LOG_FILES


@pytest.mark.asyncio
async def test_list_db_log_files_success():
    """Test successful retrieval of DB log files."""
    instance_id = 'test-mysql-instance'

    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [{
        'DescribeDBLogFiles': [
            {
                'LogFileName': 'error/mysql-error.log',
                'LastWritten': 1625097600000,  
                'Size': 12345
            },
            {
                'LogFileName': 'error/mysql-error-previous.log',
                'LastWritten': 1625011200000,
                'Size': 5678
            },
            {
                'LogFileName': 'general/mysql.log',
                'LastWritten': 1625097600000,
                'Size': 87654
            }
        ]
    }]

    mock_client = MagicMock()
    mock_client.get_paginator.return_value = mock_paginator

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await list_db_log_files(instance_id)

        mock_client.get_paginator.assert_called_once_with('describe_db_log_files')
        mock_paginator.paginate.assert_called_once()

        result_dict = json.loads(result)
        assert 'log_files' in result_dict
        assert 'count' in result_dict
        assert 'resource_uri' in result_dict

        assert result_dict['count'] == 3
        assert result_dict['resource_uri'] == RESOURCE_PREFIX_DB_LOG_FILES.format(instance_id)

        assert len(result_dict['log_files']) == 3

        log_file = result_dict['log_files'][0]
        assert log_file['log_file_name'] == 'error/mysql-error.log'
        assert 'last_written' in log_file
        assert log_file['size'] == 12345


@pytest.mark.asyncio
async def test_list_db_log_files_empty():
    """Test list_db_log_files when no logs are available."""
    instance_id = 'test-empty-logs'

    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [{
        'DescribeDBLogFiles': []
    }]

    mock_client = MagicMock()
    mock_client.get_paginator.return_value = mock_paginator

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await list_db_log_files(instance_id)

        result_dict = json.loads(result)
        assert result_dict['log_files'] == []
        assert result_dict['count'] == 0


@pytest.mark.asyncio
async def test_list_db_log_files_with_pagination():
    """Test list_db_log_files with pagination."""
    instance_id = 'test-paginated-logs'

    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {
            'DescribeDBLogFiles': [
                {
                    'LogFileName': 'log1.log',
                    'LastWritten': 1625097600000,
                    'Size': 1000
                }
            ]
        },
        {
            'DescribeDBLogFiles': [
                {
                    'LogFileName': 'log2.log',
                    'LastWritten': 1625097700000,
                    'Size': 2000
                }
            ]
        }
    ]

    mock_client = MagicMock()
    mock_client.get_paginator.return_value = mock_paginator

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await list_db_log_files(instance_id)

        result_dict = json.loads(result)
        assert len(result_dict['log_files']) == 2
        assert result_dict['count'] == 2

        log_file_names = [log['log_file_name'] for log in result_dict['log_files']]
        assert 'log1.log' in log_file_names
        assert 'log2.log' in log_file_names


@pytest.mark.asyncio
async def test_list_db_log_files_client_error():
    """Test list_db_log_files when the client raises an error."""
    from botocore.exceptions import ClientError

    instance_id = 'non-existent-instance'
    mock_client = MagicMock()
    mock_client.get_paginator.side_effect = ClientError(
        {
            'Error': {
                'Code': 'DBInstanceNotFound',
                'Message': f'DBInstance {instance_id} not found'
            }
        },
        'DescribeDBLogFiles'
    )

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await list_db_log_files(instance_id)

        result_dict = json.loads(result)
        assert 'error' in result_dict
        assert 'error_code' in result_dict
        assert result_dict['error_code'] == 'DBInstanceNotFound'
        assert f'DBInstance {instance_id} not found' in result_dict['error_message']
