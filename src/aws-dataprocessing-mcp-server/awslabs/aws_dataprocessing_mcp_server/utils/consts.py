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

"""Constants for the DataProcessing MCP Server."""

# Environment Variables
CUSTOM_TAGS_ENV_VAR = 'CUSTOM_TAGS'

# Dataprocessing Stack Management Operations
MCP_MANAGED_TAG_KEY = 'ManagedBy'
MCP_MANAGED_TAG_VALUE = 'DataprocessingMcpServer'
MCP_RESOURCE_TYPE_TAG_KEY = 'ResourceType'
MCP_CREATION_TIME_TAG_KEY = 'CreatedAt'

# Default tags to be applied to all resources
DEFAULT_RESOURCE_TAGS = {MCP_MANAGED_TAG_KEY: MCP_MANAGED_TAG_VALUE}

# EMR Resource Types
EMR_CLUSTER_RESOURCE_TYPE = 'EMRCluster'
EMR_INSTANCE_FLEET_RESOURCE_TYPE = 'EMRInstanceFleet'
EMR_INSTANCE_GROUP_RESOURCE_TYPE = 'EMRInstanceGroup'
EMR_STEPS_RESOURCE_TYPE = 'EMRSteps'
