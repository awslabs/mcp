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

"""Tests for EMR models."""

import pytest
from awslabs.dataprocessing_mcp_server.models.emr_models import (
    AddInstanceFleetResponse,
    AddInstanceFleetResponseModel,
    AddInstanceGroupsResponse,
    AddInstanceGroupsResponseModel,
    AddStepsResponse,
    AddStepsResponseModel,
    CancelStepsResponse,
    CancelStepsResponseModel,
    DescribeStepResponse,
    DescribeStepResponseModel,
    ListInstanceFleetsResponse,
    ListInstanceFleetsResponseModel,
    ListInstancesResponse,
    ListInstancesResponseModel,
    ListStepsResponse,
    ListStepsResponseModel,
    ListSupportedInstanceTypesResponse,
    ListSupportedInstanceTypesResponseModel,
    ModifyInstanceFleetResponse,
    ModifyInstanceFleetResponseModel,
    ModifyInstanceGroupsResponse,
    ModifyInstanceGroupsResponseModel,
)


@pytest.mark.asyncio
async def test_add_instance_fleet_response_model():
    """Test AddInstanceFleetResponseModel."""
    model = AddInstanceFleetResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        instance_fleet_id='if-1234567890ABCDEF0',
        cluster_arn='arn:aws:elasticmapreduce:us-west-2:123456789012:cluster/j-1234567890ABCDEF0',
        operation='add_fleet',
    )
    assert model.cluster_id == 'j-1234567890ABCDEF0'
    assert model.instance_fleet_id == 'if-1234567890ABCDEF0'
    assert (
        model.cluster_arn
        == 'arn:aws:elasticmapreduce:us-west-2:123456789012:cluster/j-1234567890ABCDEF0'
    )
    assert model.operation == 'add_fleet'


@pytest.mark.asyncio
async def test_add_instance_fleet_response():
    """Test AddInstanceFleetResponse."""
    model = AddInstanceFleetResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        instance_fleet_id='if-1234567890ABCDEF0',
        cluster_arn='arn:aws:elasticmapreduce:us-west-2:123456789012:cluster/j-1234567890ABCDEF0',
        operation='add_fleet',
    )
    response = AddInstanceFleetResponse.create(
        is_error=False,
        content=[{'type': 'text', 'text': 'Successfully added instance fleet'}],
        model=model,
    )
    assert isinstance(response, AddInstanceFleetResponse)
    assert not response.isError
    assert response.cluster_id == 'j-1234567890ABCDEF0'
    assert response.instance_fleet_id == 'if-1234567890ABCDEF0'
    assert (
        response.cluster_arn
        == 'arn:aws:elasticmapreduce:us-west-2:123456789012:cluster/j-1234567890ABCDEF0'
    )
    assert response.operation == 'add_fleet'


@pytest.mark.asyncio
async def test_add_instance_groups_response_model():
    """Test AddInstanceGroupsResponseModel."""
    model = AddInstanceGroupsResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        job_flow_id='j-1234567890ABCDEF0',
        instance_group_ids=['ig-1234567890ABCDEF0', 'ig-0987654321ABCDEF0'],
        cluster_arn='arn:aws:elasticmapreduce:us-west-2:123456789012:cluster/j-1234567890ABCDEF0',
        operation='add_groups',
    )
    assert model.cluster_id == 'j-1234567890ABCDEF0'
    assert model.job_flow_id == 'j-1234567890ABCDEF0'
    assert model.instance_group_ids == ['ig-1234567890ABCDEF0', 'ig-0987654321ABCDEF0']
    assert (
        model.cluster_arn
        == 'arn:aws:elasticmapreduce:us-west-2:123456789012:cluster/j-1234567890ABCDEF0'
    )
    assert model.operation == 'add_groups'


