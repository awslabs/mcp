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

"""Infrastructure-related Pydantic models — clusters, nodes, networks, SDI, tags."""

from __future__ import annotations

from awslabs.amazon_medialive_mcp_server.enums import (
    NetworkInterfaceMode,
    SdiSourceMode,
    SdiSourceState,
    SdiSourceType,
)
from pydantic import BaseModel, ConfigDict, Field
from typing import TYPE_CHECKING, Annotated, Optional


if TYPE_CHECKING:
    from awslabs.amazon_medialive_mcp_server.models.common import (
        InterfaceMapping,
        InterfaceMappingCreateRequest,
        InterfaceMappingUpdateRequest,
        ValidationError,
    )


class AccountConfiguration(BaseModel):
    """Placeholder documentation for AccountConfiguration."""

    model_config = ConfigDict(populate_by_name=True)

    kms_key_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='KmsKeyId',
            description='Specifies the KMS key to use for all features that use key encryption. Specify the ARN of a KMS key that you have created. Or leave blank to use the key that MediaLive creates and manages for you.',
        ),
    ]


class DescribeAccountConfigurationRequest(BaseModel):
    """Placeholder documentation for DescribeAccountConfigurationRequest."""

    model_config = ConfigDict(populate_by_name=True)


class DescribeAccountConfigurationResponse(BaseModel):
    """Placeholder documentation for DescribeAccountConfigurationResponse."""

    model_config = ConfigDict(populate_by_name=True)

    account_configuration: Annotated[
        Optional[AccountConfiguration],
        Field(
            None,
            alias='AccountConfiguration',
            description='',
        ),
    ]


class DescribeAccountConfigurationResultModel(BaseModel):
    """The account's configuration."""

    model_config = ConfigDict(populate_by_name=True)

    account_configuration: Annotated[
        Optional[AccountConfiguration],
        Field(
            None,
            alias='AccountConfiguration',
            description='',
        ),
    ]


class ClusterNetworkSettings(BaseModel):
    """Used in DescribeClusterResult, DescribeClusterSummary, UpdateClusterResult."""

    model_config = ConfigDict(populate_by_name=True)

    default_route: Annotated[
        Optional[str],
        Field(
            None,
            alias='DefaultRoute',
            description='The network interface that is the default route for traffic to and from the node. MediaLive Anywhere uses this default when the destination for the traffic isn\u0027t covered by the route table for any of the networks. Specify the value of the appropriate logicalInterfaceName parameter that you create in the interfaceMappings.',
        ),
    ]

    interface_mappings: Annotated[
        Optional[list[InterfaceMapping]],
        Field(
            None,
            alias='InterfaceMappings',
            description='An array of interfaceMapping objects for this Cluster. Each mapping logically connects one interface on the nodes with one Network. You need only one mapping for each interface because all the Nodes share the mapping.',
        ),
    ]


class ClusterNetworkSettingsCreateRequest(BaseModel):
    """Used in a CreateClusterRequest."""

    model_config = ConfigDict(populate_by_name=True)

    default_route: Annotated[
        Optional[str],
        Field(
            None,
            alias='DefaultRoute',
            description='Specify one network interface as the default route for traffic to and from the Node. MediaLive Anywhere uses this default when the destination for the traffic isn\u0027t covered by the route table for any of the networks. Specify the value of the appropriate logicalInterfaceName parameter that you create in the interfaceMappings.',
        ),
    ]

    interface_mappings: Annotated[
        Optional[list[InterfaceMappingCreateRequest]],
        Field(
            None,
            alias='InterfaceMappings',
            description='An array of interfaceMapping objects for this Cluster. You must create a mapping for node interfaces that you plan to use for encoding traffic. You typically don\u0027t create a mapping for the management interface. You define this mapping in the Cluster so that the mapping can be used by all the Nodes. Each mapping logically connects one interface on the nodes with one Network. Each mapping consists of a pair of parameters. The logicalInterfaceName parameter creates a logical name for the Node interface that handles a specific type of traffic. For example, my-Inputs-Interface. The networkID parameter refers to the ID of the network. When you create the Nodes in this Cluster, you will associate the logicalInterfaceName with the appropriate physical interface.',
        ),
    ]


