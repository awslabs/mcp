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

"""Database analyzer plugins package."""

from awslabs.dynamodb_mcp_server.db_analyzer.base_plugin import DatabasePlugin
from awslabs.dynamodb_mcp_server.db_analyzer.mysql import MySQLPlugin
from awslabs.dynamodb_mcp_server.db_analyzer.plugin_registry import PluginRegistry
from awslabs.dynamodb_mcp_server.db_analyzer.postgresql import PostgreSQLPlugin
from awslabs.dynamodb_mcp_server.db_analyzer.sqlserver import SQLServerPlugin


__all__ = [
    'DatabasePlugin',
    'MySQLPlugin',
    'PostgreSQLPlugin',
    'SQLServerPlugin',
    'PluginRegistry',
]
