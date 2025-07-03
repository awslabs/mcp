"""Tests for RDS Management MCP Server utilities."""

import datetime
import json
import pytest
from awslabs.rds_control_plane_mcp_server.common import utils
from awslabs.rds_control_plane_mcp_server.common.decorator import handle_exceptions
from awslabs.rds_control_plane_mcp_server.common.models import ClusterModel, InstanceModel
from awslabs.rds_control_plane_mcp_server.resources.db_cluster.utils import format_cluster_info
from awslabs.rds_control_plane_mcp_server.resources.db_instance.utils import format_instance_info
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestConvertDatetimeToString:
    """Tests for convert_datetime_to_string function."""

    def test_convert_datetime_direct(self):
        """Test converting a datetime object directly."""
        now = datetime.datetime.now()
        result = utils.convert_datetime_to_string(now)

        assert result == now.isoformat()

    def test_convert_datetime_in_dict(self):
        """Test converting datetime objects in a dictionary."""
        now = datetime.datetime.now()
        data = {'created': now, 'name': 'test', 'nested': {'updated': now}}

        result = utils.convert_datetime_to_string(data)

        assert isinstance(result['created'], str)
        assert result['created'] == now.isoformat()
        assert isinstance(result['nested']['updated'], str)
        assert result['nested']['updated'] == now.isoformat()

    def test_convert_datetime_in_list(self):
        """Test converting datetime objects in a list."""
        now = datetime.datetime.now()
        data = [now, 'test', {'updated': now}]

        result = utils.convert_datetime_to_string(data)

        assert isinstance(result[0], str)
        assert result[0] == now.isoformat()
        assert isinstance(result[2]['updated'], str)
        assert result[2]['updated'] == now.isoformat()

    def test_convert_non_datetime(self):
        """Test that non-datetime objects are returned unchanged."""
        data = {'name': 'test', 'count': 42, 'enabled': True, 'nested': {'values': [1, 2, 3]}}

        result = utils.convert_datetime_to_string(data)

        assert result == data

    def test_convert_datetime_with_none_values(self):
        """Test converting data with None values."""
        now = datetime.datetime.now()
        data = {'created': now, 'updated': None, 'nested': {'time': now, 'value': None}}

        result = utils.convert_datetime_to_string(data)

        assert isinstance(result['created'], str)
        assert result['created'] == now.isoformat()
        assert result['updated'] is None
        assert isinstance(result['nested']['time'], str)
        assert result['nested']['time'] == now.isoformat()
        assert result['nested']['value'] is None

    def test_convert_datetime_with_mixed_types(self):
        """Test converting data with mixed types including datetimes."""
        now = datetime.datetime.now()
        data = {
            'datetime': now,
            'string': 'test',
            'number': 42,
            'boolean': True,
            'none': None,
            'list': [now, 'test', 42],
            'dict': {'time': now, 'value': 'test'},
            'nested': {'mixed': [{'time': now, 'value': 1}, {'time': now, 'value': 'test'}]},
        }

        result = utils.convert_datetime_to_string(data)

        assert isinstance(result['datetime'], str)
        assert result['datetime'] == now.isoformat()
        assert result['string'] == 'test'
        assert result['number'] == 42
        assert result['boolean'] is True
        assert result['none'] is None
        assert isinstance(result['list'][0], str)
        assert result['list'][0] == now.isoformat()
        assert isinstance(result['dict']['time'], str)
        assert result['dict']['time'] == now.isoformat()
        assert isinstance(result['nested']['mixed'][0]['time'], str)
        assert result['nested']['mixed'][0]['time'] == now.isoformat()

    def test_convert_datetime_in_deeply_nested_structures(self):
        """Test converting datetime in deeply nested structures."""
        now = datetime.datetime.now()
        yesterday = datetime.datetime(now.year, now.month, max(1, now.day - 1))

        data = {
            'toplevel': now,
            'nested': {
                'datetime': yesterday,
                'list': [now, 'string', 123],
                'deeper': {'datetime': now, 'mixed': [yesterday, {'time': now}, [yesterday]]},
            },
            'list_of_dicts': [{'time': now}, {'time': yesterday}],
        }

        result = utils.convert_datetime_to_string(data)

        assert result['toplevel'] == now.isoformat()
        assert result['nested']['datetime'] == yesterday.isoformat()
        assert result['nested']['list'][0] == now.isoformat()
        assert result['nested']['deeper']['datetime'] == now.isoformat()
        assert result['nested']['deeper']['mixed'][0] == yesterday.isoformat()
        assert result['nested']['deeper']['mixed'][1]['time'] == now.isoformat()
        assert result['nested']['deeper']['mixed'][2][0] == yesterday.isoformat()
        assert result['list_of_dicts'][0]['time'] == now.isoformat()
        assert result['list_of_dicts'][1]['time'] == yesterday.isoformat()

        assert result['nested']['list'][1] == 'string'
        assert result['nested']['list'][2] == 123

    def test_convert_datetime_with_custom_objects(self):
        """Test converting datetime with custom objects in the structure."""
        now = datetime.datetime.now()

        class CustomObj:
            def __init__(self):
                self.timestamp = now

        custom = CustomObj()

        result = utils.convert_datetime_to_string(custom)
        assert result == custom

        data = {'obj': custom, 'time': now}
        result = utils.convert_datetime_to_string(data)

        assert result['obj'] == custom
        assert result['time'] == now.isoformat()


