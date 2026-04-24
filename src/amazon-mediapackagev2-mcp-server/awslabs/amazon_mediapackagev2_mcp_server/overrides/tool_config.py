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

"""Tool configuration for mediapackagev2 MCP server."""

INCLUDED_OPERATIONS: set[str] = {
    'CancelHarvestJob',
    'CreateChannel',
    'CreateChannelGroup',
    'CreateHarvestJob',
    'CreateOriginEndpoint',
    'DeleteChannel',
    'DeleteChannelGroup',
    'DeleteChannelPolicy',
    'DeleteOriginEndpoint',
    'DeleteOriginEndpointPolicy',
    'GetChannel',
    'GetChannelGroup',
    'GetChannelPolicy',
    'GetHarvestJob',
    'GetOriginEndpoint',
    'GetOriginEndpointPolicy',
    'ListChannelGroups',
    'ListChannels',
    'ListHarvestJobs',
    'ListOriginEndpoints',
    'ListTagsForResource',
    'PutChannelPolicy',
    'PutOriginEndpointPolicy',
    'ResetChannelState',
    'ResetOriginEndpointState',
    'TagResource',
    'UntagResource',
    'UpdateChannel',
    'UpdateChannelGroup',
    'UpdateOriginEndpoint',
}

READ_ONLY_OPERATIONS: set[str] = {
    'GetChannel',
    'GetChannelGroup',
    'GetChannelPolicy',
    'GetHarvestJob',
    'GetOriginEndpoint',
    'GetOriginEndpointPolicy',
    'ListChannelGroups',
    'ListChannels',
    'ListHarvestJobs',
    'ListOriginEndpoints',
    'ListTagsForResource',
}

DESTRUCTIVE_OPERATIONS: set[str] = {
    'CancelHarvestJob',
    'DeleteChannel',
    'DeleteChannelGroup',
    'DeleteChannelPolicy',
    'DeleteOriginEndpoint',
    'DeleteOriginEndpointPolicy',
}

# Default page sizes for paginated operations.
# Maps operation names to default MaxResults/limit values.
# Applied when the LLM does not specify a page size.
# The LLM can always override by providing the limit field explicitly.
PAGINATION_DEFAULTS: dict[str, int] = {}
