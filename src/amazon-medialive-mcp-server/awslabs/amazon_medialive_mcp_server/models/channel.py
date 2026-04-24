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

"""Channel-related Pydantic models — channel CRUD, pipelines, maintenance, batch operations."""

from __future__ import annotations

from awslabs.amazon_medialive_mcp_server.enums import (
    ChannelClass,
    ChannelPipelineIdToRestart,
    ChannelPlacementGroupState,
    ChannelState,
    InputDeviceTransferType,
    LogLevel,
    MaintenanceDay,
    PipelineId,
    RebootInputDeviceForce,
)
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import TYPE_CHECKING, Annotated, Optional


if TYPE_CHECKING:
    from awslabs.amazon_medialive_mcp_server.models.common import (
        BatchFailedResultModel,
        BatchScheduleActionCreateRequest,
        BatchScheduleActionCreateResult,
        BatchScheduleActionDeleteRequest,
        BatchScheduleActionDeleteResult,
        BatchSuccessfulResultModel,
        CdiInputSpecification,
        DescribeAnywhereSettings,
        ValidationError,
    )
    from awslabs.amazon_medialive_mcp_server.models.input import (
        InputAttachment,
        InputSpecification,
    )
    from awslabs.amazon_medialive_mcp_server.models.monitoring import EncoderSettings
    from awslabs.amazon_medialive_mcp_server.models.output import (
        OutputDestination,
    )


class AcceptInputDeviceTransferRequest(BaseModel):
    """Placeholder documentation for AcceptInputDeviceTransferRequest."""

    model_config = ConfigDict(populate_by_name=True)

    input_device_id: Annotated[
        str,
        Field(
            ...,
            alias='InputDeviceId',
            description='The unique ID of the input device to accept. For example, hd-123456789abcdef.',
        ),
    ]


class AcceptInputDeviceTransferResponse(BaseModel):
    """Placeholder documentation for AcceptInputDeviceTransferResponse."""

    model_config = ConfigDict(populate_by_name=True)


class AnywhereSettings(BaseModel):
    """Elemental anywhere settings."""

    model_config = ConfigDict(populate_by_name=True)

    channel_placement_group_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChannelPlacementGroupId',
            description='The ID of the channel placement group for the channel.',
        ),
    ]

    cluster_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClusterId',
            description='The ID of the cluster for the channel.',
        ),
    ]


class BatchDelete(BaseModel):
    """Batch delete resource request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelIds',
            description='List of channel IDs',
        ),
    ]

    input_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='InputIds',
            description='List of input IDs',
        ),
    ]

    input_security_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='InputSecurityGroupIds',
            description='List of input security group IDs',
        ),
    ]

    multiplex_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='MultiplexIds',
            description='List of multiplex IDs',
        ),
    ]


class BatchDeleteRequest(BaseModel):
    """A request to delete resources."""

    model_config = ConfigDict(populate_by_name=True)

    channel_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelIds',
            description='List of channel IDs',
        ),
    ]

    input_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='InputIds',
            description='List of input IDs',
        ),
    ]

    input_security_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='InputSecurityGroupIds',
            description='List of input security group IDs',
        ),
    ]

    multiplex_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='MultiplexIds',
            description='List of multiplex IDs',
        ),
    ]


class BatchStart(BaseModel):
    """Batch start resource request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelIds',
            description='List of channel IDs',
        ),
    ]

    multiplex_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='MultiplexIds',
            description='List of multiplex IDs',
        ),
    ]


class BatchStartRequest(BaseModel):
    """A request to start resources."""

    model_config = ConfigDict(populate_by_name=True)

    channel_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelIds',
            description='List of channel IDs',
        ),
    ]

    multiplex_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='MultiplexIds',
            description='List of multiplex IDs',
        ),
    ]


class BatchStop(BaseModel):
    """Batch stop resource request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelIds',
            description='List of channel IDs',
        ),
    ]

    multiplex_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='MultiplexIds',
            description='List of multiplex IDs',
        ),
    ]


class BatchStopRequest(BaseModel):
    """A request to stop resources."""

    model_config = ConfigDict(populate_by_name=True)

    channel_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelIds',
            description='List of channel IDs',
        ),
    ]

    multiplex_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='MultiplexIds',
            description='List of multiplex IDs',
        ),
    ]


class BatchDeleteResponse(BaseModel):
    """Placeholder documentation for BatchDeleteResponse."""

    model_config = ConfigDict(populate_by_name=True)

    failed: Annotated[
        Optional[list[BatchFailedResultModel]],
        Field(
            None,
            alias='Failed',
            description='List of failed operations',
        ),
    ]

    successful: Annotated[
        Optional[list[BatchSuccessfulResultModel]],
        Field(
            None,
            alias='Successful',
            description='List of successful operations',
        ),
    ]


class BatchDeleteResultModel(BaseModel):
    """Batch delete resource results."""

    model_config = ConfigDict(populate_by_name=True)

    failed: Annotated[
        Optional[list[BatchFailedResultModel]],
        Field(
            None,
            alias='Failed',
            description='List of failed operations',
        ),
    ]

    successful: Annotated[
        Optional[list[BatchSuccessfulResultModel]],
        Field(
            None,
            alias='Successful',
            description='List of successful operations',
        ),
    ]


class BatchStartResponse(BaseModel):
    """Placeholder documentation for BatchStartResponse."""

    model_config = ConfigDict(populate_by_name=True)

    failed: Annotated[
        Optional[list[BatchFailedResultModel]],
        Field(
            None,
            alias='Failed',
            description='List of failed operations',
        ),
    ]

    successful: Annotated[
        Optional[list[BatchSuccessfulResultModel]],
        Field(
            None,
            alias='Successful',
            description='List of successful operations',
        ),
    ]


class BatchStartResultModel(BaseModel):
    """Batch start resource results."""

    model_config = ConfigDict(populate_by_name=True)

    failed: Annotated[
        Optional[list[BatchFailedResultModel]],
        Field(
            None,
            alias='Failed',
            description='List of failed operations',
        ),
    ]

    successful: Annotated[
        Optional[list[BatchSuccessfulResultModel]],
        Field(
            None,
            alias='Successful',
            description='List of successful operations',
        ),
    ]


class BatchStopResponse(BaseModel):
    """Placeholder documentation for BatchStopResponse."""

    model_config = ConfigDict(populate_by_name=True)

    failed: Annotated[
        Optional[list[BatchFailedResultModel]],
        Field(
            None,
            alias='Failed',
            description='List of failed operations',
        ),
    ]

    successful: Annotated[
        Optional[list[BatchSuccessfulResultModel]],
        Field(
            None,
            alias='Successful',
            description='List of successful operations',
        ),
    ]


class BatchStopResultModel(BaseModel):
    """Batch stop resource results."""

    model_config = ConfigDict(populate_by_name=True)

    failed: Annotated[
        Optional[list[BatchFailedResultModel]],
        Field(
            None,
            alias='Failed',
            description='List of failed operations',
        ),
    ]

    successful: Annotated[
        Optional[list[BatchSuccessfulResultModel]],
        Field(
            None,
            alias='Successful',
            description='List of successful operations',
        ),
    ]


class CancelInputDeviceTransferRequest(BaseModel):
    """Placeholder documentation for CancelInputDeviceTransferRequest."""

    model_config = ConfigDict(populate_by_name=True)

    input_device_id: Annotated[
        str,
        Field(
            ...,
            alias='InputDeviceId',
            description='The unique ID of the input device to cancel. For example, hd-123456789abcdef.',
        ),
    ]


class CancelInputDeviceTransferResponse(BaseModel):
    """Placeholder documentation for CancelInputDeviceTransferResponse."""

    model_config = ConfigDict(populate_by_name=True)


class ChannelEgressEndpoint(BaseModel):
    """Placeholder documentation for ChannelEgressEndpoint."""

    model_config = ConfigDict(populate_by_name=True)

    source_ip: Annotated[
        Optional[str],
        Field(
            None,
            alias='SourceIp',
            description='Public IP of where a channel\u0027s output comes from',
        ),
    ]


class ChannelEngineVersionRequest(BaseModel):
    """Placeholder documentation for ChannelEngineVersionRequest."""

    model_config = ConfigDict(populate_by_name=True)

    version: Annotated[
        Optional[str],
        Field(
            None,
            alias='Version',
            description='The build identifier of the engine version to use for this channel. Specify \u0027DEFAULT\u0027 to reset to the default version.',
        ),
    ]


class ChannelEngineVersionResponse(BaseModel):
    """Placeholder documentation for ChannelEngineVersionResponse."""

    model_config = ConfigDict(populate_by_name=True)

    expiration_date: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='ExpirationDate',
            description='The UTC time when the version expires.',
        ),
    ]

    version: Annotated[
        Optional[str],
        Field(
            None,
            alias='Version',
            description='The build identifier for this version of the channel version.',
        ),
    ]


class ClaimDeviceRequest(BaseModel):
    """A request to claim an AWS Elemental device that you have purchased from a third-party vendor."""

    model_config = ConfigDict(populate_by_name=True)

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The id of the device you want to claim.',
        ),
    ]


class ClaimDeviceResponse(BaseModel):
    """Placeholder documentation for ClaimDeviceResponse."""

    model_config = ConfigDict(populate_by_name=True)


class CreateChannelPlacementGroupRequest(BaseModel):
    """A request to create a channel placement group."""

    model_config = ConfigDict(populate_by_name=True)

    cluster_id: Annotated[
        str,
        Field(
            ...,
            alias='ClusterId',
            description='The ID of the cluster.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Specify a name that is unique in the Cluster. You can\u0027t change the name. Names are case-sensitive.',
        ),
    ]

    nodes: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='Nodes',
            description='An array of one ID for the Node that you want to associate with the ChannelPlacementGroup. (You can\u0027t associate more than one Node with the ChannelPlacementGroup.) The Node and the ChannelPlacementGroup must be in the same Cluster.',
        ),
    ]

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='An ID that you assign to a create request. This ID ensures idempotency when creating resources. the request.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]


class CreateChannelPlacementGroupResponse(BaseModel):
    """Placeholder documentation for CreateChannelPlacementGroupResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this ChannelPlacementGroup. It is automatically assigned when the ChannelPlacementGroup is created.',
        ),
    ]

    channels: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='Channels',
            description='Used in ListChannelPlacementGroupsResult',
        ),
    ]

    cluster_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClusterId',
            description='The ID of the Cluster that the Node belongs to.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the ChannelPlacementGroup. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the ChannelPlacementGroup.',
        ),
    ]

    nodes: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='Nodes',
            description='An array with one item, which is the single Node that is associated with the ChannelPlacementGroup.',
        ),
    ]

    state: Annotated[
        Optional[ChannelPlacementGroupState],
        Field(
            None,
            alias='State',
            description='The current state of the ChannelPlacementGroup.',
        ),
    ]


