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

"""Replication group tools for ElastiCache MCP server."""

from .create import create_replication_group
from .connect import create_jump_host_rg, connect_jump_host_rg, get_ssh_tunnel_command_rg
from .delete import delete_replication_group
from .describe import describe_replication_groups
from .modify import modify_replication_group, modify_replication_group_shard_configuration
from .test_migration import test_migration
from .start_migration import start_migration
from .complete_migration import complete_migration
from .parsers import (
    parse_shorthand_nodegroup,
    parse_shorthand_log_delivery,
    parse_shorthand_resharding,
)
from .processors import (
    process_log_delivery_configurations,
    process_nodegroup_configuration,
    process_resharding_configuration,
)

__all__ = [
    'connect_jump_host_rg',
    'create_jump_host_rg',
    'create_replication_group',
    'delete_replication_group',
    'describe_replication_groups',
    'get_ssh_tunnel_command_rg',
    'modify_replication_group',
    'modify_replication_group_shard_configuration',
    'parse_shorthand_nodegroup',
    'parse_shorthand_log_delivery',
    'parse_shorthand_resharding',
    'process_log_delivery_configurations',
    'process_nodegroup_configuration',
    'process_resharding_configuration',
    'test_migration',
    'start_migration',
    'complete_migration',
]