class ClusterNetworkSettingsUpdateRequest(BaseModel):
    """Placeholder documentation for ClusterNetworkSettingsUpdateRequest."""

    model_config = ConfigDict(populate_by_name=True)

    default_route: Annotated[
        Optional[str],
        Field(
            None,
            alias='DefaultRoute',
            description='Include this parameter only if you want to change the default route for the Cluster. Specify one network interface as the default route for traffic to and from the node. MediaLive Anywhere uses this default when the destination for the traffic isn\u0027t covered by the route table for any of the networks. Specify the value of the appropriate logicalInterfaceName parameter that you create in the interfaceMappings.',
        ),
    ]

    interface_mappings: Annotated[
        Optional[list[InterfaceMappingUpdateRequest]],
        Field(
            None,
            alias='InterfaceMappings',
            description='An array of interfaceMapping objects for this Cluster. Include this parameter only if you want to change the interface mappings for the Cluster. Typically, you change the interface mappings only to fix an error you made when creating the mapping. In an update request, make sure that you enter the entire set of mappings again, not just the mappings that you want to add or change. You define this mapping so that the mapping can be used by all the Nodes. Each mapping logically connects one interface on the nodes with one Network. Each mapping consists of a pair of parameters. The logicalInterfaceName parameter creates a logical name for the Node interface that handles a specific type of traffic. For example, my-Inputs-Interface. The networkID parameter refers to the ID of the network. When you create the Nodes in this Cluster, you will associate the logicalInterfaceName with the appropriate physical interface.',
        ),
    ]


class ListTagsForResourceRequest(BaseModel):
    """Placeholder documentation for ListTagsForResourceRequest."""

    model_config = ConfigDict(populate_by_name=True)

    resource_arn: Annotated[
        str,
        Field(
            ...,
            alias='ResourceArn',
            description='',
        ),
    ]


class ListTagsForResourceResponse(BaseModel):
    """Placeholder documentation for ListTagsForResourceResponse."""

    model_config = ConfigDict(populate_by_name=True)

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='',
        ),
    ]


class NodeInterfaceMapping(BaseModel):
    """A mapping that's used to pair a logical network interface name on a Node with the physical interface name exposed in the operating system."""

    model_config = ConfigDict(populate_by_name=True)

    logical_interface_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='LogicalInterfaceName',
            description='A uniform logical interface name to address in a MediaLive channel configuration.',
        ),
    ]

    network_interface_mode: Annotated[
        Optional[NetworkInterfaceMode],
        Field(
            None,
            alias='NetworkInterfaceMode',
            description='',
        ),
    ]

    physical_interface_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='PhysicalInterfaceName',
            description='The name of the physical interface on the hardware that will be running Elemental anywhere.',
        ),
    ]


class NodeInterfaceMappingCreateRequest(BaseModel):
    """Used in CreateNodeRequest."""

    model_config = ConfigDict(populate_by_name=True)

    logical_interface_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='LogicalInterfaceName',
            description='Specify one of the logicalInterfaceNames that you created in the Cluster that this node belongs to. For example, my-Inputs-Interface.',
        ),
    ]

    network_interface_mode: Annotated[
        Optional[NetworkInterfaceMode],
        Field(
            None,
            alias='NetworkInterfaceMode',
            description='The style of the network -- NAT or BRIDGE.',
        ),
    ]

    physical_interface_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='PhysicalInterfaceName',
            description='Specify the physical name that corresponds to the logicalInterfaceName that you specified in this interface mapping. For example, Eth1 or ENO1234EXAMPLE.',
        ),
    ]


