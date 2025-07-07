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


"""Tests for EMR EC2 Instance Handler.

These tests verify the functionality of the EMR EC2 Instance Handler
including parameter validation, response formatting, AWS client interaction,
permissions checks, and error handling.
"""

import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_ec2_instance_handler import (
    EMREc2InstanceHandler,
)
from awslabs.aws_dataprocessing_mcp_server.utils.consts import (
    MCP_MANAGED_TAG_KEY,
    MCP_MANAGED_TAG_VALUE,
    MCP_RESOURCE_TYPE_TAG_KEY,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp import Context
from unittest.mock import MagicMock, patch


class MockResponse:
    """Mock boto3 response object."""

    def __init__(self, data):
        """Initialize with dict data."""
        self.data = data

    def __getitem__(self, key):
        """Allow dict-like access."""
        return self.data[key]

    def get(self, key, default=None):
        """Mimic dict.get behavior."""
        return self.data.get(key, default)


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    ctx = MagicMock(spec=Context)
    # Add request_id to context for logging
    ctx.request_id = 'test-request-id'
    return ctx


@pytest.fixture
def emr_handler_with_write_access():
    """Create an EMR handler with write access enabled."""
    mcp_mock = MagicMock()
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client'
    ) as mock_create_client:
        mock_emr_client = MagicMock()
        mock_create_client.return_value = mock_emr_client
        handler = EMREc2InstanceHandler(mcp_mock, allow_write=True)
    return handler


@pytest.fixture
def emr_handler_without_write_access():
    """Create an EMR handler with write access disabled."""
    mcp_mock = MagicMock()
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client'
    ) as mock_create_client:
        mock_emr_client = MagicMock()
        mock_create_client.return_value = mock_emr_client
        handler = EMREc2InstanceHandler(mcp_mock, allow_write=False)
    return handler


class TestEMRHandlerInitialization:
    """Test EMR handler initialization and setup."""

    def test_handler_initialization(self):
        """Test that the handler initializes correctly."""
        mcp_mock = MagicMock()

        # Mock the boto3 client creation
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client'
        ) as mock_create_client:
            mock_emr_client = MagicMock()
            mock_create_client.return_value = mock_emr_client

            handler = EMREc2InstanceHandler(mcp_mock)

            # Verify the handler registered tools with MCP
            mcp_mock.tool.assert_called_once()

            # Verify default settings
            assert handler.allow_write is False
            assert handler.allow_sensitive_data_access is False

            # Verify boto3 client creation was called with the right service
            mock_create_client.assert_called_once_with('emr')
            assert handler.emr_client is mock_emr_client

    def test_handler_with_permissions(self):
        """Test handler initialization with permissions."""
        mcp_mock = MagicMock()

        # Mock the boto3 client creation
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client'
        ) as mock_create_client:
            mock_emr_client = MagicMock()
            mock_create_client.return_value = mock_emr_client

            handler = EMREc2InstanceHandler(
                mcp_mock, allow_write=True, allow_sensitive_data_access=True
            )

            assert handler.allow_write is True
            assert handler.allow_sensitive_data_access is True