@pytest.mark.asyncio
async def test_add_instance_groups_response():
    """Test AddInstanceGroupsResponse."""
    model = AddInstanceGroupsResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        job_flow_id='j-1234567890ABCDEF0',
        instance_group_ids=['ig-1234567890ABCDEF0', 'ig-0987654321ABCDEF0'],
        cluster_arn='arn:aws:elasticmapreduce:us-west-2:123456789012:cluster/j-1234567890ABCDEF0',
        operation='add_groups',
    )
    response = AddInstanceGroupsResponse.create(
        is_error=False,
        content=[{'type': 'text', 'text': 'Successfully added instance groups'}],
        model=model,
    )
    assert isinstance(response, AddInstanceGroupsResponse)
    assert not response.isError
    assert response.cluster_id == 'j-1234567890ABCDEF0'
    assert response.job_flow_id == 'j-1234567890ABCDEF0'
    assert response.instance_group_ids == ['ig-1234567890ABCDEF0', 'ig-0987654321ABCDEF0']
    assert (
        response.cluster_arn
        == 'arn:aws:elasticmapreduce:us-west-2:123456789012:cluster/j-1234567890ABCDEF0'
    )
    assert response.operation == 'add_groups'


@pytest.mark.asyncio
async def test_modify_instance_fleet_response_model():
    """Test ModifyInstanceFleetResponseModel."""
    model = ModifyInstanceFleetResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        instance_fleet_id='if-1234567890ABCDEF0',
        operation='modify_fleet',
    )
    assert model.cluster_id == 'j-1234567890ABCDEF0'
    assert model.instance_fleet_id == 'if-1234567890ABCDEF0'
    assert model.operation == 'modify_fleet'


@pytest.mark.asyncio
async def test_modify_instance_fleet_response():
    """Test ModifyInstanceFleetResponse."""
    model = ModifyInstanceFleetResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        instance_fleet_id='if-1234567890ABCDEF0',
        operation='modify_fleet',
    )
    response = ModifyInstanceFleetResponse.create(
        is_error=False,
        content=[{'type': 'text', 'text': 'Successfully modified instance fleet'}],
        model=model,
    )
    assert isinstance(response, ModifyInstanceFleetResponse)
    assert not response.isError
    assert response.cluster_id == 'j-1234567890ABCDEF0'
    assert response.instance_fleet_id == 'if-1234567890ABCDEF0'
    assert response.operation == 'modify_fleet'


@pytest.mark.asyncio
async def test_modify_instance_groups_response_model():
    """Test ModifyInstanceGroupsResponseModel."""
    model = ModifyInstanceGroupsResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        instance_group_ids=['ig-1234567890ABCDEF0', 'ig-0987654321ABCDEF0'],
        operation='modify_groups',
    )
    assert model.cluster_id == 'j-1234567890ABCDEF0'
    assert model.instance_group_ids == ['ig-1234567890ABCDEF0', 'ig-0987654321ABCDEF0']
    assert model.operation == 'modify_groups'


@pytest.mark.asyncio
async def test_modify_instance_groups_response():
    """Test ModifyInstanceGroupsResponse."""
    model = ModifyInstanceGroupsResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        instance_group_ids=['ig-1234567890ABCDEF0', 'ig-0987654321ABCDEF0'],
        operation='modify_groups',
    )
    response = ModifyInstanceGroupsResponse.create(
        is_error=False,
        content=[{'type': 'text', 'text': 'Successfully modified instance groups'}],
        model=model,
    )
    assert isinstance(response, ModifyInstanceGroupsResponse)
    assert not response.isError
    assert response.cluster_id == 'j-1234567890ABCDEF0'
    assert response.instance_group_ids == ['ig-1234567890ABCDEF0', 'ig-0987654321ABCDEF0']
    assert response.operation == 'modify_groups'