class DeleteChannelPlacementGroupRequest(BaseModel):
    """Placeholder documentation for DeleteChannelPlacementGroupRequest."""

    model_config = ConfigDict(populate_by_name=True)

    channel_placement_group_id: Annotated[
        str,
        Field(
            ...,
            alias='ChannelPlacementGroupId',
            description='The ID of the channel placement group.',
        ),
    ]

    cluster_id: Annotated[
        str,
        Field(
            ...,
            alias='ClusterId',
            description='The ID of the cluster.',
        ),
    ]


class DeleteChannelPlacementGroupResponse(BaseModel):
    """Placeholder documentation for DeleteChannelPlacementGroupResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this ChannelPlacementGroup. It is automatically assigned when the ChannelPlacementGroup is created.',
        ),
    ]

    channels: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='Channels',
            description='Used in ListChannelPlacementGroupsResult',
        ),
    ]

    cluster_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClusterId',
            description='The ID of the Cluster that the Node belongs to.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the ChannelPlacementGroup. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the ChannelPlacementGroup.',
        ),
    ]

    nodes: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='Nodes',
            description='An array with one item, which is the single Node that is associated with the ChannelPlacementGroup.',
        ),
    ]

    state: Annotated[
        Optional[ChannelPlacementGroupState],
        Field(
            None,
            alias='State',
            description='The current state of the ChannelPlacementGroup.',
        ),
    ]


class DeleteChannelRequest(BaseModel):
    """Placeholder documentation for DeleteChannelRequest."""

    model_config = ConfigDict(populate_by_name=True)

    channel_id: Annotated[
        str,
        Field(
            ...,
            alias='ChannelId',
            description='Unique ID of the channel.',
        ),
    ]


class DescribeChannelPlacementGroupRequest(BaseModel):
    """Placeholder documentation for DescribeChannelPlacementGroupRequest."""

    model_config = ConfigDict(populate_by_name=True)

    channel_placement_group_id: Annotated[
        str,
        Field(
            ...,
            alias='ChannelPlacementGroupId',
            description='The ID of the channel placement group.',
        ),
    ]

    cluster_id: Annotated[
        str,
        Field(
            ...,
            alias='ClusterId',
            description='The ID of the cluster.',
        ),
    ]


class DescribeChannelPlacementGroupResponse(BaseModel):
    """Placeholder documentation for DescribeChannelPlacementGroupResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this ChannelPlacementGroup. It is automatically assigned when the ChannelPlacementGroup is created.',
        ),
    ]

    channels: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='Channels',
            description='Used in ListChannelPlacementGroupsResult',
        ),
    ]

    cluster_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClusterId',
            description='The ID of the Cluster that the Node belongs to.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the ChannelPlacementGroup. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the ChannelPlacementGroup.',
        ),
    ]

    nodes: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='Nodes',
            description='An array with one item, which is the single Node that is associated with the ChannelPlacementGroup.',
        ),
    ]

    state: Annotated[
        Optional[ChannelPlacementGroupState],
        Field(
            None,
            alias='State',
            description='The current state of the ChannelPlacementGroup.',
        ),
    ]


class DescribeChannelPlacementGroupResult(BaseModel):
    """Contains the response for CreateChannelPlacementGroup, DescribeChannelPlacementGroup, DeleteChannelPlacementGroup, UpdateChannelPlacementGroup."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this ChannelPlacementGroup. It is automatically assigned when the ChannelPlacementGroup is created.',
        ),
    ]

    channels: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='Channels',
            description='Used in ListChannelPlacementGroupsResult',
        ),
    ]

    cluster_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClusterId',
            description='The ID of the Cluster that the Node belongs to.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the ChannelPlacementGroup. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the ChannelPlacementGroup.',
        ),
    ]

    nodes: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='Nodes',
            description='An array with one item, which is the single Node that is associated with the ChannelPlacementGroup.',
        ),
    ]

    state: Annotated[
        Optional[ChannelPlacementGroupState],
        Field(
            None,
            alias='State',
            description='The current state of the ChannelPlacementGroup.',
        ),
    ]


class DescribeChannelPlacementGroupSummary(BaseModel):
    """Contains the response for ListChannelPlacementGroups."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this ChannelPlacementGroup. It is automatically assigned when the ChannelPlacementGroup is created.',
        ),
    ]

    channels: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='Channels',
            description='Used in ListChannelPlacementGroupsResult',
        ),
    ]

    cluster_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClusterId',
            description='The ID of the Cluster that the Node belongs to.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the ChannelPlacementGroup. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the ChannelPlacementGroup.',
        ),
    ]

    nodes: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='Nodes',
            description='An array with one item, which is the single Node that is associated with the ChannelPlacementGroup.',
        ),
    ]

    state: Annotated[
        Optional[ChannelPlacementGroupState],
        Field(
            None,
            alias='State',
            description='The current state of the ChannelPlacementGroup.',
        ),
    ]


class DescribeChannelRequest(BaseModel):
    """Placeholder documentation for DescribeChannelRequest."""

    model_config = ConfigDict(populate_by_name=True)

    channel_id: Annotated[
        str,
        Field(
            ...,
            alias='ChannelId',
            description='channel ID',
        ),
    ]


class ListChannelPlacementGroupsRequest(BaseModel):
    """Placeholder documentation for ListChannelPlacementGroupsRequest."""

    model_config = ConfigDict(populate_by_name=True)

    cluster_id: Annotated[
        str,
        Field(
            ...,
            alias='ClusterId',
            description='The ID of the cluster',
        ),
    ]

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='The maximum number of items to return.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='The token to retrieve the next page of results.',
        ),
    ]


class ListChannelPlacementGroupsResponse(BaseModel):
    """Placeholder documentation for ListChannelPlacementGroupsResponse."""

    model_config = ConfigDict(populate_by_name=True)

    channel_placement_groups: Annotated[
        Optional[list[DescribeChannelPlacementGroupSummary]],
        Field(
            None,
            alias='ChannelPlacementGroups',
            description='An array of ChannelPlacementGroups that exist in the Cluster.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='Token for the next result.',
        ),
    ]


