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

# boto3_tools/__init__.py
from .boto3_registry import Boto3ToolRegistry
from .boto3_docstrings import boto3_docstrings
from awslabs.aws_finops_mcp_server.consts import AWS_SERVICE_NAME_MAP as SERVICE_NAME_MAP

__all__ = ['Boto3ToolRegistry', 'SERVICE_NAME_MAP', 'boto3_docstrings']