@pytest.mark.asyncio
async def test_list_instance_fleets_response_model():
    """Test ListInstanceFleetsResponseModel."""
    model = ListInstanceFleetsResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        instance_fleets=[
            {'Id': 'if-1234567890ABCDEF0', 'Name': 'InstanceFleet1'},
            {'Id': 'if-0987654321ABCDEF0', 'Name': 'InstanceFleet2'},
        ],
        count=2,
        marker='pagination-token',
        operation='list',
    )
    assert model.cluster_id == 'j-1234567890ABCDEF0'
    assert model.instance_fleets == [
        {'Id': 'if-1234567890ABCDEF0', 'Name': 'InstanceFleet1'},
        {'Id': 'if-0987654321ABCDEF0', 'Name': 'InstanceFleet2'},
    ]
    assert model.count == 2
    assert model.marker == 'pagination-token'
    assert model.operation == 'list'


@pytest.mark.asyncio
async def test_list_instance_fleets_response():
    """Test ListInstanceFleetsResponse."""
    model = ListInstanceFleetsResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        instance_fleets=[
            {'Id': 'if-1234567890ABCDEF0', 'Name': 'InstanceFleet1'},
            {'Id': 'if-0987654321ABCDEF0', 'Name': 'InstanceFleet2'},
        ],
        count=2,
        marker='pagination-token',
        operation='list',
    )
    response = ListInstanceFleetsResponse.create(
        is_error=False,
        content=[{'type': 'text', 'text': 'Successfully listed instance fleets'}],
        model=model,
    )
    assert isinstance(response, ListInstanceFleetsResponse)
    assert not response.isError
    assert response.cluster_id == 'j-1234567890ABCDEF0'
    assert response.instance_fleets == [
        {'Id': 'if-1234567890ABCDEF0', 'Name': 'InstanceFleet1'},
        {'Id': 'if-0987654321ABCDEF0', 'Name': 'InstanceFleet2'},
    ]
    assert response.count == 2
    assert response.marker == 'pagination-token'
    assert response.operation == 'list'


@pytest.mark.asyncio
async def test_list_instances_response_model():
    """Test ListInstancesResponseModel."""
    model = ListInstancesResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        instances=[
            {'Id': 'i-1234567890ABCDEF0', 'InstanceGroupName': 'InstanceGroup1'},
            {'Id': 'i-0987654321ABCDEF0', 'InstanceGroupName': 'InstanceGroup2'},
        ],
        count=2,
        marker='pagination-token',
        operation='list',
    )
    assert model.cluster_id == 'j-1234567890ABCDEF0'
    assert model.instances == [
        {'Id': 'i-1234567890ABCDEF0', 'InstanceGroupName': 'InstanceGroup1'},
        {'Id': 'i-0987654321ABCDEF0', 'InstanceGroupName': 'InstanceGroup2'},
    ]
    assert model.count == 2
    assert model.marker == 'pagination-token'
    assert model.operation == 'list'


@pytest.mark.asyncio
async def test_list_instances_response():
    """Test ListInstancesResponse."""
    model = ListInstancesResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        instances=[
            {'Id': 'i-1234567890ABCDEF0', 'InstanceGroupName': 'InstanceGroup1'},
            {'Id': 'i-0987654321ABCDEF0', 'InstanceGroupName': 'InstanceGroup2'},
        ],
        count=2,
        marker='pagination-token',
        operation='list',
    )
    response = ListInstancesResponse.create(
        is_error=False,
        content=[{'type': 'text', 'text': 'Successfully listed instances'}],
        model=model,
    )
    assert isinstance(response, ListInstancesResponse)
    assert not response.isError
    assert response.cluster_id == 'j-1234567890ABCDEF0'
    assert response.instances == [
        {'Id': 'i-1234567890ABCDEF0', 'InstanceGroupName': 'InstanceGroup1'},
        {'Id': 'i-0987654321ABCDEF0', 'InstanceGroupName': 'InstanceGroup2'},
    ]
    assert response.count == 2
    assert response.marker == 'pagination-token'
    assert response.operation == 'list'