class ListChannelPlacementGroupsResult(BaseModel):
    """Contains the response for ListChannelPlacementGroups."""

    model_config = ConfigDict(populate_by_name=True)

    channel_placement_groups: Annotated[
        Optional[list[DescribeChannelPlacementGroupSummary]],
        Field(
            None,
            alias='ChannelPlacementGroups',
            description='An array of ChannelPlacementGroups that exist in the Cluster.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='Token for the next result.',
        ),
    ]


class ListChannelsRequest(BaseModel):
    """Placeholder documentation for ListChannelsRequest."""

    model_config = ConfigDict(populate_by_name=True)

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='',
        ),
    ]


class MaintenanceCreateSettings(BaseModel):
    """Placeholder documentation for MaintenanceCreateSettings."""

    model_config = ConfigDict(populate_by_name=True)

    maintenance_day: Annotated[
        Optional[MaintenanceDay],
        Field(
            None,
            alias='MaintenanceDay',
            description='Choose one day of the week for maintenance. The chosen day is used for all future maintenance windows.',
        ),
    ]

    maintenance_start_time: Annotated[
        Optional[str],
        Field(
            None,
            alias='MaintenanceStartTime',
            description='Choose the hour that maintenance will start. The chosen time is used for all future maintenance windows.',
        ),
    ]


class MaintenanceStatus(BaseModel):
    """Placeholder documentation for MaintenanceStatus."""

    model_config = ConfigDict(populate_by_name=True)

    maintenance_day: Annotated[
        Optional[MaintenanceDay],
        Field(
            None,
            alias='MaintenanceDay',
            description='The currently selected maintenance day.',
        ),
    ]

    maintenance_deadline: Annotated[
        Optional[str],
        Field(
            None,
            alias='MaintenanceDeadline',
            description='Maintenance is required by the displayed date and time. Date and time is in ISO.',
        ),
    ]

    maintenance_scheduled_date: Annotated[
        Optional[str],
        Field(
            None,
            alias='MaintenanceScheduledDate',
            description='The currently scheduled maintenance date and time. Date and time is in ISO.',
        ),
    ]

    maintenance_start_time: Annotated[
        Optional[str],
        Field(
            None,
            alias='MaintenanceStartTime',
            description='The currently selected maintenance start time. Time is in UTC.',
        ),
    ]


class MaintenanceUpdateSettings(BaseModel):
    """Placeholder documentation for MaintenanceUpdateSettings."""

    model_config = ConfigDict(populate_by_name=True)

    maintenance_day: Annotated[
        Optional[MaintenanceDay],
        Field(
            None,
            alias='MaintenanceDay',
            description='Choose one day of the week for maintenance. The chosen day is used for all future maintenance windows.',
        ),
    ]

    maintenance_scheduled_date: Annotated[
        Optional[str],
        Field(
            None,
            alias='MaintenanceScheduledDate',
            description='Choose a specific date for maintenance to occur. The chosen date is used for the next maintenance window only.',
        ),
    ]

    maintenance_start_time: Annotated[
        Optional[str],
        Field(
            None,
            alias='MaintenanceStartTime',
            description='Choose the hour that maintenance will start. The chosen time is used for all future maintenance windows.',
        ),
    ]


class PipelineDetail(BaseModel):
    """Runtime details of a pipeline when a channel is running."""

    model_config = ConfigDict(populate_by_name=True)

    active_input_attachment_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='ActiveInputAttachmentName',
            description='The name of the active input attachment currently being ingested by this pipeline.',
        ),
    ]

    active_input_switch_action_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='ActiveInputSwitchActionName',
            description='The name of the input switch schedule action that occurred most recently and that resulted in the switch to the current input attachment for this pipeline.',
        ),
    ]

    active_motion_graphics_action_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='ActiveMotionGraphicsActionName',
            description='The name of the motion graphics activate action that occurred most recently and that resulted in the current graphics URI for this pipeline.',
        ),
    ]

    active_motion_graphics_uri: Annotated[
        Optional[str],
        Field(
            None,
            alias='ActiveMotionGraphicsUri',
            description='The current URI being used for HTML5 motion graphics for this pipeline.',
        ),
    ]

    pipeline_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='PipelineId',
            description='Pipeline ID',
        ),
    ]

    channel_engine_version: Annotated[
        Optional[ChannelEngineVersionResponse],
        Field(
            None,
            alias='ChannelEngineVersion',
            description='Current engine version of the encoder for this pipeline.',
        ),
    ]


class PipelineLockingSettings(BaseModel):
    """Pipeline Locking Settings."""

    model_config = ConfigDict(populate_by_name=True)


class PipelinePauseStateSettings(BaseModel):
    """Settings for pausing a pipeline."""

    model_config = ConfigDict(populate_by_name=True)

    pipeline_id: Annotated[
        PipelineId,
        Field(
            ...,
            alias='PipelineId',
            description='Pipeline ID to pause ("PIPELINE_0" or "PIPELINE_1").',
        ),
    ]


class RebootInputDevice(BaseModel):
    """Placeholder documentation for RebootInputDevice."""

    model_config = ConfigDict(populate_by_name=True)

    force: Annotated[
        Optional[RebootInputDeviceForce],
        Field(
            None,
            alias='Force',
            description='Force a reboot of an input device. If the device is streaming, it will stop streaming and begin rebooting within a few seconds of sending the command. If the device was streaming prior to the reboot, the device will resume streaming when the reboot completes.',
        ),
    ]


class RebootInputDeviceRequest(BaseModel):
    """A request to reboot an AWS Elemental device."""

    model_config = ConfigDict(populate_by_name=True)

    force: Annotated[
        Optional[RebootInputDeviceForce],
        Field(
            None,
            alias='Force',
            description='Force a reboot of an input device. If the device is streaming, it will stop streaming and begin rebooting within a few seconds of sending the command. If the device was streaming prior to the reboot, the device will resume streaming when the reboot completes.',
        ),
    ]

    input_device_id: Annotated[
        str,
        Field(
            ...,
            alias='InputDeviceId',
            description='The unique ID of the input device to reboot. For example, hd-123456789abcdef.',
        ),
    ]


class RebootInputDeviceResponse(BaseModel):
    """Placeholder documentation for RebootInputDeviceResponse."""

    model_config = ConfigDict(populate_by_name=True)


class RejectInputDeviceTransferRequest(BaseModel):
    """Placeholder documentation for RejectInputDeviceTransferRequest."""

    model_config = ConfigDict(populate_by_name=True)

    input_device_id: Annotated[
        str,
        Field(
            ...,
            alias='InputDeviceId',
            description='The unique ID of the input device to reject. For example, hd-123456789abcdef.',
        ),
    ]


class RejectInputDeviceTransferResponse(BaseModel):
    """Placeholder documentation for RejectInputDeviceTransferResponse."""

    model_config = ConfigDict(populate_by_name=True)


class RestartChannelPipelinesRequest(BaseModel):
    """Pipelines to restart."""

    model_config = ConfigDict(populate_by_name=True)

    channel_id: Annotated[
        str,
        Field(
            ...,
            alias='ChannelId',
            description='ID of channel',
        ),
    ]

    pipeline_ids: Annotated[
        Optional[list[ChannelPipelineIdToRestart]],
        Field(
            None,
            alias='PipelineIds',
            description='An array of pipelines to restart in this channel. Format PIPELINE_0 or PIPELINE_1.',
        ),
    ]


class StartChannelRequest(BaseModel):
    """Placeholder documentation for StartChannelRequest."""

    model_config = ConfigDict(populate_by_name=True)

    channel_id: Annotated[
        str,
        Field(
            ...,
            alias='ChannelId',
            description='A request to start a channel',
        ),
    ]


class StopChannelRequest(BaseModel):
    """Placeholder documentation for StopChannelRequest."""

    model_config = ConfigDict(populate_by_name=True)

    channel_id: Annotated[
        str,
        Field(
            ...,
            alias='ChannelId',
            description='A request to stop a running channel',
        ),
    ]


class BatchUpdateScheduleRequest(BaseModel):
    """List of actions to create and list of actions to delete."""

    model_config = ConfigDict(populate_by_name=True)

    channel_id: Annotated[
        str,
        Field(
            ...,
            alias='ChannelId',
            description='Id of the channel whose schedule is being updated.',
        ),
    ]

    creates: Annotated[
        Optional[BatchScheduleActionCreateRequest],
        Field(
            None,
            alias='Creates',
            description='Schedule actions to create in the schedule.',
        ),
    ]

    deletes: Annotated[
        Optional[BatchScheduleActionDeleteRequest],
        Field(
            None,
            alias='Deletes',
            description='Schedule actions to delete from the schedule.',
        ),
    ]