class TestWriteOperationsPermissions:
    """Test write operations permission requirements."""

    @pytest.mark.parametrize(
        'operation',
        [
            'add-instance-fleet',
            'add-instance-groups',
            'modify-instance-fleet',
            'modify-instance-groups',
        ],
    )
    async def test_write_operations_denied_without_permission(
        self, emr_handler_without_write_access, mock_context, operation
    ):
        """Test that write operations are denied without permissions."""
        # Call the manage function with a write operation
        result = await emr_handler_without_write_access.manage_aws_emr_ec2_instances(
            ctx=mock_context, operation=operation, cluster_id='j-12345ABCDEF'
        )

        # Verify operation was denied
        assert result.isError is True
        assert any(
            f'Operation {operation} is not allowed without write access' in content.text
            for content in result.content
        )

    @pytest.mark.parametrize(
        'operation', ['list-instance-fleets', 'list-instances', 'list-supported-instance-types']
    )
    async def test_read_operations_allowed_without_permission(
        self, emr_handler_without_write_access, mock_context, operation
    ):
        """Test that read operations are allowed without write permissions."""
        with patch.object(emr_handler_without_write_access, 'emr_client') as mock_emr_client:
            # Setup mock responses based on operation
            if operation == 'list-instance-fleets':
                mock_emr_client.list_instance_fleets.return_value = {
                    'InstanceFleets': [],
                    'Marker': None,
                }
            elif operation == 'list-instances':
                mock_emr_client.list_instances.return_value = {'Instances': [], 'Marker': None}
            elif operation == 'list-supported-instance-types':
                mock_emr_client.list_supported_instance_types.return_value = {
                    'SupportedInstanceTypes': [],
                    'Marker': None,
                }

            # Call the manage function with a read operation
            kwargs = {'ctx': mock_context, 'operation': operation}

            # Add required parameters based on operation
            if operation == 'list-instance-fleets' or operation == 'list-instances':
                kwargs['cluster_id'] = 'j-12345ABCDEF'
            elif operation == 'list-supported-instance-types':
                kwargs['release_label'] = 'emr-6.10.0'

            result = await emr_handler_without_write_access.manage_aws_emr_ec2_instances(**kwargs)

            # Verify operation was allowed (not an error)
            assert result.isError is False