@pytest.mark.asyncio
async def test_list_supported_instance_types_response_model():
    """Test ListSupportedInstanceTypesResponseModel."""
    model = ListSupportedInstanceTypesResponseModel(
        instance_types=[
            {'InstanceType': 'm5.xlarge', 'ReleaseLabel': 'emr-7.9.0'},
            {'InstanceType': 'm5.2xlarge', 'ReleaseLabel': 'emr-7.9.0'},
        ],
        count=2,
        marker='pagination-token',
        release_label='emr-7.9.0',
        operation='list',
    )
    assert model.instance_types == [
        {'InstanceType': 'm5.xlarge', 'ReleaseLabel': 'emr-7.9.0'},
        {'InstanceType': 'm5.2xlarge', 'ReleaseLabel': 'emr-7.9.0'},
    ]
    assert model.count == 2
    assert model.marker == 'pagination-token'
    assert model.release_label == 'emr-7.9.0'
    assert model.operation == 'list'


@pytest.mark.asyncio
async def test_list_supported_instance_types_response():
    """Test ListSupportedInstanceTypesResponse."""
    model = ListSupportedInstanceTypesResponseModel(
        instance_types=[
            {'InstanceType': 'm5.xlarge', 'ReleaseLabel': 'emr-7.9.0'},
            {'InstanceType': 'm5.2xlarge', 'ReleaseLabel': 'emr-7.9.0'},
        ],
        count=2,
        marker='pagination-token',
        release_label='emr-7.9.0',
        operation='list',
    )
    response = ListSupportedInstanceTypesResponse.create(
        is_error=False,
        content=[{'type': 'text', 'text': 'Successfully listed supported instance types'}],
        model=model,
    )
    assert isinstance(response, ListSupportedInstanceTypesResponse)
    assert not response.isError
    assert response.instance_types == [
        {'InstanceType': 'm5.xlarge', 'ReleaseLabel': 'emr-7.9.0'},
        {'InstanceType': 'm5.2xlarge', 'ReleaseLabel': 'emr-7.9.0'},
    ]
    assert response.count == 2
    assert response.marker == 'pagination-token'
    assert response.release_label == 'emr-7.9.0'
    assert response.operation == 'list'


@pytest.mark.asyncio
async def test_add_steps_response_model():
    """Test AddStepsResponseModel."""
    model = AddStepsResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        step_ids=['s-1234567890ABCDEF0', 's-0987654321ABCDEF0'],
        count=2,
        operation='add',
    )
    assert model.cluster_id == 'j-1234567890ABCDEF0'
    assert model.step_ids == ['s-1234567890ABCDEF0', 's-0987654321ABCDEF0']
    assert model.count == 2
    assert model.operation == 'add'


@pytest.mark.asyncio
async def test_add_steps_response():
    """Test AddStepsResponse."""
    model = AddStepsResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        step_ids=['s-1234567890ABCDEF0', 's-0987654321ABCDEF0'],
        count=2,
        operation='add',
    )
    response = AddStepsResponse.create(
        is_error=False, content=[{'type': 'text', 'text': 'Successfully added steps'}], model=model
    )
    assert isinstance(response, AddStepsResponse)
    assert not response.isError
    assert response.cluster_id == 'j-1234567890ABCDEF0'
    assert response.step_ids == ['s-1234567890ABCDEF0', 's-0987654321ABCDEF0']
    assert response.count == 2
    assert response.operation == 'add'


@pytest.mark.asyncio
async def test_cancel_steps_response_model():
    """Test CancelStepsResponseModel."""
    model = CancelStepsResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        step_cancellation_info=[
            {
                'StepId': 's-1234567890ABCDEF0',
                'Status': 'SUBMITTED',
                'Reason': 'Test cancellation',
            },
            {'StepId': 's-0987654321ABCDEF0', 'Status': 'FAILED', 'Reason': 'Test cancellation'},
        ],
        count=2,
        operation='cancel',
    )
    assert model.cluster_id == 'j-1234567890ABCDEF0'
    assert model.step_cancellation_info == [
        {'StepId': 's-1234567890ABCDEF0', 'Status': 'SUBMITTED', 'Reason': 'Test cancellation'},
        {'StepId': 's-0987654321ABCDEF0', 'Status': 'FAILED', 'Reason': 'Test cancellation'},
    ]
    assert model.count == 2
    assert model.operation == 'cancel'