class BatchUpdateScheduleResponse(BaseModel):
    """Placeholder documentation for BatchUpdateScheduleResponse."""

    model_config = ConfigDict(populate_by_name=True)

    creates: Annotated[
        Optional[BatchScheduleActionCreateResult],
        Field(
            None,
            alias='Creates',
            description='Schedule actions created in the schedule.',
        ),
    ]

    deletes: Annotated[
        Optional[BatchScheduleActionDeleteResult],
        Field(
            None,
            alias='Deletes',
            description='Schedule actions deleted from the schedule.',
        ),
    ]


class BatchUpdateScheduleResult(BaseModel):
    """Results of a batch schedule update."""

    model_config = ConfigDict(populate_by_name=True)

    creates: Annotated[
        Optional[BatchScheduleActionCreateResult],
        Field(
            None,
            alias='Creates',
            description='Schedule actions created in the schedule.',
        ),
    ]

    deletes: Annotated[
        Optional[BatchScheduleActionDeleteResult],
        Field(
            None,
            alias='Deletes',
            description='Schedule actions deleted from the schedule.',
        ),
    ]


class TransferInputDevice(BaseModel):
    """The transfer details of the input device."""

    model_config = ConfigDict(populate_by_name=True)

    target_customer_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='TargetCustomerId',
            description='The AWS account ID (12 digits) for the recipient of the device transfer.',
        ),
    ]

    target_region: Annotated[
        Optional[str],
        Field(
            None,
            alias='TargetRegion',
            description='The target AWS region to transfer the device.',
        ),
    ]

    transfer_message: Annotated[
        Optional[str],
        Field(
            None,
            alias='TransferMessage',
            description='An optional message for the recipient. Maximum 280 characters.',
        ),
    ]


class TransferInputDeviceRequest(BaseModel):
    """A request to transfer an input device."""

    model_config = ConfigDict(populate_by_name=True)

    input_device_id: Annotated[
        str,
        Field(
            ...,
            alias='InputDeviceId',
            description='The unique ID of this input device. For example, hd-123456789abcdef.',
        ),
    ]

    target_customer_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='TargetCustomerId',
            description='The AWS account ID (12 digits) for the recipient of the device transfer.',
        ),
    ]

    target_region: Annotated[
        Optional[str],
        Field(
            None,
            alias='TargetRegion',
            description='The target AWS region to transfer the device.',
        ),
    ]

    transfer_message: Annotated[
        Optional[str],
        Field(
            None,
            alias='TransferMessage',
            description='An optional message for the recipient. Maximum 280 characters.',
        ),
    ]


class TransferInputDeviceResponse(BaseModel):
    """Placeholder documentation for TransferInputDeviceResponse."""

    model_config = ConfigDict(populate_by_name=True)


class TransferringInputDeviceSummary(BaseModel):
    """Details about the input device that is being transferred."""

    model_config = ConfigDict(populate_by_name=True)

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique ID of the input device.',
        ),
    ]

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='The optional message that the sender has attached to the transfer.',
        ),
    ]

    target_customer_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='TargetCustomerId',
            description='The AWS account ID for the recipient of the input device transfer.',
        ),
    ]

    transfer_type: Annotated[
        Optional[InputDeviceTransferType],
        Field(
            None,
            alias='TransferType',
            description='The type (direction) of the input device transfer.',
        ),
    ]


class UpdateChannelClass(BaseModel):
    """Placeholder documentation for UpdateChannelClass."""

    model_config = ConfigDict(populate_by_name=True)

    channel_class: Annotated[
        ChannelClass,
        Field(
            ...,
            alias='ChannelClass',
            description='The channel class that you wish to update this channel to use.',
        ),
    ]

    destinations: Annotated[
        Optional[list[OutputDestination]],
        Field(
            None,
            alias='Destinations',
            description='A list of output destinations for this channel.',
        ),
    ]


class UpdateChannelClassRequest(BaseModel):
    """Channel class that the channel should be updated to."""

    model_config = ConfigDict(populate_by_name=True)

    channel_class: Annotated[
        ChannelClass,
        Field(
            ...,
            alias='ChannelClass',
            description='The channel class that you wish to update this channel to use.',
        ),
    ]

    channel_id: Annotated[
        str,
        Field(
            ...,
            alias='ChannelId',
            description='Channel Id of the channel whose class should be updated.',
        ),
    ]

    destinations: Annotated[
        Optional[list[OutputDestination]],
        Field(
            None,
            alias='Destinations',
            description='A list of output destinations for this channel.',
        ),
    ]


class UpdateChannelPlacementGroupRequest(BaseModel):
    """A request to update the channel placement group."""

    model_config = ConfigDict(populate_by_name=True)

    channel_placement_group_id: Annotated[
        str,
        Field(
            ...,
            alias='ChannelPlacementGroupId',
            description='The ID of the channel placement group.',
        ),
    ]

    cluster_id: Annotated[
        str,
        Field(
            ...,
            alias='ClusterId',
            description='The ID of the cluster.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Include this parameter only if you want to change the current name of the ChannelPlacementGroup. Specify a name that is unique in the Cluster. You can\u0027t change the name. Names are case-sensitive.',
        ),
    ]

    nodes: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='Nodes',
            description='Include this parameter only if you want to change the list of Nodes that are associated with the ChannelPlacementGroup.',
        ),
    ]


class UpdateChannelPlacementGroupResponse(BaseModel):
    """Placeholder documentation for UpdateChannelPlacementGroupResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this ChannelPlacementGroup. It is automatically assigned when the ChannelPlacementGroup is created.',
        ),
    ]

    channels: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='Channels',
            description='Used in ListChannelPlacementGroupsResult',
        ),
    ]

    cluster_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClusterId',
            description='The ID of the Cluster that the Node belongs to.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the ChannelPlacementGroup. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the ChannelPlacementGroup.',
        ),
    ]

    nodes: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='Nodes',
            description='An array with one item, which is the single Node that is associated with the ChannelPlacementGroup.',
        ),
    ]

    state: Annotated[
        Optional[ChannelPlacementGroupState],
        Field(
            None,
            alias='State',
            description='The current state of the ChannelPlacementGroup.',
        ),
    ]


class ChannelConfigurationValidationError(BaseModel):
    """Placeholder documentation for ChannelConfigurationValidationError."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]

    validation_errors: Annotated[
        Optional[list[ValidationError]],
        Field(
            None,
            alias='ValidationErrors',
            description='A collection of validation error responses.',
        ),
    ]


class VpcOutputSettings(BaseModel):
    """The properties for a private VPC Output When this property is specified, the output egress addresses will be created in a user specified VPC."""

    model_config = ConfigDict(populate_by_name=True)

    public_address_allocation_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='PublicAddressAllocationIds',
            description='List of public address allocation ids to associate with ENIs that will be created in Output VPC. Must specify one for SINGLE_PIPELINE, two for STANDARD channels',
        ),
    ]

    security_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='SecurityGroupIds',
            description='A list of up to 5 EC2 VPC security group IDs to attach to the Output VPC network interfaces. If none are specified then the VPC default security group will be used',
        ),
    ]

    subnet_ids: Annotated[
        list[str],
        Field(
            ...,
            alias='SubnetIds',
            description='A list of VPC subnet IDs from the same VPC. If STANDARD channel, subnet IDs must be mapped to two unique availability zones (AZ).',
        ),
    ]


class VpcOutputSettingsDescription(BaseModel):
    """The properties for a private VPC Output."""

    model_config = ConfigDict(populate_by_name=True)

    availability_zones: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='AvailabilityZones',
            description='The Availability Zones where the vpc subnets are located. The first Availability Zone applies to the first subnet in the list of subnets. The second Availability Zone applies to the second subnet.',
        ),
    ]

    network_interface_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='NetworkInterfaceIds',
            description='A list of Elastic Network Interfaces created by MediaLive in the customer\u0027s VPC',
        ),
    ]

    security_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='SecurityGroupIds',
            description='A list of up EC2 VPC security group IDs attached to the Output VPC network interfaces.',
        ),
    ]

    subnet_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='SubnetIds',
            description='A list of VPC subnet IDs from the same VPC. If STANDARD channel, subnet IDs must be mapped to two unique availability zones (AZ).',
        ),
    ]