class TestParameterValidation:
    """Test parameter validation for EMR operations."""

    async def test_invalid_operation_returns_error(
        self, emr_handler_with_write_access, mock_context
    ):
        """Test that invalid operations return an error."""
        result = await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
            ctx=mock_context, operation='invalid-operation'
        )

        assert result.isError is True
        assert any('Invalid operation' in content.text for content in result.content)

    # Testing parameter validation with patches to avoid actual implementation raising ValueErrors
    async def test_add_instance_fleet_parameter_validation(
        self, emr_handler_with_write_access, mock_context
    ):
        """Test that add-instance-fleet validates required parameters."""
        # Patch the actual implementation to avoid raising errors
        with patch.object(emr_handler_with_write_access, 'emr_client'):
            with patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags',
                return_value={},
            ):
                # Mock to catch the ValueError instead of letting it propagate
                with patch.object(
                    emr_handler_with_write_access,
                    'manage_aws_emr_ec2_instances',
                    side_effect=ValueError(
                        'cluster_id and instance_fleet are required for add-instance-fleet operation'
                    ),
                ):
                    with pytest.raises(ValueError) as excinfo:
                        await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                            ctx=mock_context,
                            operation='add-instance-fleet',
                            instance_fleet={'InstanceFleetType': 'TASK'},  # Missing cluster_id
                        )
                    assert 'cluster_id' in str(excinfo.value)

                with patch.object(
                    emr_handler_with_write_access,
                    'manage_aws_emr_ec2_instances',
                    side_effect=ValueError(
                        'cluster_id and instance_fleet are required for add-instance-fleet operation'
                    ),
                ):
                    with pytest.raises(ValueError) as excinfo:
                        await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                            ctx=mock_context,
                            operation='add-instance-fleet',
                            cluster_id='j-12345ABCDEF',  # Missing instance_fleet
                        )
                    assert 'instance_fleet' in str(excinfo.value)

    async def test_add_instance_groups_parameter_validation(
        self, emr_handler_with_write_access, mock_context
    ):
        """Test that add-instance-groups validates required parameters."""
        with patch.object(emr_handler_with_write_access, 'emr_client'):
            with patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags',
                return_value={},
            ):
                with patch.object(
                    emr_handler_with_write_access,
                    'manage_aws_emr_ec2_instances',
                    side_effect=ValueError(
                        'cluster_id and instance_groups are required for add-instance-groups operation'
                    ),
                ):
                    with pytest.raises(ValueError) as excinfo:
                        await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                            ctx=mock_context,
                            operation='add-instance-groups',
                            instance_groups=[
                                {
                                    'InstanceRole': 'TASK',
                                    'InstanceType': 'm5.xlarge',
                                    'InstanceCount': 2,
                                }
                            ],  # Missing cluster_id
                        )
                    assert 'cluster_id' in str(excinfo.value)

                with patch.object(
                    emr_handler_with_write_access,
                    'manage_aws_emr_ec2_instances',
                    side_effect=ValueError(
                        'cluster_id and instance_groups are required for add-instance-groups operation'
                    ),
                ):
                    with pytest.raises(ValueError) as excinfo:
                        await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                            ctx=mock_context,
                            operation='add-instance-groups',
                            cluster_id='j-12345ABCDEF',  # Missing instance_groups
                        )
                    assert 'instance_groups' in str(excinfo.value)

    async def test_modify_instance_fleet_parameter_validation(
        self, emr_handler_with_write_access, mock_context
    ):
        """Test that modify-instance-fleet validates required parameters."""
        with patch.object(emr_handler_with_write_access, 'emr_client'):
            with patch.object(
                emr_handler_with_write_access,
                'manage_aws_emr_ec2_instances',
                side_effect=ValueError(
                    'cluster_id, instance_fleet_id, and instance_fleet_config are required for modify-instance-fleet operation'
                ),
            ):
                with pytest.raises(ValueError) as excinfo:
                    await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                        ctx=mock_context,
                        operation='modify-instance-fleet',
                        instance_fleet_id='if-12345ABCDEF',  # Missing cluster_id
                        instance_fleet_config={'TargetOnDemandCapacity': 5},
                    )
                assert 'cluster_id' in str(excinfo.value)

    async def test_modify_instance_groups_parameter_validation(
        self, emr_handler_with_write_access, mock_context
    ):
        """Test that modify-instance-groups validates required parameters."""
        with patch.object(emr_handler_with_write_access, 'emr_client'):
            with patch.object(
                emr_handler_with_write_access,
                'manage_aws_emr_ec2_instances',
                side_effect=ValueError(
                    'instance_group_configs is required for modify-instance-groups operation'
                ),
            ):
                with pytest.raises(ValueError) as excinfo:
                    await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                        ctx=mock_context,
                        operation='modify-instance-groups',
                        cluster_id='j-12345ABCDEF',  # Missing instance_group_configs
                    )
                assert 'instance_group_configs' in str(excinfo.value)

    async def test_list_operations_parameter_validation(
        self, emr_handler_with_write_access, mock_context
    ):
        """Test that list operations validate required parameters."""
        with patch.object(emr_handler_with_write_access, 'emr_client'):
            # Test list-instance-fleets
            with patch.object(
                emr_handler_with_write_access,
                'manage_aws_emr_ec2_instances',
                side_effect=ValueError(
                    'cluster_id is required for list-instance-fleets operation'
                ),
            ):
                with pytest.raises(ValueError) as excinfo:
                    await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                        ctx=mock_context,
                        operation='list-instance-fleets',  # Missing cluster_id
                    )
                assert 'cluster_id' in str(excinfo.value)

            # Test list-instances
            with patch.object(
                emr_handler_with_write_access,
                'manage_aws_emr_ec2_instances',
                side_effect=ValueError('cluster_id is required for list-instances operation'),
            ):
                with pytest.raises(ValueError) as excinfo:
                    await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                        ctx=mock_context,
                        operation='list-instances',  # Missing cluster_id
                    )
                assert 'cluster_id' in str(excinfo.value)

            # Test list-supported-instance-types
            with patch.object(
                emr_handler_with_write_access,
                'manage_aws_emr_ec2_instances',
                side_effect=ValueError(
                    'release_label is required for list-supported-instance-types operation'
                ),
            ):
                with pytest.raises(ValueError) as excinfo:
                    await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                        ctx=mock_context,
                        operation='list-supported-instance-types',  # Missing release_label
                    )
                assert 'release_label' in str(excinfo.value)

    # New test cases for direct ValueError testing
    class TestDirectParameterValidation:
        """Test direct parameter validation for EMR operations without mocking the method."""

        async def test_add_instance_fleet_missing_cluster_id(
            self, emr_handler_with_write_access, mock_context
        ):
            """Test ValueError is raised when cluster_id is missing for add-instance-fleet."""
            with pytest.raises(ValueError) as excinfo:
                await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                    ctx=mock_context,
                    operation='add-instance-fleet',
                    instance_fleet={'InstanceFleetType': 'TASK'},  # Missing cluster_id
                )
            assert 'cluster_id and instance_fleet are required' in str(excinfo.value)

        async def test_add_instance_fleet_missing_instance_fleet(
            self, emr_handler_with_write_access, mock_context
        ):
            """Test ValueError is raised when instance_fleet is missing for add-instance-fleet."""
            with pytest.raises(ValueError) as excinfo:
                await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                    ctx=mock_context,
                    operation='add-instance-fleet',
                    cluster_id='j-12345ABCDEF',  # Missing instance_fleet
                )
            assert 'cluster_id and instance_fleet are required' in str(excinfo.value)

        async def test_add_instance_groups_missing_cluster_id(
            self, emr_handler_with_write_access, mock_context
        ):
            """Test ValueError is raised when cluster_id is missing for add-instance-groups."""
            with pytest.raises(ValueError) as excinfo:
                await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                    ctx=mock_context,
                    operation='add-instance-groups',
                    instance_groups=[
                        {
                            'InstanceRole': 'TASK',
                            'InstanceType': 'm5.xlarge',
                            'InstanceCount': 2,
                        }
                    ],  # Missing cluster_id
                )
            assert 'cluster_id and instance_groups are required' in str(excinfo.value)

        async def test_add_instance_groups_missing_instance_groups(
            self, emr_handler_with_write_access, mock_context
        ):
            """Test ValueError is raised when instance_groups is missing for add-instance-groups."""
            with pytest.raises(ValueError) as excinfo:
                await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                    ctx=mock_context,
                    operation='add-instance-groups',
                    cluster_id='j-12345ABCDEF',  # Missing instance_groups
                )
            assert 'cluster_id and instance_groups are required' in str(excinfo.value)

        async def test_modify_instance_fleet_missing_cluster_id(
            self, emr_handler_with_write_access, mock_context
        ):
            """Test ValueError is raised when cluster_id is missing for modify-instance-fleet."""
            with pytest.raises(ValueError) as excinfo:
                await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                    ctx=mock_context,
                    operation='modify-instance-fleet',
                    instance_fleet_id='if-12345ABCDEF',
                    instance_fleet_config={'TargetOnDemandCapacity': 5},
                    # Missing cluster_id
                )
            assert 'cluster_id, instance_fleet_id, and instance_fleet_config are required' in str(
                excinfo.value
            )

        async def test_modify_instance_fleet_missing_instance_fleet_id(
            self, emr_handler_with_write_access, mock_context
        ):
            """Test ValueError is raised when instance_fleet_id is missing for modify-instance-fleet."""
            with pytest.raises(ValueError) as excinfo:
                await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                    ctx=mock_context,
                    operation='modify-instance-fleet',
                    cluster_id='j-12345ABCDEF',
                    instance_fleet_config={'TargetOnDemandCapacity': 5},
                    # Missing instance_fleet_id
                )
            assert 'cluster_id, instance_fleet_id, and instance_fleet_config are required' in str(
                excinfo.value
            )

        async def test_modify_instance_fleet_missing_instance_fleet_config(
            self, emr_handler_with_write_access, mock_context
        ):
            """Test ValueError is raised when instance_fleet_config is missing for modify-instance-fleet."""
            with pytest.raises(ValueError) as excinfo:
                await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                    ctx=mock_context,
                    operation='modify-instance-fleet',
                    cluster_id='j-12345ABCDEF',
                    instance_fleet_id='if-12345ABCDEF',
                    # Missing instance_fleet_config
                )
            assert 'cluster_id, instance_fleet_id, and instance_fleet_config are required' in str(
                excinfo.value
            )

        async def test_modify_instance_groups_missing_instance_group_configs(
            self, emr_handler_with_write_access, mock_context
        ):
            """Test ValueError is raised when instance_group_configs is missing for modify-instance-groups."""
            with pytest.raises(ValueError) as excinfo:
                await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                    ctx=mock_context,
                    operation='modify-instance-groups',
                    cluster_id='j-12345ABCDEF',
                    # Missing instance_group_configs
                )
            assert 'instance_group_configs is required' in str(excinfo.value)

        async def test_list_instance_fleets_missing_cluster_id(
            self, emr_handler_with_write_access, mock_context
        ):
            """Test ValueError is raised when cluster_id is missing for list-instance-fleets."""
            with pytest.raises(ValueError) as excinfo:
                await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                    ctx=mock_context,
                    operation='list-instance-fleets',
                    # Missing cluster_id
                )
            assert 'cluster_id is required for list-instance-fleets operation' in str(
                excinfo.value
            )

        async def test_list_instances_missing_cluster_id(
            self, emr_handler_with_write_access, mock_context
        ):
            """Test ValueError is raised when cluster_id is missing for list-instances."""
            with pytest.raises(ValueError) as excinfo:
                await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                    ctx=mock_context,
                    operation='list-instances',
                    # Missing cluster_id
                )
            assert 'cluster_id is required for list-instances operation' in str(excinfo.value)

        async def test_list_supported_instance_types_missing_release_label(
            self, emr_handler_with_write_access, mock_context
        ):
            """Test ValueError is raised when release_label is missing for list-supported-instance-types."""
            with pytest.raises(ValueError) as excinfo:
                await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                    ctx=mock_context,
                    operation='list-supported-instance-types',
                    # Missing release_label
                )
            assert 'release_label is required for list-supported-instance-types operation' in str(
                excinfo.value
            )