@pytest.mark.asyncio
class TestPaginateAwsApiCall:
    """Tests for paginate_aws_api_call function."""

    async def test_paginate_single_page(self):
        """Test pagination with single page of results."""
        mock_client = MagicMock()
        mock_client.return_value = {'Items': [{'id': '1'}, {'id': '2'}]}

        def format_item(item):
            return {'formatted_id': item['id']}

        result = await utils.paginate_aws_api_call(
            client_function=mock_client, format_function=format_item, result_key='Items'
        )

        assert len(result) == 2
        assert result[0]['formatted_id'] == '1'
        assert result[1]['formatted_id'] == '2'
        assert mock_client.call_count == 1

    async def test_paginate_multiple_pages(self):
        """Test pagination with multiple pages of results."""
        mock_client = MagicMock()
        mock_client.side_effect = [
            {'Items': [{'id': '1'}, {'id': '2'}], 'Marker': 'next-page'},
            {'Items': [{'id': '3'}, {'id': '4'}]},
        ]

        def format_item(item):
            return {'formatted_id': item['id']}

        result = await utils.paginate_aws_api_call(
            client_function=mock_client, format_function=format_item, result_key='Items'
        )

        assert len(result) == 4
        assert [item['formatted_id'] for item in result] == ['1', '2', '3', '4']
        assert mock_client.call_count == 2

    async def test_paginate_empty_results(self):
        """Test pagination with empty results."""
        mock_client = MagicMock()
        mock_client.return_value = {'Items': []}

        def format_item(item):
            return item

        result = await utils.paginate_aws_api_call(
            client_function=mock_client, format_function=format_item, result_key='Items'
        )

        assert len(result) == 0
        assert mock_client.call_count == 1

    async def test_paginate_with_kwargs(self):
        """Test pagination with additional keyword arguments."""
        mock_client = MagicMock()
        mock_client.return_value = {'Items': [{'id': '1'}]}

        def format_item(item):
            return item

        await utils.paginate_aws_api_call(
            client_function=mock_client,
            format_function=format_item,
            result_key='Items',
            MaxResults=10,
            Filter='test',
        )

        mock_client.assert_called_once_with(MaxResults=10, Filter='test')

    async def test_paginate_with_format_error(self):
        """Test pagination when format function raises an error."""
        mock_client = MagicMock()
        mock_client.return_value = {'Items': [{'id': '1'}, {'bad_item': True}]}

        def format_item(item):
            return {'formatted_id': item['id']}  # Will raise KeyError for bad_item

        with pytest.raises(KeyError):
            await utils.paginate_aws_api_call(
                client_function=mock_client, format_function=format_item, result_key='Items'
            )

    async def test_paginate_with_exception_handling(self):
        """Test pagination handling when exceptions occur mid-way."""
        mock_client = MagicMock()

        mock_client.side_effect = [
            {'Items': [{'id': '1'}], 'Marker': 'token1'},
            Exception('API error'),
        ]

        with pytest.raises(Exception) as excinfo:
            await utils.paginate_aws_api_call(
                mock_client, format_function=lambda x: x, result_key='Items'
            )

        assert 'API error' in str(excinfo.value)
        assert mock_client.call_count == 2

    async def test_paginate_with_missing_token(self):
        """Test pagination with inconsistent token presence."""
        mock_client = MagicMock()

        mock_client.return_value = {'Items': [{'id': '1'}]}  # No marker/token key

        result = await utils.paginate_aws_api_call(
            mock_client, format_function=lambda x: x, result_key='Items'
        )

        assert len(result) == 1
        assert result[0]['id'] == '1'
        assert mock_client.call_count == 1

    async def test_paginate_with_complex_params(self):
        """Test pagination with complex initial parameters."""
        mock_client = MagicMock()
        mock_client.side_effect = [
            {'Resources': [{'id': '1'}], 'Marker': 'token1'},
            {'Resources': [{'id': '2'}], 'Marker': 'token2'},
            {'Resources': [{'id': '3'}]},
        ]

        # Complex initial parameters including lists and nested dictionaries
        complex_params = {
            'Filters': [
                {'Name': 'state', 'Values': ['running', 'stopped']},
                {'Name': 'type', 'Values': ['t2.micro']},
            ],
            'Config': {'DetailLevel': 'high', 'Options': {'IncludeTags': True}},
        }

        result = await utils.paginate_aws_api_call(
            mock_client, format_function=lambda x: x, result_key='Resources', **complex_params
        )

        assert len(result) == 3
        assert [r['id'] for r in result] == ['1', '2', '3']

        first_call_kwargs = mock_client.call_args_list[0][1]
        assert first_call_kwargs['Filters'] == complex_params['Filters']
        assert first_call_kwargs['Config'] == complex_params['Config']

        assert mock_client.call_args_list[1][1]['Marker'] == 'token1'
        assert mock_client.call_args_list[2][1]['Marker'] == 'token2'