class ChannelSummary(BaseModel):
    """Placeholder documentation for ChannelSummary."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The unique arn of the channel.',
        ),
    ]

    cdi_input_specification: Annotated[
        Optional[CdiInputSpecification],
        Field(
            None,
            alias='CdiInputSpecification',
            description='Specification of CDI inputs for this channel',
        ),
    ]

    channel_class: Annotated[
        Optional[ChannelClass],
        Field(
            None,
            alias='ChannelClass',
            description='The class for this channel. STANDARD for a channel with two pipelines or SINGLE_PIPELINE for a channel with one pipeline.',
        ),
    ]

    destinations: Annotated[
        Optional[list[OutputDestination]],
        Field(
            None,
            alias='Destinations',
            description='A list of destinations of the channel. For UDP outputs, there is one destination per output. For other types (HLS, for example), there is one destination per packager.',
        ),
    ]

    egress_endpoints: Annotated[
        Optional[list[ChannelEgressEndpoint]],
        Field(
            None,
            alias='EgressEndpoints',
            description='The endpoints where outgoing connections initiate from',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique id of the channel.',
        ),
    ]

    input_attachments: Annotated[
        Optional[list[InputAttachment]],
        Field(
            None,
            alias='InputAttachments',
            description='List of input attachments for channel.',
        ),
    ]

    input_specification: Annotated[
        Optional[InputSpecification],
        Field(
            None,
            alias='InputSpecification',
            description='Specification of network and file inputs for this channel',
        ),
    ]

    log_level: Annotated[
        Optional[LogLevel],
        Field(
            None,
            alias='LogLevel',
            description='The log level being written to CloudWatch Logs.',
        ),
    ]

    maintenance: Annotated[
        Optional[MaintenanceStatus],
        Field(
            None,
            alias='Maintenance',
            description='Maintenance settings for this channel.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name of the channel. (user-mutable)',
        ),
    ]

    pipelines_running_count: Annotated[
        Optional[int],
        Field(
            None,
            alias='PipelinesRunningCount',
            description='The number of currently healthy pipelines.',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='The Amazon Resource Name (ARN) of the role assumed when running the Channel.',
        ),
    ]

    state: Annotated[
        Optional[ChannelState],
        Field(
            None,
            alias='State',
            description='',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    vpc: Annotated[
        Optional[VpcOutputSettingsDescription],
        Field(
            None,
            alias='Vpc',
            description='Settings for any VPC outputs.',
        ),
    ]

    anywhere_settings: Annotated[
        Optional[DescribeAnywhereSettings],
        Field(
            None,
            alias='AnywhereSettings',
            description='AnywhereSettings settings for this channel.',
        ),
    ]

    channel_engine_version: Annotated[
        Optional[ChannelEngineVersionResponse],
        Field(
            None,
            alias='ChannelEngineVersion',
            description='The engine version that you requested for this channel.',
        ),
    ]

    used_channel_engine_versions: Annotated[
        Optional[list[ChannelEngineVersionResponse]],
        Field(
            None,
            alias='UsedChannelEngineVersions',
            description='The engine version that the running pipelines are using.',
        ),
    ]


class ListChannelsResponse(BaseModel):
    """Placeholder documentation for ListChannelsResponse."""

    model_config = ConfigDict(populate_by_name=True)

    channels: Annotated[
        Optional[list[ChannelSummary]],
        Field(
            None,
            alias='Channels',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='',
        ),
    ]


class ListChannelsResultModel(BaseModel):
    """Placeholder documentation for ListChannelsResultModel."""

    model_config = ConfigDict(populate_by_name=True)

    channels: Annotated[
        Optional[list[ChannelSummary]],
        Field(
            None,
            alias='Channels',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='',
        ),
    ]


class Channel(BaseModel):
    """Placeholder documentation for Channel."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The unique arn of the channel.',
        ),
    ]

    cdi_input_specification: Annotated[
        Optional[CdiInputSpecification],
        Field(
            None,
            alias='CdiInputSpecification',
            description='Specification of CDI inputs for this channel',
        ),
    ]

    channel_class: Annotated[
        Optional[ChannelClass],
        Field(
            None,
            alias='ChannelClass',
            description='The class for this channel. STANDARD for a channel with two pipelines or SINGLE_PIPELINE for a channel with one pipeline.',
        ),
    ]

    destinations: Annotated[
        Optional[list[OutputDestination]],
        Field(
            None,
            alias='Destinations',
            description='A list of destinations of the channel. For UDP outputs, there is one destination per output. For other types (HLS, for example), there is one destination per packager.',
        ),
    ]

    egress_endpoints: Annotated[
        Optional[list[ChannelEgressEndpoint]],
        Field(
            None,
            alias='EgressEndpoints',
            description='The endpoints where outgoing connections initiate from',
        ),
    ]

    encoder_settings: Annotated[
        Optional[EncoderSettings],
        Field(
            None,
            alias='EncoderSettings',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique id of the channel.',
        ),
    ]

    input_attachments: Annotated[
        Optional[list[InputAttachment]],
        Field(
            None,
            alias='InputAttachments',
            description='List of input attachments for channel.',
        ),
    ]

    input_specification: Annotated[
        Optional[InputSpecification],
        Field(
            None,
            alias='InputSpecification',
            description='Specification of network and file inputs for this channel',
        ),
    ]

    log_level: Annotated[
        Optional[LogLevel],
        Field(
            None,
            alias='LogLevel',
            description='The log level being written to CloudWatch Logs.',
        ),
    ]

    maintenance: Annotated[
        Optional[MaintenanceStatus],
        Field(
            None,
            alias='Maintenance',
            description='Maintenance settings for this channel.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name of the channel. (user-mutable)',
        ),
    ]

    pipeline_details: Annotated[
        Optional[list[PipelineDetail]],
        Field(
            None,
            alias='PipelineDetails',
            description='Runtime details for the pipelines of a running channel.',
        ),
    ]

    pipelines_running_count: Annotated[
        Optional[int],
        Field(
            None,
            alias='PipelinesRunningCount',
            description='The number of currently healthy pipelines.',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='The Amazon Resource Name (ARN) of the role assumed when running the Channel.',
        ),
    ]

    state: Annotated[
        Optional[ChannelState],
        Field(
            None,
            alias='State',
            description='',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    vpc: Annotated[
        Optional[VpcOutputSettingsDescription],
        Field(
            None,
            alias='Vpc',
            description='Settings for VPC output',
        ),
    ]

    anywhere_settings: Annotated[
        Optional[DescribeAnywhereSettings],
        Field(
            None,
            alias='AnywhereSettings',
            description='Anywhere settings for this channel.',
        ),
    ]

    channel_engine_version: Annotated[
        Optional[ChannelEngineVersionResponse],
        Field(
            None,
            alias='ChannelEngineVersion',
            description='Requested engine version for this channel.',
        ),
    ]


class CreateChannel(BaseModel):
    """Placeholder documentation for CreateChannel."""

    model_config = ConfigDict(populate_by_name=True)

    cdi_input_specification: Annotated[
        Optional[CdiInputSpecification],
        Field(
            None,
            alias='CdiInputSpecification',
            description='Specification of CDI inputs for this channel',
        ),
    ]

    channel_class: Annotated[
        Optional[ChannelClass],
        Field(
            None,
            alias='ChannelClass',
            description='The class for this channel. STANDARD for a channel with two pipelines or SINGLE_PIPELINE for a channel with one pipeline.',
        ),
    ]

    destinations: Annotated[
        Optional[list[OutputDestination]],
        Field(
            None,
            alias='Destinations',
            description='',
        ),
    ]

    encoder_settings: Annotated[
        Optional[EncoderSettings],
        Field(
            None,
            alias='EncoderSettings',
            description='',
        ),
    ]

    input_attachments: Annotated[
        Optional[list[InputAttachment]],
        Field(
            None,
            alias='InputAttachments',
            description='List of input attachments for channel.',
        ),
    ]

    input_specification: Annotated[
        Optional[InputSpecification],
        Field(
            None,
            alias='InputSpecification',
            description='Specification of network and file inputs for this channel',
        ),
    ]

    log_level: Annotated[
        Optional[LogLevel],
        Field(
            None,
            alias='LogLevel',
            description='The log level to write to CloudWatch Logs.',
        ),
    ]

    maintenance: Annotated[
        Optional[MaintenanceCreateSettings],
        Field(
            None,
            alias='Maintenance',
            description='Maintenance settings for this channel.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Name of channel.',
        ),
    ]

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='Unique request ID to be specified. This is needed to prevent retries from creating multiple resources.',
        ),
    ]

    reserved: Annotated[
        Optional[str],
        Field(
            None,
            alias='Reserved',
            description='Deprecated field that\u0027s only usable by whitelisted customers.',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='An optional Amazon Resource Name (ARN) of the role to assume when running the Channel.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    vpc: Annotated[
        Optional[VpcOutputSettings],
        Field(
            None,
            alias='Vpc',
            description='Settings for the VPC outputs',
        ),
    ]

    anywhere_settings: Annotated[
        Optional[AnywhereSettings],
        Field(
            None,
            alias='AnywhereSettings',
            description='The Elemental Anywhere settings for this channel.',
        ),
    ]

    channel_engine_version: Annotated[
        Optional[ChannelEngineVersionRequest],
        Field(
            None,
            alias='ChannelEngineVersion',
            description='The desired engine version for this channel.',
        ),
    ]

    dry_run: Annotated[
        Optional[bool],
        Field(
            None,
            alias='DryRun',
            description='',
        ),
    ]


class CreateChannelRequest(BaseModel):
    """A request to create a channel."""

    model_config = ConfigDict(populate_by_name=True)

    cdi_input_specification: Annotated[
        Optional[CdiInputSpecification],
        Field(
            None,
            alias='CdiInputSpecification',
            description='Specification of CDI inputs for this channel',
        ),
    ]

    channel_class: Annotated[
        Optional[ChannelClass],
        Field(
            None,
            alias='ChannelClass',
            description='The class for this channel. STANDARD for a channel with two pipelines or SINGLE_PIPELINE for a channel with one pipeline.',
        ),
    ]

    destinations: Annotated[
        Optional[list[OutputDestination]],
        Field(
            None,
            alias='Destinations',
            description='',
        ),
    ]

    encoder_settings: Annotated[
        Optional[EncoderSettings],
        Field(
            None,
            alias='EncoderSettings',
            description='',
        ),
    ]

    input_attachments: Annotated[
        Optional[list[InputAttachment]],
        Field(
            None,
            alias='InputAttachments',
            description='List of input attachments for channel.',
        ),
    ]

    input_specification: Annotated[
        Optional[InputSpecification],
        Field(
            None,
            alias='InputSpecification',
            description='Specification of network and file inputs for this channel',
        ),
    ]

    log_level: Annotated[
        Optional[LogLevel],
        Field(
            None,
            alias='LogLevel',
            description='The log level to write to CloudWatch Logs.',
        ),
    ]

    maintenance: Annotated[
        Optional[MaintenanceCreateSettings],
        Field(
            None,
            alias='Maintenance',
            description='Maintenance settings for this channel.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Name of channel.',
        ),
    ]

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='Unique request ID to be specified. This is needed to prevent retries from creating multiple resources.',
        ),
    ]

    reserved: Annotated[
        Optional[str],
        Field(
            None,
            alias='Reserved',
            description='Deprecated field that\u0027s only usable by whitelisted customers.',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='An optional Amazon Resource Name (ARN) of the role to assume when running the Channel.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    vpc: Annotated[
        Optional[VpcOutputSettings],
        Field(
            None,
            alias='Vpc',
            description='Settings for the VPC outputs',
        ),
    ]

    anywhere_settings: Annotated[
        Optional[AnywhereSettings],
        Field(
            None,
            alias='AnywhereSettings',
            description='The Elemental Anywhere settings for this channel.',
        ),
    ]

    channel_engine_version: Annotated[
        Optional[ChannelEngineVersionRequest],
        Field(
            None,
            alias='ChannelEngineVersion',
            description='The desired engine version for this channel.',
        ),
    ]

    dry_run: Annotated[
        Optional[bool],
        Field(
            None,
            alias='DryRun',
            description='',
        ),
    ]


class CreateChannelResponse(BaseModel):
    """Placeholder documentation for CreateChannelResponse."""

    model_config = ConfigDict(populate_by_name=True)

    channel: Annotated[
        Optional[Channel],
        Field(
            None,
            alias='Channel',
            description='',
        ),
    ]


class CreateChannelResultModel(BaseModel):
    """Placeholder documentation for CreateChannelResultModel."""

    model_config = ConfigDict(populate_by_name=True)

    channel: Annotated[
        Optional[Channel],
        Field(
            None,
            alias='Channel',
            description='',
        ),
    ]


class DeleteChannelResponse(BaseModel):
    """Placeholder documentation for DeleteChannelResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The unique arn of the channel.',
        ),
    ]

    cdi_input_specification: Annotated[
        Optional[CdiInputSpecification],
        Field(
            None,
            alias='CdiInputSpecification',
            description='Specification of CDI inputs for this channel',
        ),
    ]

    channel_class: Annotated[
        Optional[ChannelClass],
        Field(
            None,
            alias='ChannelClass',
            description='The class for this channel. STANDARD for a channel with two pipelines or SINGLE_PIPELINE for a channel with one pipeline.',
        ),
    ]

    destinations: Annotated[
        Optional[list[OutputDestination]],
        Field(
            None,
            alias='Destinations',
            description='A list of destinations of the channel. For UDP outputs, there is one destination per output. For other types (HLS, for example), there is one destination per packager.',
        ),
    ]

    egress_endpoints: Annotated[
        Optional[list[ChannelEgressEndpoint]],
        Field(
            None,
            alias='EgressEndpoints',
            description='The endpoints where outgoing connections initiate from',
        ),
    ]

    encoder_settings: Annotated[
        Optional[EncoderSettings],
        Field(
            None,
            alias='EncoderSettings',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique id of the channel.',
        ),
    ]

    input_attachments: Annotated[
        Optional[list[InputAttachment]],
        Field(
            None,
            alias='InputAttachments',
            description='List of input attachments for channel.',
        ),
    ]

    input_specification: Annotated[
        Optional[InputSpecification],
        Field(
            None,
            alias='InputSpecification',
            description='Specification of network and file inputs for this channel',
        ),
    ]

    log_level: Annotated[
        Optional[LogLevel],
        Field(
            None,
            alias='LogLevel',
            description='The log level being written to CloudWatch Logs.',
        ),
    ]

    maintenance: Annotated[
        Optional[MaintenanceStatus],
        Field(
            None,
            alias='Maintenance',
            description='Maintenance settings for this channel.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name of the channel. (user-mutable)',
        ),
    ]

    pipeline_details: Annotated[
        Optional[list[PipelineDetail]],
        Field(
            None,
            alias='PipelineDetails',
            description='Runtime details for the pipelines of a running channel.',
        ),
    ]

    pipelines_running_count: Annotated[
        Optional[int],
        Field(
            None,
            alias='PipelinesRunningCount',
            description='The number of currently healthy pipelines.',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='The Amazon Resource Name (ARN) of the role assumed when running the Channel.',
        ),
    ]

    state: Annotated[
        Optional[ChannelState],
        Field(
            None,
            alias='State',
            description='',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    vpc: Annotated[
        Optional[VpcOutputSettingsDescription],
        Field(
            None,
            alias='Vpc',
            description='Settings for VPC output',
        ),
    ]

    anywhere_settings: Annotated[
        Optional[DescribeAnywhereSettings],
        Field(
            None,
            alias='AnywhereSettings',
            description='Anywhere settings for this channel.',
        ),
    ]

    channel_engine_version: Annotated[
        Optional[ChannelEngineVersionResponse],
        Field(
            None,
            alias='ChannelEngineVersion',
            description='Requested engine version for this channel.',
        ),
    ]


class DescribeChannelResponse(BaseModel):
    """Placeholder documentation for DescribeChannelResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The unique arn of the channel.',
        ),
    ]

    cdi_input_specification: Annotated[
        Optional[CdiInputSpecification],
        Field(
            None,
            alias='CdiInputSpecification',
            description='Specification of CDI inputs for this channel',
        ),
    ]

    channel_class: Annotated[
        Optional[ChannelClass],
        Field(
            None,
            alias='ChannelClass',
            description='The class for this channel. STANDARD for a channel with two pipelines or SINGLE_PIPELINE for a channel with one pipeline.',
        ),
    ]

    destinations: Annotated[
        Optional[list[OutputDestination]],
        Field(
            None,
            alias='Destinations',
            description='A list of destinations of the channel. For UDP outputs, there is one destination per output. For other types (HLS, for example), there is one destination per packager.',
        ),
    ]

    egress_endpoints: Annotated[
        Optional[list[ChannelEgressEndpoint]],
        Field(
            None,
            alias='EgressEndpoints',
            description='The endpoints where outgoing connections initiate from',
        ),
    ]

    encoder_settings: Annotated[
        Optional[EncoderSettings],
        Field(
            None,
            alias='EncoderSettings',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique id of the channel.',
        ),
    ]

    input_attachments: Annotated[
        Optional[list[InputAttachment]],
        Field(
            None,
            alias='InputAttachments',
            description='List of input attachments for channel.',
        ),
    ]

    input_specification: Annotated[
        Optional[InputSpecification],
        Field(
            None,
            alias='InputSpecification',
            description='Specification of network and file inputs for this channel',
        ),
    ]

    log_level: Annotated[
        Optional[LogLevel],
        Field(
            None,
            alias='LogLevel',
            description='The log level being written to CloudWatch Logs.',
        ),
    ]

    maintenance: Annotated[
        Optional[MaintenanceStatus],
        Field(
            None,
            alias='Maintenance',
            description='Maintenance settings for this channel.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name of the channel. (user-mutable)',
        ),
    ]

    pipeline_details: Annotated[
        Optional[list[PipelineDetail]],
        Field(
            None,
            alias='PipelineDetails',
            description='Runtime details for the pipelines of a running channel.',
        ),
    ]

    pipelines_running_count: Annotated[
        Optional[int],
        Field(
            None,
            alias='PipelinesRunningCount',
            description='The number of currently healthy pipelines.',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='The Amazon Resource Name (ARN) of the role assumed when running the Channel.',
        ),
    ]

    state: Annotated[
        Optional[ChannelState],
        Field(
            None,
            alias='State',
            description='',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    vpc: Annotated[
        Optional[VpcOutputSettingsDescription],
        Field(
            None,
            alias='Vpc',
            description='Settings for VPC output',
        ),
    ]

    anywhere_settings: Annotated[
        Optional[DescribeAnywhereSettings],
        Field(
            None,
            alias='AnywhereSettings',
            description='Anywhere settings for this channel.',
        ),
    ]

    channel_engine_version: Annotated[
        Optional[ChannelEngineVersionResponse],
        Field(
            None,
            alias='ChannelEngineVersion',
            description='Requested engine version for this channel.',
        ),
    ]


class RestartChannelPipelinesResponse(BaseModel):
    """Placeholder documentation for RestartChannelPipelinesResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The unique arn of the channel.',
        ),
    ]

    cdi_input_specification: Annotated[
        Optional[CdiInputSpecification],
        Field(
            None,
            alias='CdiInputSpecification',
            description='Specification of CDI inputs for this channel',
        ),
    ]

    channel_class: Annotated[
        Optional[ChannelClass],
        Field(
            None,
            alias='ChannelClass',
            description='The class for this channel. STANDARD for a channel with two pipelines or SINGLE_PIPELINE for a channel with one pipeline.',
        ),
    ]

    destinations: Annotated[
        Optional[list[OutputDestination]],
        Field(
            None,
            alias='Destinations',
            description='A list of destinations of the channel. For UDP outputs, there is one destination per output. For other types (HLS, for example), there is one destination per packager.',
        ),
    ]

    egress_endpoints: Annotated[
        Optional[list[ChannelEgressEndpoint]],
        Field(
            None,
            alias='EgressEndpoints',
            description='The endpoints where outgoing connections initiate from',
        ),
    ]

    encoder_settings: Annotated[
        Optional[EncoderSettings],
        Field(
            None,
            alias='EncoderSettings',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique id of the channel.',
        ),
    ]

    input_attachments: Annotated[
        Optional[list[InputAttachment]],
        Field(
            None,
            alias='InputAttachments',
            description='List of input attachments for channel.',
        ),
    ]

    input_specification: Annotated[
        Optional[InputSpecification],
        Field(
            None,
            alias='InputSpecification',
            description='Specification of network and file inputs for this channel',
        ),
    ]

    log_level: Annotated[
        Optional[LogLevel],
        Field(
            None,
            alias='LogLevel',
            description='The log level being written to CloudWatch Logs.',
        ),
    ]

    maintenance: Annotated[
        Optional[MaintenanceStatus],
        Field(
            None,
            alias='Maintenance',
            description='Maintenance settings for this channel.',
        ),
    ]

    maintenance_status: Annotated[
        Optional[str],
        Field(
            None,
            alias='MaintenanceStatus',
            description='The time in milliseconds by when the PVRE restart must occur.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name of the channel. (user-mutable)',
        ),
    ]

    pipeline_details: Annotated[
        Optional[list[PipelineDetail]],
        Field(
            None,
            alias='PipelineDetails',
            description='Runtime details for the pipelines of a running channel.',
        ),
    ]

    pipelines_running_count: Annotated[
        Optional[int],
        Field(
            None,
            alias='PipelinesRunningCount',
            description='The number of currently healthy pipelines.',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='The Amazon Resource Name (ARN) of the role assumed when running the Channel.',
        ),
    ]

    state: Annotated[
        Optional[ChannelState],
        Field(
            None,
            alias='State',
            description='',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    vpc: Annotated[
        Optional[VpcOutputSettingsDescription],
        Field(
            None,
            alias='Vpc',
            description='Settings for VPC output',
        ),
    ]

    anywhere_settings: Annotated[
        Optional[DescribeAnywhereSettings],
        Field(
            None,
            alias='AnywhereSettings',
            description='Anywhere settings for this channel.',
        ),
    ]

    channel_engine_version: Annotated[
        Optional[ChannelEngineVersionResponse],
        Field(
            None,
            alias='ChannelEngineVersion',
            description='Requested engine version for this channel.',
        ),
    ]


class StartChannelResponse(BaseModel):
    """Placeholder documentation for StartChannelResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The unique arn of the channel.',
        ),
    ]

    cdi_input_specification: Annotated[
        Optional[CdiInputSpecification],
        Field(
            None,
            alias='CdiInputSpecification',
            description='Specification of CDI inputs for this channel',
        ),
    ]

    channel_class: Annotated[
        Optional[ChannelClass],
        Field(
            None,
            alias='ChannelClass',
            description='The class for this channel. STANDARD for a channel with two pipelines or SINGLE_PIPELINE for a channel with one pipeline.',
        ),
    ]

    destinations: Annotated[
        Optional[list[OutputDestination]],
        Field(
            None,
            alias='Destinations',
            description='A list of destinations of the channel. For UDP outputs, there is one destination per output. For other types (HLS, for example), there is one destination per packager.',
        ),
    ]

    egress_endpoints: Annotated[
        Optional[list[ChannelEgressEndpoint]],
        Field(
            None,
            alias='EgressEndpoints',
            description='The endpoints where outgoing connections initiate from',
        ),
    ]

    encoder_settings: Annotated[
        Optional[EncoderSettings],
        Field(
            None,
            alias='EncoderSettings',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique id of the channel.',
        ),
    ]

    input_attachments: Annotated[
        Optional[list[InputAttachment]],
        Field(
            None,
            alias='InputAttachments',
            description='List of input attachments for channel.',
        ),
    ]

    input_specification: Annotated[
        Optional[InputSpecification],
        Field(
            None,
            alias='InputSpecification',
            description='Specification of network and file inputs for this channel',
        ),
    ]

    log_level: Annotated[
        Optional[LogLevel],
        Field(
            None,
            alias='LogLevel',
            description='The log level being written to CloudWatch Logs.',
        ),
    ]

    maintenance: Annotated[
        Optional[MaintenanceStatus],
        Field(
            None,
            alias='Maintenance',
            description='Maintenance settings for this channel.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name of the channel. (user-mutable)',
        ),
    ]

    pipeline_details: Annotated[
        Optional[list[PipelineDetail]],
        Field(
            None,
            alias='PipelineDetails',
            description='Runtime details for the pipelines of a running channel.',
        ),
    ]

    pipelines_running_count: Annotated[
        Optional[int],
        Field(
            None,
            alias='PipelinesRunningCount',
            description='The number of currently healthy pipelines.',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='The Amazon Resource Name (ARN) of the role assumed when running the Channel.',
        ),
    ]

    state: Annotated[
        Optional[ChannelState],
        Field(
            None,
            alias='State',
            description='',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    vpc: Annotated[
        Optional[VpcOutputSettingsDescription],
        Field(
            None,
            alias='Vpc',
            description='Settings for VPC output',
        ),
    ]

    anywhere_settings: Annotated[
        Optional[DescribeAnywhereSettings],
        Field(
            None,
            alias='AnywhereSettings',
            description='Anywhere settings for this channel.',
        ),
    ]

    channel_engine_version: Annotated[
        Optional[ChannelEngineVersionResponse],
        Field(
            None,
            alias='ChannelEngineVersion',
            description='Requested engine version for this channel.',
        ),
    ]


class StopChannelResponse(BaseModel):
    """Placeholder documentation for StopChannelResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The unique arn of the channel.',
        ),
    ]

    cdi_input_specification: Annotated[
        Optional[CdiInputSpecification],
        Field(
            None,
            alias='CdiInputSpecification',
            description='Specification of CDI inputs for this channel',
        ),
    ]

    channel_class: Annotated[
        Optional[ChannelClass],
        Field(
            None,
            alias='ChannelClass',
            description='The class for this channel. STANDARD for a channel with two pipelines or SINGLE_PIPELINE for a channel with one pipeline.',
        ),
    ]

    destinations: Annotated[
        Optional[list[OutputDestination]],
        Field(
            None,
            alias='Destinations',
            description='A list of destinations of the channel. For UDP outputs, there is one destination per output. For other types (HLS, for example), there is one destination per packager.',
        ),
    ]

    egress_endpoints: Annotated[
        Optional[list[ChannelEgressEndpoint]],
        Field(
            None,
            alias='EgressEndpoints',
            description='The endpoints where outgoing connections initiate from',
        ),
    ]

    encoder_settings: Annotated[
        Optional[EncoderSettings],
        Field(
            None,
            alias='EncoderSettings',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique id of the channel.',
        ),
    ]

    input_attachments: Annotated[
        Optional[list[InputAttachment]],
        Field(
            None,
            alias='InputAttachments',
            description='List of input attachments for channel.',
        ),
    ]

    input_specification: Annotated[
        Optional[InputSpecification],
        Field(
            None,
            alias='InputSpecification',
            description='Specification of network and file inputs for this channel',
        ),
    ]

    log_level: Annotated[
        Optional[LogLevel],
        Field(
            None,
            alias='LogLevel',
            description='The log level being written to CloudWatch Logs.',
        ),
    ]

    maintenance: Annotated[
        Optional[MaintenanceStatus],
        Field(
            None,
            alias='Maintenance',
            description='Maintenance settings for this channel.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name of the channel. (user-mutable)',
        ),
    ]

    pipeline_details: Annotated[
        Optional[list[PipelineDetail]],
        Field(
            None,
            alias='PipelineDetails',
            description='Runtime details for the pipelines of a running channel.',
        ),
    ]

    pipelines_running_count: Annotated[
        Optional[int],
        Field(
            None,
            alias='PipelinesRunningCount',
            description='The number of currently healthy pipelines.',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='The Amazon Resource Name (ARN) of the role assumed when running the Channel.',
        ),
    ]

    state: Annotated[
        Optional[ChannelState],
        Field(
            None,
            alias='State',
            description='',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    vpc: Annotated[
        Optional[VpcOutputSettingsDescription],
        Field(
            None,
            alias='Vpc',
            description='Settings for VPC output',
        ),
    ]

    anywhere_settings: Annotated[
        Optional[DescribeAnywhereSettings],
        Field(
            None,
            alias='AnywhereSettings',
            description='Anywhere settings for this channel.',
        ),
    ]

    channel_engine_version: Annotated[
        Optional[ChannelEngineVersionResponse],
        Field(
            None,
            alias='ChannelEngineVersion',
            description='Requested engine version for this channel.',
        ),
    ]


class UpdateChannel(BaseModel):
    """Placeholder documentation for UpdateChannel."""

    model_config = ConfigDict(populate_by_name=True)

    cdi_input_specification: Annotated[
        Optional[CdiInputSpecification],
        Field(
            None,
            alias='CdiInputSpecification',
            description='Specification of CDI inputs for this channel',
        ),
    ]

    destinations: Annotated[
        Optional[list[OutputDestination]],
        Field(
            None,
            alias='Destinations',
            description='A list of output destinations for this channel.',
        ),
    ]

    encoder_settings: Annotated[
        Optional[EncoderSettings],
        Field(
            None,
            alias='EncoderSettings',
            description='The encoder settings for this channel.',
        ),
    ]

    input_attachments: Annotated[
        Optional[list[InputAttachment]],
        Field(
            None,
            alias='InputAttachments',
            description='',
        ),
    ]

    input_specification: Annotated[
        Optional[InputSpecification],
        Field(
            None,
            alias='InputSpecification',
            description='Specification of network and file inputs for this channel',
        ),
    ]

    log_level: Annotated[
        Optional[LogLevel],
        Field(
            None,
            alias='LogLevel',
            description='The log level to write to CloudWatch Logs.',
        ),
    ]

    maintenance: Annotated[
        Optional[MaintenanceUpdateSettings],
        Field(
            None,
            alias='Maintenance',
            description='Maintenance settings for this channel.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name of the channel.',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='An optional Amazon Resource Name (ARN) of the role to assume when running the Channel. If you do not specify this on an update call but the role was previously set that role will be removed.',
        ),
    ]

    channel_engine_version: Annotated[
        Optional[ChannelEngineVersionRequest],
        Field(
            None,
            alias='ChannelEngineVersion',
            description='Channel engine version for this channel',
        ),
    ]

    dry_run: Annotated[
        Optional[bool],
        Field(
            None,
            alias='DryRun',
            description='',
        ),
    ]

    anywhere_settings: Annotated[
        Optional[AnywhereSettings],
        Field(
            None,
            alias='AnywhereSettings',
            description='The Elemental Anywhere settings for this channel.',
        ),
    ]


class UpdateChannelClassResponse(BaseModel):
    """Placeholder documentation for UpdateChannelClassResponse."""

    model_config = ConfigDict(populate_by_name=True)

    channel: Annotated[
        Optional[Channel],
        Field(
            None,
            alias='Channel',
            description='',
        ),
    ]


class UpdateChannelRequest(BaseModel):
    """A request to update a channel."""

    model_config = ConfigDict(populate_by_name=True)

    cdi_input_specification: Annotated[
        Optional[CdiInputSpecification],
        Field(
            None,
            alias='CdiInputSpecification',
            description='Specification of CDI inputs for this channel',
        ),
    ]

    channel_id: Annotated[
        str,
        Field(
            ...,
            alias='ChannelId',
            description='channel ID',
        ),
    ]

    destinations: Annotated[
        Optional[list[OutputDestination]],
        Field(
            None,
            alias='Destinations',
            description='A list of output destinations for this channel.',
        ),
    ]

    encoder_settings: Annotated[
        Optional[EncoderSettings],
        Field(
            None,
            alias='EncoderSettings',
            description='The encoder settings for this channel.',
        ),
    ]

    input_attachments: Annotated[
        Optional[list[InputAttachment]],
        Field(
            None,
            alias='InputAttachments',
            description='',
        ),
    ]

    input_specification: Annotated[
        Optional[InputSpecification],
        Field(
            None,
            alias='InputSpecification',
            description='Specification of network and file inputs for this channel',
        ),
    ]

    log_level: Annotated[
        Optional[LogLevel],
        Field(
            None,
            alias='LogLevel',
            description='The log level to write to CloudWatch Logs.',
        ),
    ]

    maintenance: Annotated[
        Optional[MaintenanceUpdateSettings],
        Field(
            None,
            alias='Maintenance',
            description='Maintenance settings for this channel.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name of the channel.',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='An optional Amazon Resource Name (ARN) of the role to assume when running the Channel. If you do not specify this on an update call but the role was previously set that role will be removed.',
        ),
    ]

    channel_engine_version: Annotated[
        Optional[ChannelEngineVersionRequest],
        Field(
            None,
            alias='ChannelEngineVersion',
            description='Channel engine version for this channel',
        ),
    ]

    dry_run: Annotated[
        Optional[bool],
        Field(
            None,
            alias='DryRun',
            description='',
        ),
    ]

    anywhere_settings: Annotated[
        Optional[AnywhereSettings],
        Field(
            None,
            alias='AnywhereSettings',
            description='The Elemental Anywhere settings for this channel.',
        ),
    ]


class UpdateChannelResponse(BaseModel):
    """Placeholder documentation for UpdateChannelResponse."""

    model_config = ConfigDict(populate_by_name=True)

    channel: Annotated[
        Optional[Channel],
        Field(
            None,
            alias='Channel',
            description='',
        ),
    ]


class UpdateChannelResultModel(BaseModel):
    """The updated channel's description."""

    model_config = ConfigDict(populate_by_name=True)

    channel: Annotated[
        Optional[Channel],
        Field(
            None,
            alias='Channel',
            description='',
        ),
    ]
