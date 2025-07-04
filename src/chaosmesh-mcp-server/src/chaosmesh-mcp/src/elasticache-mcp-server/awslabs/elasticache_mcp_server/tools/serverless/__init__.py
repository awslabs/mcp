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

"""Serverless cache operations for ElastiCache MCP server."""

from .create import create_serverless_cache
from .delete import delete_serverless_cache
from .describe import describe_serverless_caches
from .modify import modify_serverless_cache
from .models import CacheUsageLimits
from .connect import (
    connect_jump_host_serverless,
    get_ssh_tunnel_command_serverless,
    create_jump_host_serverless,
)

__all__ = [
    'create_serverless_cache',
    'delete_serverless_cache',
    'describe_serverless_caches',
    'modify_serverless_cache',
    'CacheUsageLimits',
    'connect_jump_host_serverless',
    'get_ssh_tunnel_command_serverless',
    'create_jump_host_serverless',
]