class TestFormatClusterInfo:
    """Tests for format_cluster_info function."""

    def test_format_cluster_info_complete(self, mock_rds_client):
        """Test formatting complete cluster information."""
        response = mock_rds_client.describe_db_clusters()
        cluster = response['DBClusters'][0]

        result = format_cluster_info(cluster)  # type: ignore

        assert isinstance(result, ClusterModel)

        # Check core attributes
        assert result.cluster_id == 'test-cluster'
        assert result.engine == 'aurora-mysql'
        assert result.status == 'available'
        assert result.endpoint == 'test-cluster.cluster-abc123.us-east-1.rds.amazonaws.com'
        assert (
            result.reader_endpoint == 'test-cluster.cluster-ro-abc123.us-east-1.rds.amazonaws.com'
        )
        assert result.multi_az is True
        assert result.backup_retention == 7
        assert result.preferred_backup_window == '07:00-09:00'
        assert result.preferred_maintenance_window == 'sun:05:00-sun:06:00'

        # Check members
        assert len(result.members) == 1
        assert result.members[0].instance_id == 'test-instance-1'
        assert result.members[0].is_writer is True
        assert result.members[0].status == 'in-sync'

        # Check security groups
        assert len(result.vpc_security_groups) == 1
        assert result.vpc_security_groups[0].id == 'sg-12345'
        assert result.vpc_security_groups[0].status == 'active'

        # Check tags
        assert result.tags == {'Environment': 'Test'}

    def test_format_cluster_info_minimal(self):
        """Test formatting minimal cluster information."""
        cluster = {
            'DBClusterIdentifier': 'min-cluster',
            'Status': 'creating',
            'Engine': 'aurora-postgresql',
            'MultiAZ': False,
            'BackupRetentionPeriod': 1,
        }

        result = format_cluster_info(cluster)  # type: ignore

        assert isinstance(result, ClusterModel)
        assert result.cluster_id == 'min-cluster'
        assert result.status == 'creating'
        assert result.engine == 'aurora-postgresql'
        assert result.multi_az is False
        assert result.backup_retention == 1

        # Check optional fields have default values
        assert result.members == []
        assert result.vpc_security_groups == []
        assert result.tags == {}
        assert result.resource_uri is None

    def test_format_cluster_info_with_empty_lists(self):
        """Test formatting cluster information with explicitly empty lists."""
        cluster = {
            'DBClusterIdentifier': 'empty-list-cluster',
            'Status': 'available',
            'Engine': 'aurora-mysql',
            'MultiAZ': True,
            'BackupRetentionPeriod': 7,
            'DBClusterMembers': [],
            'VpcSecurityGroups': [],
            'TagList': [],
        }

        result = format_cluster_info(cluster)  # type: ignore

        assert isinstance(result, ClusterModel)
        assert result.cluster_id == 'empty-list-cluster'

        # Check empty lists are properly handled
        assert result.members == []
        assert result.vpc_security_groups == []
        assert result.tags == {}


