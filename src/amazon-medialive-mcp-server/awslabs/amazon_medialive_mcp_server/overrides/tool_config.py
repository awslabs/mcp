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

# Hand-written tool configuration for MediaLive MCP server.
# Controls which API operations are exposed as MCP tools and annotates
# them as read-only or destructive for safety metadata.

# Curated set of operations to expose as MCP tools.
# Only these operations receive @mcp.tool() decoration.
INCLUDED_OPERATIONS: set[str] = {
    # Channel CRUD and lifecycle
    'CreateChannel',
    'DeleteChannel',
    'DescribeChannel',
    'ListChannels',
    'StartChannel',
    'StopChannel',
    'UpdateChannel',
    'UpdateChannelClass',
    # Input CRUD
    'CreateInput',
    'DeleteInput',
    'DescribeInput',
    'ListInputs',
    'UpdateInput',
    # Input security groups
    'CreateInputSecurityGroup',
    'DeleteInputSecurityGroup',
    'DescribeInputSecurityGroup',
    'ListInputSecurityGroups',
    'UpdateInputSecurityGroup',
    # Multiplex CRUD and lifecycle
    'CreateMultiplex',
    'DeleteMultiplex',
    'DescribeMultiplex',
    'ListMultiplexes',
    'StartMultiplex',
    'StopMultiplex',
    'UpdateMultiplex',
    # Multiplex programs
    'CreateMultiplexProgram',
    'DeleteMultiplexProgram',
    'DescribeMultiplexProgram',
    'ListMultiplexPrograms',
    'UpdateMultiplexProgram',
    # Schedule management
    'BatchUpdateSchedule',
    'DescribeSchedule',
    'DeleteSchedule',
    # Input devices
    'DescribeInputDevice',
    'ListInputDevices',
    # Offerings and reservations
    'DescribeOffering',
    'DescribeReservation',
    'ListOfferings',
    'ListReservations',
    # Account configuration
    'DescribeAccountConfiguration',
    # Tags
    'ListTagsForResource',
    'CreateTags',
    'DeleteTags',
    # Thumbnails
    'DescribeThumbnails',
}

# Read-only operations — Describe*, List*, and Get* calls that do not mutate state.
READ_ONLY_OPERATIONS: set[str] = {
    'DescribeAccountConfiguration',
    'DescribeChannel',
    'DescribeInput',
    'DescribeInputDevice',
    'DescribeInputSecurityGroup',
    'DescribeMultiplex',
    'DescribeMultiplexProgram',
    'DescribeOffering',
    'DescribeReservation',
    'DescribeSchedule',
    'DescribeThumbnails',
    'ListChannels',
    'ListInputDevices',
    'ListInputSecurityGroups',
    'ListInputs',
    'ListMultiplexPrograms',
    'ListMultiplexes',
    'ListOfferings',
    'ListReservations',
    'ListTagsForResource',
}

# Destructive operations — Delete* calls that permanently remove resources.
DESTRUCTIVE_OPERATIONS: set[str] = {
    'DeleteChannel',
    'DeleteInput',
    'DeleteInputSecurityGroup',
    'DeleteMultiplex',
    'DeleteMultiplexProgram',
    'DeleteSchedule',
    'DeleteTags',
}

# Default page sizes for paginated operations.
# Maps operation names to default MaxResults/limit values.
# Applied when the LLM does not specify a page size.
# Default page sizes tuned to per-item response weight.
# Heavy items (many fields, nested lists/objects) get smaller pages to keep
# responses within a reasonable token budget.  Light/tiny items can afford
# larger pages.  The LLM can always override by providing the limit field
# explicitly.
#
# Weight analysis (from generated output models):
#   Heavy  – ChannelSummary (19 fields, nested destinations/inputAttachments),
#            Input (21 fields, nested destinations/sources),
#            InputDeviceSummary (15+ fields, nested hd/uhd/network settings)
#   Medium – Reservation (18 scalar-heavy fields), Offering (11 fields),
#            ScheduleAction (3 fields but deeply nested settings)
#   Light  – MultiplexSummary (9 fields), InputSecurityGroup (6 fields)
#   Tiny   – MultiplexProgramSummary (2 fields),
#            TransferringInputDeviceSummary (4 fields)
PAGINATION_DEFAULTS: dict[str, int] = {
    # Heavy
    'ListChannels': 5,
    'ListInputs': 5,
    'ListInputDevices': 5,
    # Medium
    'ListReservations': 10,
    'ListOfferings': 10,
    'DescribeSchedule': 10,
    # Light
    'ListMultiplexes': 20,
    'ListInputSecurityGroups': 20,
    # Tiny
    'ListMultiplexPrograms': 50,
    'ListInputDeviceTransfers': 50,
}