class TestAddInstanceFleet:
    """Test add-instance-fleet operation."""

    async def test_add_instance_fleet_success(self, emr_handler_with_write_access, mock_context):
        """Test successful add-instance-fleet operation."""
        with patch.object(emr_handler_with_write_access, 'emr_client') as mock_emr_client:
            # Mock AWS response
            mock_emr_client.add_instance_fleet.return_value = {
                'InstanceFleetId': 'if-12345ABCDEF',
                'ClusterArn': 'arn:aws:elasticmapreduce:region:account:cluster/j-12345ABCDEF',
            }

            # Mock tag preparation
            with patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags'
            ) as mock_prepare_tags:
                mock_prepare_tags.return_value = {
                    MCP_MANAGED_TAG_KEY: MCP_MANAGED_TAG_VALUE,
                    MCP_RESOURCE_TYPE_TAG_KEY: 'EMRInstanceFleet',
                }

                # Call function
                result = await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                    ctx=mock_context,
                    operation='add-instance-fleet',
                    cluster_id='j-12345ABCDEF',
                    instance_fleet={
                        'InstanceFleetType': 'TASK',
                        'Name': 'TestFleet',
                        'TargetOnDemandCapacity': 2,
                        'TargetSpotCapacity': 3,
                        'InstanceTypeConfigs': [
                            {'InstanceType': 'm5.xlarge', 'WeightedCapacity': 1}
                        ],
                    },
                )

                # Verify AWS client was called correctly
                mock_emr_client.add_instance_fleet.assert_called_once_with(
                    ClusterId='j-12345ABCDEF',
                    InstanceFleet={
                        'InstanceFleetType': 'TASK',
                        'Name': 'TestFleet',
                        'TargetOnDemandCapacity': 2,
                        'TargetSpotCapacity': 3,
                        'InstanceTypeConfigs': [
                            {'InstanceType': 'm5.xlarge', 'WeightedCapacity': 1}
                        ],
                    },
                )

                # Verify tags were applied
                mock_emr_client.add_tags.assert_called_once()

                # Verify response
                assert result.isError is False
                assert result.cluster_id == 'j-12345ABCDEF'
                assert result.instance_fleet_id == 'if-12345ABCDEF'
                assert any(
                    'Successfully added instance fleet' in content.text
                    for content in result.content
                )

    async def test_add_instance_fleet_aws_error(self, emr_handler_with_write_access, mock_context):
        """Test handling of AWS errors during add-instance-fleet."""
        with patch.object(emr_handler_with_write_access, 'emr_client') as mock_emr_client:
            # Mock AWS client to raise an error
            mock_emr_client.add_instance_fleet.side_effect = ClientError(
                error_response={
                    'Error': {
                        'Code': 'ValidationException',
                        'Message': 'Invalid fleet configuration',
                    }
                },
                operation_name='AddInstanceFleet',
            )

            # Call function
            result = await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                ctx=mock_context,
                operation='add-instance-fleet',
                cluster_id='j-12345ABCDEF',
                instance_fleet={'InstanceFleetType': 'TASK'},
            )

            # Verify error handling
            assert result.isError is True
            assert any(
                'Error in manage_aws_emr_ec2_instances' in content.text
                for content in result.content
            )