class TestFormatInstanceInfo:
    """Tests for format_instance_info function."""

    def test_format_instance_info_complete(self, mock_rds_client):
        """Test formatting complete instance information."""
        response = mock_rds_client.describe_db_instances()
        instance = response['DBInstances'][0]  # Instance with cluster

        result = format_instance_info(instance)  # type: ignore

        assert isinstance(result, InstanceModel)

        # Check core attributes
        assert result.instance_id == 'test-instance-1'
        assert result.status == 'available'
        assert result.engine == 'aurora-mysql'
        assert result.engine_version == '5.7.12'
        assert result.instance_class == 'db.r5.large'
        assert result.availability_zone == 'us-east-1a'
        assert result.multi_az is False
        assert result.publicly_accessible is False
        assert result.db_cluster == 'test-cluster'

        # Check endpoint
        assert result.endpoint.address == 'test-instance-1.abc123.us-east-1.rds.amazonaws.com'
        assert result.endpoint.port == 3306
        assert result.endpoint.hosted_zone_id == 'Z2R2ITUGPM61AM'

        # Check storage
        assert result.storage.type == 'aurora'
        assert result.storage.encrypted is True

    def test_format_instance_info_standalone(self, mock_rds_client):
        """Test formatting standalone instance information."""
        response = mock_rds_client.describe_db_instances()
        instance = response['DBInstances'][1]  # Standalone instance

        result = format_instance_info(instance)

        assert isinstance(result, InstanceModel)

        # Check core attributes
        assert result.instance_id == 'test-instance-2'
        assert result.status == 'available'
        assert result.engine == 'mysql'
        assert result.engine_version == '8.0.23'
        assert result.instance_class == 'db.t3.medium'
        assert result.availability_zone == 'us-east-1b'
        assert result.multi_az is False
        assert result.publicly_accessible is False
        assert result.db_cluster is None  # No cluster for this instance

        # Check endpoint
        assert result.endpoint.address == 'test-instance-2.def456.us-east-1.rds.amazonaws.com'
        assert result.endpoint.port == 3306
        assert result.endpoint.hosted_zone_id == 'Z2R2ITUGPM61AM'

        # Check storage
        assert result.storage.type == 'gp2'
        assert result.storage.allocated == 20
        assert result.storage.encrypted is False

    def test_format_instance_info_minimal(self):
        """Test formatting minimal instance information."""
        instance = {
            'DBInstanceIdentifier': 'min-instance',
            'DBInstanceStatus': 'creating',
            'Engine': 'postgres',
            'DBInstanceClass': 'db.t3.micro',
            'MultiAZ': False,
            'PubliclyAccessible': True,
        }

        result = format_instance_info(instance)  # type: ignore

        assert isinstance(result, InstanceModel)
        assert result.instance_id == 'min-instance'
        assert result.status == 'creating'
        assert result.engine == 'postgres'
        assert result.instance_class == 'db.t3.micro'
        assert result.multi_az is False
        assert result.publicly_accessible is True

        # Check optional fields have default values
        assert result.vpc_security_groups == []
        assert result.tags == {}
        assert result.resource_uri is None

    def test_format_instance_info_with_partial_endpoint(self):
        """Test formatting instance information with partial endpoint data."""
        instance = {
            'DBInstanceIdentifier': 'partial-endpoint-instance',
            'DBInstanceStatus': 'available',
            'Engine': 'mysql',
            'EngineVersion': '5.7',
            'DBInstanceClass': 'db.t3.medium',
            'MultiAZ': False,
            'PubliclyAccessible': False,
            'Endpoint': {
                'Address': 'test.amazon.com',
            },
        }

        result = format_instance_info(instance)  # type: ignore

        assert isinstance(result, InstanceModel)
        assert result.instance_id == 'partial-endpoint-instance'

        # Check partial endpoint is handled properly
        assert result.endpoint.address == 'test.amazon.com'
        assert result.endpoint.port is None
        assert result.endpoint.hosted_zone_id is None

    def test_format_instance_info_with_partial_storage(self):
        """Test formatting instance information with partial storage data."""
        instance = {
            'DBInstanceIdentifier': 'partial-storage-instance',
            'DBInstanceStatus': 'available',
            'Engine': 'mysql',
            'EngineVersion': '5.7',
            'DBInstanceClass': 'db.t3.medium',
            'MultiAZ': False,
            'PubliclyAccessible': False,
            'StorageType': 'gp2',
        }

        result = format_instance_info(instance)  # type: ignore

        assert isinstance(result, InstanceModel)
        assert result.instance_id == 'partial-storage-instance'

        # Check partial storage is handled properly
        assert result.storage.type == 'gp2'
        assert result.storage.allocated is None
        assert result.storage.encrypted is None