@pytest.mark.asyncio
async def test_cancel_steps_response():
    """Test CancelStepsResponse."""
    model = CancelStepsResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        step_cancellation_info=[
            {
                'StepId': 's-1234567890ABCDEF0',
                'Status': 'SUBMITTED',
                'Reason': 'Test cancellation',
            },
            {'StepId': 's-0987654321ABCDEF0', 'Status': 'FAILED', 'Reason': 'Test cancellation'},
        ],
        count=2,
        operation='cancel',
    )
    response = CancelStepsResponse.create(
        is_error=False,
        content=[{'type': 'text', 'text': 'Successfully cancelled steps'}],
        model=model,
    )

    assert isinstance(response, CancelStepsResponse)
    assert not response.isError
    assert response.cluster_id == 'j-1234567890ABCDEF0'
    assert response.step_cancellation_info == [
        {'StepId': 's-1234567890ABCDEF0', 'Status': 'SUBMITTED', 'Reason': 'Test cancellation'},
        {'StepId': 's-0987654321ABCDEF0', 'Status': 'FAILED', 'Reason': 'Test cancellation'},
    ]
    assert response.count == 2
    assert response.operation == 'cancel'


@pytest.mark.asyncio
async def test_describe_step_response_model():
    """Test DescribeStepResponseModel."""
    model = DescribeStepResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        step={
            'Id': 's-1234567890ABCDEF0',
            'Name': 'Test Step',
            'Status': {'State': 'COMPLETED'},
            'Config': {'Jar': 'command-runner.jar'},
        },
        operation='describe',
    )
    assert model.cluster_id == 'j-1234567890ABCDEF0'
    assert model.step['Id'] == 's-1234567890ABCDEF0'
    assert model.step['Name'] == 'Test Step'
    assert model.operation == 'describe'


@pytest.mark.asyncio
async def test_describe_step_response():
    """Test DescribeStepResponse."""
    model = DescribeStepResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        step={
            'Id': 's-1234567890ABCDEF0',
            'Name': 'Test Step',
            'Status': {'State': 'COMPLETED'},
            'Config': {'Jar': 'command-runner.jar'},
        },
        operation='describe',
    )
    response = DescribeStepResponse.create(
        is_error=False,
        content=[{'type': 'text', 'text': 'Successfully described step'}],
        model=model,
    )
    assert isinstance(response, DescribeStepResponse)
    assert not response.isError
    assert response.cluster_id == 'j-1234567890ABCDEF0'
    assert response.step['Id'] == 's-1234567890ABCDEF0'
    assert response.operation == 'describe'


@pytest.mark.asyncio
async def test_list_steps_response_model():
    """Test ListStepsResponseModel."""
    model = ListStepsResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        steps=[
            {'Id': 's-1234567890ABCDEF0', 'Name': 'Step1', 'Status': {'State': 'COMPLETED'}},
            {'Id': 's-0987654321ABCDEF0', 'Name': 'Step2', 'Status': {'State': 'RUNNING'}},
        ],
        count=2,
        marker='pagination-token',
        operation='list',
    )
    assert model.cluster_id == 'j-1234567890ABCDEF0'
    assert model.steps == [
        {'Id': 's-1234567890ABCDEF0', 'Name': 'Step1', 'Status': {'State': 'COMPLETED'}},
        {'Id': 's-0987654321ABCDEF0', 'Name': 'Step2', 'Status': {'State': 'RUNNING'}},
    ]
    assert model.count == 2
    assert model.marker == 'pagination-token'
    assert model.operation == 'list'