class SdiSource(BaseModel):
    """Used in CreateSdiSourceResponse, DeleteSdiSourceResponse, DescribeSdiSourceResponse, ListSdiSourcesResponse, UpdateSdiSourceResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this SdiSource. It is automatically assigned when the SdiSource is created.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the SdiSource. Unique in the AWS account.The ID is the resource-id portion of the ARN.',
        ),
    ]

    inputs: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='Inputs',
            description='The list of inputs that are currently using this SDI source. This list will be empty if the SdiSource has just been deleted.',
        ),
    ]

    mode: Annotated[
        Optional[SdiSourceMode],
        Field(
            None,
            alias='Mode',
            description='Applies only if the type is QUAD. The mode for handling the quad-link signal QUADRANT or INTERLEAVE.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name of the SdiSource.',
        ),
    ]

    state: Annotated[
        Optional[SdiSourceState],
        Field(
            None,
            alias='State',
            description='Specifies whether the SDI source is attached to an SDI input (IN_USE) or not (IDLE).',
        ),
    ]

    type: Annotated[
        Optional[SdiSourceType],
        Field(
            None,
            alias='Type',
            description='',
        ),
    ]


class SdiSourceMapping(BaseModel):
    """Used in DescribeNodeSummary, DescribeNodeResult."""

    model_config = ConfigDict(populate_by_name=True)

    card_number: Annotated[
        Optional[int],
        Field(
            None,
            alias='CardNumber',
            description='A number that uniquely identifies the SDI card on the node hardware.',
        ),
    ]

    channel_number: Annotated[
        Optional[int],
        Field(
            None,
            alias='ChannelNumber',
            description='A number that uniquely identifies a port on the SDI card.',
        ),
    ]

    sdi_source: Annotated[
        Optional[str],
        Field(
            None,
            alias='SdiSource',
            description='The ID of the SdiSource to associate with this port on this card. You can use the ListSdiSources operation to discover all the IDs.',
        ),
    ]


class SdiSourceMappingUpdateRequest(BaseModel):
    """Used in SdiSourceMappingsUpdateRequest. One SDI source mapping. It connects one logical SdiSource to the physical SDI card and port that the physical SDI source uses. You must specify all three parameters in this object."""

    model_config = ConfigDict(populate_by_name=True)

    card_number: Annotated[
        Optional[int],
        Field(
            None,
            alias='CardNumber',
            description='A number that uniquely identifies the SDI card on the node hardware. For information about how physical cards are identified on your node hardware, see the documentation for your node hardware. The numbering always starts at 1.',
        ),
    ]

    channel_number: Annotated[
        Optional[int],
        Field(
            None,
            alias='ChannelNumber',
            description='A number that uniquely identifies a port on the card. This must be an SDI port (not a timecode port, for example). For information about how ports are identified on physical cards, see the documentation for your node hardware.',
        ),
    ]

    sdi_source: Annotated[
        Optional[str],
        Field(
            None,
            alias='SdiSource',
            description='The ID of a SDI source streaming on the given SDI capture card port.',
        ),
    ]


class SdiSourceSummary(BaseModel):
    """Used in CreateSdiSourceResponse, DeleteSdiSourceResponse, DescribeSdiSourceResponse, ListSdiSourcesResponse, UpdateSdiSourceResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this SdiSource. It is automatically assigned when the SdiSource is created.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the SdiSource. Unique in the AWS account.The ID is the resource-id portion of the ARN.',
        ),
    ]

    inputs: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='Inputs',
            description='The list of inputs that are currently using this SDI source. This list will be empty if the SdiSource has just been deleted.',
        ),
    ]

    mode: Annotated[
        Optional[SdiSourceMode],
        Field(
            None,
            alias='Mode',
            description='Applies only if the type is QUAD. The mode for handling the quad-link signal QUADRANT or INTERLEAVE.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name of the SdiSource.',
        ),
    ]

    state: Annotated[
        Optional[SdiSourceState],
        Field(
            None,
            alias='State',
            description='Specifies whether the SDI source is attached to an SDI input (IN_USE) or not (IDLE).',
        ),
    ]

    type: Annotated[
        Optional[SdiSourceType],
        Field(
            None,
            alias='Type',
            description='',
        ),
    ]


class TagsModel(BaseModel):
    """Placeholder documentation for TagsModel."""

    model_config = ConfigDict(populate_by_name=True)

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='',
        ),
    ]


class NodeConfigurationValidationError(BaseModel):
    """Details about a configuration error on the Node."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='The error message.',
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
