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

"""Constants for the EKS MCP Server."""

# EKS Stack Management Operations
GENERATE_OPERATION = 'generate'
DEPLOY_OPERATION = 'deploy'
DESCRIBE_OPERATION = 'describe'
DELETE_OPERATION = 'delete'

# AWS CloudFormation
CFN_STACK_NAME_TEMPLATE = 'eks-{cluster_name}-stack'
CFN_CAPABILITY_IAM = 'CAPABILITY_IAM'
CFN_ON_FAILURE_DELETE = 'DELETE'
CFN_CREATED_BY_TAG = 'EksMcpServer'
CFN_STACK_TAG_KEY = 'CreatedBy'
CFN_STACK_TAG_VALUE = 'EksMcpServer'

# Error message templates
STACK_NOT_OWNED_ERROR_TEMPLATE = (
    'Stack {stack_name} exists but was not created by {tool_name}. '
    'For safety reasons, this tool will only {operation} stacks that were created by itself. '
    'To manage this stack, please use the AWS Console, CLI, or the tool that created it.'
)
