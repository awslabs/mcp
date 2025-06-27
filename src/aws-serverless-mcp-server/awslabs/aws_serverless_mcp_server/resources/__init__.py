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

"""
MCP Resources Index

Exports all resource implementations for the AWS Serverless MCP server.
"""

from awslabs.aws_serverless_mcp_server.resources.deployment_details import (
    handle_deployment_details,
)
from awslabs.aws_serverless_mcp_server.resources.deployment_list import handle_deployments_list
from awslabs.aws_serverless_mcp_server.resources.template_details import handle_template_details
from awslabs.aws_serverless_mcp_server.resources.template_list import handle_template_list

__all__ = [
    handle_deployment_details,
    handle_deployments_list,
    handle_template_details,
    handle_template_list,
]