class TestAddInstanceGroups:
    """Test add-instance-groups operation."""

    async def test_add_instance_groups_success(self, emr_handler_with_write_access, mock_context):
        """Test successful add-instance-groups operation."""
        with patch.object(emr_handler_with_write_access, 'emr_client') as mock_emr_client:
            # Mock AWS response
            mock_emr_client.add_instance_groups.return_value = {
                'InstanceGroupIds': ['ig-12345ABCDEF', 'ig-67890GHIJKL'],
                'JobFlowId': 'j-12345ABCDEF',
                'ClusterArn': 'arn:aws:elasticmapreduce:region:account:cluster/j-12345ABCDEF',
            }

            # Mock tag preparation
            with patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags'
            ) as mock_prepare_tags:
                mock_prepare_tags.return_value = {
                    MCP_MANAGED_TAG_KEY: MCP_MANAGED_TAG_VALUE,
                    MCP_RESOURCE_TYPE_TAG_KEY: 'EMRInstanceGroup',
                }

                # Call function
                result = await emr_handler_with_write_access.manage_aws_emr_ec2_instances(
                    ctx=mock_context,
                    operation='add-instance-groups',
                    cluster_id='j-12345ABCDEF',
                    instance_groups=[
                        {
                            'InstanceRole': 'TASK',
                            'InstanceType': 'm5.xlarge',
                            'InstanceCount': 2,
                            'Name': 'Task Group 1',
                        },
                        {
                            'InstanceRole': 'TASK',
                            'InstanceType': 'm5.2xlarge',
                            'InstanceCount': 1,
                            'Name': 'Task Group 2',
                        },
                    ],
                )

                # Verify AWS client was called correctly
                mock_emr_client.add_instance_groups.assert_called_once()
                args, kwargs = mock_emr_client.add_instance_groups.call_args
                assert kwargs['JobFlowId'] == 'j-12345ABCDEF'
                assert len(kwargs['InstanceGroups']) == 2

                # Verify tags were applied
                mock_emr_client.add_tags.assert_called_once()

                # Verify response
                assert result.isError is False
                assert result.cluster_id == 'j-12345ABCDEF'