@pytest.mark.asyncio
class TestHandleExceptions:
    """Tests for handle_exceptions decorator."""

    @handle_exceptions
    async def mock_aws_operation(self, error=None):
        """Mock AWS operation that may raise an error."""
        if error:
            raise error
        return 'success'

    async def test_handle_client_error(self):
        """Test handling AWS client error."""
        error = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='DescribeDBClusters',
        )

        result = await self.mock_aws_operation(error=error)
        result_dict = json.loads(result)

        assert 'error' in result_dict
        assert 'Access denied' in str(result_dict)
        assert 'error_code' in result_dict
        assert result_dict['error_code'] == 'AccessDenied'

    async def test_handle_general_exception(self):
        """Test handling general exception."""
        error = ValueError('Invalid value')

        result = await self.mock_aws_operation(error=error)
        result_dict = json.loads(result)

        assert 'error' in result_dict
        assert 'Invalid value' in str(result_dict)
        assert 'error_type' in result_dict

    async def test_handle_success(self):
        """Test handling successful operation."""
        result = await self.mock_aws_operation()
        assert result == 'success'

    async def test_handle_aws_api_error_with_detailed_error(self):
        """Test AWS API error handling with detailed error information."""
        error_code = 'InvalidParameterCombination'
        error_message = 'Parameters x and y cannot be used together'

        error_response = {
            'Error': {'Code': error_code, 'Message': error_message, 'Type': 'Sender'}
        }

        error = ClientError(error_response, 'describe_db_clusters')

        result = await self.mock_aws_operation(error=error)
        result_dict = json.loads(result)

        assert 'error' in result_dict
        assert result_dict['error_code'] == error_code
        assert result_dict['error_message'] == error_message
        assert result_dict['operation'] == 'mock_aws_operation'
        assert error_code in result_dict['error']

    async def test_handle_nested_exception(self):
        """Test general error handling with nested exception."""
        try:
            try:
                1 / 0
            except ZeroDivisionError as e:
                raise ValueError('Invalid calculation') from e
        except ValueError as e:
            error = e

        result = await self.mock_aws_operation(error=error)
        result_dict = json.loads(result)

        assert 'error' in result_dict
        assert result_dict['error_type'] == 'ValueError'
        assert result_dict['error_message'] == 'Invalid calculation'
        assert result_dict['operation'] == 'mock_aws_operation'
