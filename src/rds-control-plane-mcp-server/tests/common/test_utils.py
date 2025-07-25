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

"""Tests for the utils module in the RDS Control Plane MCP Server."""

import datetime
from awslabs.rds_control_plane_mcp_server.common.utils import (
    add_mcp_tags,
    convert_datetime_to_string,
    format_rds_api_response,
    handle_paginated_aws_api_call,
)
from awslabs.rds_control_plane_mcp_server.tools.db_cluster.utils import format_cluster_info
from awslabs.rds_control_plane_mcp_server.tools.db_instance.utils import format_instance_info
from unittest.mock import MagicMock


class TestPaginationUtils:
    """Test pagination utility functions."""

    def test_handle_paginated_aws_api_call(self):
        """Test paginated API call handling."""
        mock_paginated_operation = MagicMock()
        mock_paginator = MagicMock()
        mock_paginated_operation.get_paginator.return_value = mock_paginator

        # Mock page iterator
        mock_pages = [{'TestKey': [{'id': 1}, {'id': 2}]}, {'TestKey': [{'id': 3}]}]
        mock_paginator.paginate.return_value = mock_pages

        def format_func(item):
            return f'formatted_{item["id"]}'

        result = handle_paginated_aws_api_call(
            client=mock_paginated_operation,
            paginator_name='test_paginator',
            operation_parameters={'param': 'value'},
            format_function=format_func,
            result_key='TestKey',
        )

        assert result == ['formatted_1', 'formatted_2', 'formatted_3']
        mock_paginated_operation.get_paginator.assert_called_once_with('test_paginator')


class TestResponseFormatting:
    """Test response formatting utilities."""

    def test_format_rds_api_response_removes_metadata(self):
        """Test that ResponseMetadata is removed from AWS responses."""
        response = {'Data': 'test', 'ResponseMetadata': {'RequestId': '123'}}

        result = format_rds_api_response(response)

        assert 'ResponseMetadata' not in result
        assert result['Data'] == 'test'

    def test_convert_datetime_to_string_datetime(self):
        """Test datetime conversion to string."""
        dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
        result = convert_datetime_to_string(dt)
        assert result == '2023-01-01T12:00:00'

    def test_convert_datetime_to_string_dict(self):
        """Test datetime conversion in nested dictionary."""
        dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
        obj = {'date': dt, 'name': 'test'}

        result = convert_datetime_to_string(obj)

        assert result['date'] == '2023-01-01T12:00:00'
        assert result['name'] == 'test'

    def test_convert_datetime_to_string_list(self):
        """Test datetime conversion in list."""
        dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
        obj = [dt, 'test']

        result = convert_datetime_to_string(obj)

        assert result[0] == '2023-01-01T12:00:00'
        assert result[1] == 'test'


class TestTaggingUtils:
    """Test tagging utility functions."""

    def test_add_mcp_tags(self):
        """Test adding MCP tags to parameters."""
        params = {'Tags': [{'Key': 'existing', 'Value': 'tag'}]}

        result = add_mcp_tags(params)

        assert len(result['Tags']) == 3
        assert {'Key': 'mcp_server_version', 'Value': '0.1.0'} in result['Tags']
        assert {'Key': 'created_by', 'Value': 'rds-control-plane-mcp-server'} in result['Tags']

    def test_add_mcp_tags_no_existing_tags(self):
        """Test adding MCP tags when no existing tags."""
        params = {}

        result = add_mcp_tags(params)

        assert len(result['Tags']) == 2
        assert {'Key': 'mcp_server_version', 'Value': '0.1.0'} in result['Tags']


class TestFormattingUtils:
    """Test formatting utility functions."""

    def test_format_cluster_info(self):
        """Test cluster information formatting."""
        cluster = {
            'DBClusterIdentifier': 'test-cluster',
            'Status': 'available',
            'Engine': 'aurora-mysql',
            'DBClusterMembers': [{'DBInstanceIdentifier': 'instance-1', 'IsClusterWriter': True}],
            'TagList': [{'Key': 'env', 'Value': 'test'}],
        }

        result = format_cluster_info(cluster)

        assert result['cluster_id'] == 'test-cluster'
        assert result['status'] == 'available'
        assert len(result['members']) == 1
        assert result['tags']['env'] == 'test'

    def test_format_instance_info(self):
        """Test instance information formatting."""
        instance = {
            'DBInstanceIdentifier': 'test-instance',
            'DBInstanceStatus': 'available',
            'Engine': 'mysql',
            'Endpoint': {'Address': 'test.amazonaws.com', 'Port': 3306},
            'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-123', 'Status': 'active'}],
            'TagList': [{'Key': 'env', 'Value': 'test'}],
        }

        result = format_instance_info(instance)

        assert result['instance_id'] == 'test-instance'
        assert result['endpoint']['address'] == 'test.amazonaws.com'
        assert result['endpoint']['port'] == 3306
        assert len(result['vpc_security_groups']) == 1
        assert result['tags']['env'] == 'test'
