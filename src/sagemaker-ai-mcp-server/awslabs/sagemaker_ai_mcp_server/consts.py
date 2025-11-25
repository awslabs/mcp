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

"""Constants for the SageMaker AI MCP Server."""

from typing import Literal, TypeAlias


# HyperPod Stack Management Operations
STACK_DEPLOY_OPERATION = 'deploy'
STACK_DESCRIBE_OPERATION = 'describe'
STACK_DELETE_OPERATION = 'delete'

# HyperPod Node Management Operations
LIST_CLUSTERS_OPERATION = 'list_clusters'
LIST_NODES_OPERATION = 'list_nodes'
DESCRIBE_NODE_OPERATION = 'describe_node'
UPDATE_SOFTWARE_OPERATION = 'update_software'
BATCH_DELETE_OPERATION = 'batch_delete'

# AWS CloudFormation
CFN_CAPABILITY_IAM = 'CAPABILITY_IAM'
CFN_CAPABILITY_NAMED_IAM = 'CAPABILITY_NAMED_IAM'
CAPABILITY_AUTO_EXPAND = 'CAPABILITY_AUTO_EXPAND'
CFN_ON_FAILURE_DELETE = 'DELETE'
CFN_STACK_TAG_KEY = 'CreatedBy'
CFN_STACK_TAG_VALUE = 'HyperPodMCPServer'
HYPERPOD_CFN_TEMPLATE_URL_EKS = 'https://aws-sagemaker-hyperpod-cluster-setup-us-east-1-prod.s3.us-east-1.amazonaws.com/templates/main-stack-eks-based-template.yaml'
HYPERPOD_CFN_TEMPLATE_URL_SLURM = 'https://aws-sagemaker-hyperpod-cluster-setup-us-east-1-prod.s3.us-east-1.amazonaws.com/templates-slurm/main-stack-slurm-based-template.yaml'

# Error message templates
STACK_NOT_OWNED_ERROR_TEMPLATE = (
    'Stack {stack_name} exists but was not created by {tool_name}. '
    'For safety reasons, this tool will only {operation} stacks that were created by itself. '
    'To manage this stack, please use the AWS Console, CLI, or the tool that created it.'
)


STACK_OPERATIONS = Literal['deploy', 'describe', 'delete']

SUPPORTED_REGIONS = Literal[
    'ap-northeast-1',
    'ap-south-1',
    'ap-southeast-1',
    'ap-southeast-2',
    'ap-southeast-3',
    'ap-southeast-4',
    'ca-central-1',
    'eu-central-1',
    'eu-north-1',
    'eu-south-2',
    'eu-west-1',
    'eu-west-2',
    'sa-east-1',
    'us-east-1',
    'us-east-2',
    'us-west-1',
    'us-west-2',
]

CLUSTER_ORCHESTRATORS = Literal['eks', 'slurm']

NODE_OPERATIONS: TypeAlias = Literal[
    'list_clusters',
    'list_nodes',
    'describe_node',
    'update_software',
    'batch_delete',
]