@pytest.mark.asyncio
async def test_list_steps_response():
    """Test ListStepsResponse."""
    model = ListStepsResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        steps=[
            {'Id': 's-1234567890ABCDEF0', 'Name': 'Step1', 'Status': {'State': 'COMPLETED'}},
            {'Id': 's-0987654321ABCDEF0', 'Name': 'Step2', 'Status': {'State': 'RUNNING'}},
        ],
        count=2,
        marker='pagination-token',
        operation='list',
    )
    response = ListStepsResponse.create(
        is_error=False,
        content=[{'type': 'text', 'text': 'Successfully listed steps'}],
        model=model,
    )
    assert isinstance(response, ListStepsResponse)
    assert not response.isError
    assert response.cluster_id == 'j-1234567890ABCDEF0'
    assert response.steps == [
        {'Id': 's-1234567890ABCDEF0', 'Name': 'Step1', 'Status': {'State': 'COMPLETED'}},
        {'Id': 's-0987654321ABCDEF0', 'Name': 'Step2', 'Status': {'State': 'RUNNING'}},
    ]
    assert response.count == 2
    assert response.marker == 'pagination-token'
    assert response.operation == 'list'


# Test error responses
@pytest.mark.asyncio
async def test_error_response_models():
    """Test all response models with error states."""
    # Test AddInstanceFleetResponse with error
    model = AddInstanceFleetResponseModel(
        cluster_id='j-1234567890ABCDEF0',
        instance_fleet_id='',
        cluster_arn='',
        operation='add_fleet',
    )
    response = AddInstanceFleetResponse.create(
        is_error=True,
        content=[{'type': 'text', 'text': 'Error adding instance fleet'}],
        model=model,
    )
    assert response.isError is True
    assert response.instance_fleet_id == ''

    # Test AddStepsResponse with error
    steps_model = AddStepsResponseModel(
        cluster_id='j-1234567890ABCDEF0', step_ids=[], count=0, operation='add'
    )
    steps_response = AddStepsResponse.create(
        is_error=True, content=[{'type': 'text', 'text': 'Error adding steps'}], model=steps_model
    )
    assert steps_response.isError is True
    assert steps_response.count == 0


# Test edge cases
@pytest.mark.asyncio
async def test_model_edge_cases():
    """Test models with edge case values."""
    # Test with None values where allowed
    model = ListInstanceFleetsResponseModel(
        cluster_id='j-1234567890ABCDEF0', instance_fleets=[], count=0, marker=None
    )
    assert model.marker is None
    assert model.count == 0
    assert model.instance_fleets == []

    # Test with empty step cancellation info
    cancel_model = CancelStepsResponseModel(
        cluster_id='j-1234567890ABCDEF0', step_cancellation_info=[], count=0, operation='cancel'
    )
    assert cancel_model.step_cancellation_info == []
    assert cancel_model.count == 0


# Test default values
@pytest.mark.asyncio
async def test_model_defaults():
    """Test model default values."""
    """Test model default values."""
    # Test AddInstanceFleetResponseModel defaults
    model = AddInstanceFleetResponseModel(
        cluster_id='j-1234567890ABCDEF0', instance_fleet_id='if-1234567890ABCDEF0'
    )
    assert model.operation == 'add_fleet'
    assert model.cluster_arn is None

    # Test AddStepsResponseModel defaults
    steps_model = AddStepsResponseModel(
        cluster_id='j-1234567890ABCDEF0', step_ids=['s-1234567890ABCDEF0'], count=1
    )
    assert steps_model.operation == 'add'

    # Test DescribeStepResponseModel defaults
    describe_model = DescribeStepResponseModel(
        cluster_id='j-1234567890ABCDEF0', step={'Id': 's-1234567890ABCDEF0'}
    )
    assert describe_model.operation == 'describe'
